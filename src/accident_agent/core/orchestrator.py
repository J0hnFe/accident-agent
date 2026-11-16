"""Orquestador: ciclo planificar-actuar-observar con function calling (seccion 7.5, tarea 4.3).

Por solicitud:
1. Arma los mensajes: prompt de sistema, historial, contexto de la sesion y mensaje del usuario.
2. Pide al LLM una respuesta final o llamadas a herramientas.
3. Ejecuta las llamadas en paralelo, cada una con su timeout, y devuelve al LLM el resultado
   o un error estructurado. Repite hasta la respuesta final o el limite de iteraciones.
4. Verifica el grounding (ids citados), guarda la memoria y responde.

Nunca propaga excepciones a la interfaz: los fallos del proveedor se convierten en un mensaje
amigable y los de las herramientas vuelven al LLM como resultado.
"""

import json
import re
import time
import uuid
from collections.abc import Iterable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from typing import Any, Final, Literal

from pydantic import BaseModel, Field

from accident_agent.core.llm import (
    AuthenticationError,
    LLMError,
    LLMProvider,
    LLMResult,
    Message,
    RateLimitError,
    ToolCall,
)
from accident_agent.core.memory import ConversationMemory
from accident_agent.core.prompts import SYSTEM_PROMPT, session_context, tool_result_content
from accident_agent.core.registry import ToolRegistry
from accident_agent.core.tool import ToolResult, execute
from accident_agent.core.tracer import NoopTracer, Trace, Tracer
from accident_agent.observability.events import EventLogger

ACCIDENT_ID: Final = re.compile(r"\bSIN-\d{4}-\d{4}\b")
MAX_REMEMBERED_IDS: Final = 20

StopReason = Literal["final_answer", "max_iterations", "llm_error"]
ToolStatus = Literal["ok", "error", "timeout"]

MESSAGES: Final[dict[str, str]] = {
    "rate_limit": (
        "El servicio de inteligencia artificial alcanzo su limite de uso. "
        "Intenta de nuevo en unos minutos."
    ),
    "auth": (
        "La clave del proveedor de inteligencia artificial falta o no es valida. "
        "Revisa OPENROUTER_API_KEY en el archivo .env."
    ),
    "unavailable": (
        "El servicio de inteligencia artificial no esta disponible en este momento. "
        "Intenta de nuevo mas tarde."
    ),
    "max_iterations": (
        "No pude completar la respuesta dentro del limite de pasos permitido. "
        "Intenta dividir la pregunta en partes mas simples."
    ),
    "empty": "No obtuve una respuesta del modelo. Intenta reformular la pregunta.",
}


class ToolUse(BaseModel):
    name: str
    params: dict[str, Any] | str
    duration_ms: int
    status: ToolStatus
    error_type: str | None = None


class OrchestratorResponse(BaseModel):
    session_id: str
    answer: str
    tools_used: list[ToolUse] = Field(default_factory=list)
    trace_id: str
    iterations: int
    stop_reason: StopReason


class OrchestratorLimits(BaseModel):
    max_iterations: int = 5
    max_tool_calls_per_iteration: int = 4


def _params(arguments: str) -> dict[str, Any] | str:
    try:
        value = json.loads(arguments or "{}")
    except json.JSONDecodeError:
        return arguments
    return value if isinstance(value, dict) else arguments


def _summary(result: ToolResult) -> dict[str, Any]:
    """Resumen para el log: conteos e ids, nunca textos."""
    data = result.data or {}
    summary: dict[str, Any] = {}
    for key in ("total_found", "report_id", "file_path"):
        if key in data:
            summary[key] = data[key]
    ids = [a.get("accident_id") for a in data.get("accidents", []) if isinstance(a, dict)]
    ids += data.get("included_ids", [])
    if ids:
        summary["accident_ids"] = ids[:MAX_REMEMBERED_IDS]
    for key in ("not_found_ids", "stats", "reports"):
        if data.get(key):
            summary[key] = len(data[key]) if key != "not_found_ids" else data[key]
    return summary


def _result_ids(result: ToolResult) -> list[str]:
    data = result.data or {}
    ids = [a["accident_id"] for a in data.get("accidents", []) if isinstance(a, dict)]
    return ids + list(data.get("included_ids", []))


def _unique(ids: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(ids))


class Orchestrator:
    def __init__(
        self,
        *,
        llm: LLMProvider,
        registry: ToolRegistry,
        memory: ConversationMemory,
        logger: EventLogger,
        tracer: Tracer | None = None,
        limits: OrchestratorLimits | None = None,
        executor: ThreadPoolExecutor | None = None,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._memory = memory
        self._logger = logger
        self._tracer = tracer or NoopTracer()
        self._limits = limits or OrchestratorLimits()
        self._executor = executor or ThreadPoolExecutor(max_workers=8, thread_name_prefix="tool")

    def handle(self, session_id: str, message: str) -> OrchestratorResponse:
        trace_id = uuid.uuid4().hex
        started = time.monotonic()
        trace = self._tracer.start_trace(trace_id=trace_id, session_id=session_id, input=message)
        log = {"trace_id": trace_id, "session_id": session_id}
        try:
            response = self._run(session_id, message, trace_id, trace, log)
        except Exception as exc:
            # Ultima red de seguridad: la interfaz nunca recibe una excepcion.
            self._logger.warning("request_error", **log, error=type(exc).__name__)
            response = OrchestratorResponse(
                session_id=session_id,
                answer=MESSAGES["unavailable"],
                trace_id=trace_id,
                iterations=0,
                stop_reason="llm_error",
            )
        duration_ms = int((time.monotonic() - started) * 1000)
        self._logger.info(
            "request",
            **log,
            iterations=response.iterations,
            stop_reason=response.stop_reason,
            tools=[t.name for t in response.tools_used],
            duration_ms=duration_ms,
        )
        trace.end(
            output=response.answer,
            metadata={"stop_reason": response.stop_reason, "iterations": response.iterations},
        )
        return response

    def _run(
        self, session_id: str, message: str, trace_id: str, trace: Trace, log: dict[str, str]
    ) -> OrchestratorResponse:
        remembered = self._memory.last_accident_ids(session_id)
        messages = [Message(role="system", content=SYSTEM_PROMPT)]
        messages += self._memory.history(session_id)
        if context := session_context(remembered):
            messages.append(Message(role="system", content=context))
        messages.append(Message(role="user", content=message))

        tools_used: list[ToolUse] = []
        turn_ids: list[str] = []
        retrieved_text: list[str] = []
        specs = self._registry.specs()

        def finish(answer: str, stop: StopReason, iterations: int) -> OrchestratorResponse:
            if stop == "final_answer":
                answer = self._grounded(answer, message, remembered, retrieved_text, log)
                self._memory.add_turn(session_id, message, answer)
                if turn_ids:
                    self._memory.set_last_accident_ids(
                        session_id, _unique(turn_ids)[:MAX_REMEMBERED_IDS]
                    )
            return OrchestratorResponse(
                session_id=session_id,
                answer=answer,
                tools_used=tools_used,
                trace_id=trace_id,
                iterations=iterations,
                stop_reason=stop,
            )

        for iteration in range(1, self._limits.max_iterations + 1):
            result = self._call_llm(messages, specs, trace, {**log, "iteration": iteration})
            if isinstance(result, LLMError):
                return finish(self._llm_error_message(result), "llm_error", iteration)
            if not result.tool_calls:
                return finish(result.content or MESSAGES["empty"], "final_answer", iteration)

            messages.append(
                Message(role="assistant", content=result.content, tool_calls=result.tool_calls)
            )
            for call, outcome, duration_ms in self._run_tools(result.tool_calls, trace):
                tools_used.append(
                    ToolUse(
                        name=call.name,
                        params=_params(call.arguments),
                        duration_ms=duration_ms,
                        status=self._status(outcome),
                        error_type=outcome.error.type if outcome.error else None,
                    )
                )
                self._logger.info(
                    "tool_call",
                    **log,
                    iteration=iteration,
                    tool=call.name,
                    params=_params(call.arguments),
                    duration_ms=duration_ms,
                    status=self._status(outcome),
                    result_summary=_summary(outcome),
                    error_type=outcome.error.type if outcome.error else None,
                )
                payload = outcome.to_llm()
                content = tool_result_content(payload)
                retrieved_text.append(content)
                turn_ids += _result_ids(outcome)
                messages.append(Message(role="tool", tool_call_id=call.id, content=content))

        return finish(MESSAGES["max_iterations"], "max_iterations", self._limits.max_iterations)

    def _call_llm(
        self, messages: list[Message], specs: list[Any], trace: Trace, log: dict[str, Any]
    ) -> LLMResult | LLMError:
        started = time.monotonic()
        with trace.generation([m.model_dump(exclude_none=True) for m in messages]) as generation:
            try:
                result = self._llm.complete(messages, specs)
            except LLMError as exc:
                generation.update(error=type(exc).__name__)
                self._logger.warning(
                    "llm_call",
                    **log,
                    status="error",
                    error_type=type(exc).__name__,
                    duration_ms=int((time.monotonic() - started) * 1000),
                )
                return exc
            usage = result.usage.model_dump()
            generation.update(
                model=result.model,
                output={
                    "content": result.content,
                    "tool_calls": [c.model_dump() for c in result.tool_calls],
                },
                usage=usage,
            )
        self._logger.info(
            "llm_call",
            **log,
            status="ok",
            model=result.model,
            duration_ms=int((time.monotonic() - started) * 1000),
            tokens=usage,
            retries=result.retries,
            tool_calls=[c.name for c in result.tool_calls],
        )
        return result

    def _run_tools(
        self, calls: list[ToolCall], trace: Trace
    ) -> list[tuple[ToolCall, ToolResult, int]]:
        limit = self._limits.max_tool_calls_per_iteration
        started = time.monotonic()
        pending: list[tuple[ToolCall, Future[ToolResult] | ToolResult, float]] = []
        for index, call in enumerate(calls):
            tool = self._registry.get(call.name)
            if index >= limit:
                outcome: Future[ToolResult] | ToolResult = ToolResult.failure(
                    "execution", f"limite de {limit} llamadas a herramientas por iteracion"
                )
                pending.append((call, outcome, 0.0))
            elif tool is None:
                outcome = ToolResult.failure("not_found", f"herramienta desconocida: {call.name}")
                pending.append((call, outcome, 0.0))
            else:
                future = self._executor.submit(execute, tool, call.arguments)
                pending.append((call, future, tool.timeout_seconds))

        results = []
        for call, outcome, timeout in pending:
            with trace.span(call.name, _params(call.arguments)) as span:
                if isinstance(outcome, Future):
                    remaining = max(0.0, started + timeout - time.monotonic())
                    try:
                        outcome = outcome.result(timeout=remaining)
                    except FutureTimeout:
                        # El hilo sigue hasta su timeout nativo (driver de Neo4j o httpx).
                        outcome = ToolResult.failure(
                            "timeout", f"la herramienta {call.name} supero {timeout:g} s"
                        )
                span.update(
                    output=_summary(outcome), error=outcome.error.type if outcome.error else None
                )
            duration_ms = int((time.monotonic() - started) * 1000)
            results.append((call, outcome, duration_ms))
        return results

    @staticmethod
    def _status(result: ToolResult) -> ToolStatus:
        if result.ok:
            return "ok"
        return "timeout" if result.error and result.error.type == "timeout" else "error"

    @staticmethod
    def _llm_error_message(error: LLMError) -> str:
        if isinstance(error, RateLimitError):
            return MESSAGES["rate_limit"]
        if isinstance(error, AuthenticationError):
            return MESSAGES["auth"]
        return MESSAGES["unavailable"]

    def _grounded(
        self,
        answer: str,
        question: str,
        remembered: list[str],
        retrieved: list[str],
        log: dict[str, str],
    ) -> str:
        """Tarea 4.5: un id citado debe venir de las herramientas, la memoria o la pregunta."""
        allowed = set(remembered) | set(ACCIDENT_ID.findall(question))
        for text in retrieved:
            allowed |= set(ACCIDENT_ID.findall(text))
        unknown = sorted(set(ACCIDENT_ID.findall(answer)) - allowed)
        if not unknown:
            return answer
        self._logger.warning("grounding_violation", **log, accident_ids=unknown)
        return (
            f"{answer}\n\nNota: la respuesta menciona identificadores que no se obtuvieron de la "
            f"base ({', '.join(unknown)}); verificalos antes de usarlos."
        )

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)
