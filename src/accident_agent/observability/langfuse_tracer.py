"""Adaptador Langfuse Cloud del puerto `Tracer` (seccion 7.9 del plan, tarea 4.6b).

Una observacion raiz `request` (tipo agent) por solicitud, con el mismo trace_id de los logs; una
generation por llamada al LLM y una observacion tipo tool por herramienta. La sesion se propaga a
todas con `propagate_attributes`. Entradas y salidas pasan por la misma redaccion que los logs.
El SDK envia en segundo plano; `SafeTracer` aisla cualquier fallo.
"""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from typing import Any

from langfuse import Langfuse, propagate_attributes

from accident_agent.core.tracer import Generation, Span
from accident_agent.observability.logging import redact_value


class _LangfuseSpan:
    def __init__(self, observation: Any) -> None:
        self._observation = observation

    def update(self, *, output: Any = None, error: str | None = None) -> None:
        self._observation.update(
            output=redact_value(output),
            level="ERROR" if error else None,
            status_message=error,
        )


class _LangfuseGeneration:
    def __init__(self, observation: Any) -> None:
        self._observation = observation

    def update(
        self,
        *,
        model: str | None = None,
        output: Any = None,
        usage: dict[str, int] | None = None,
        error: str | None = None,
    ) -> None:
        usage = usage or {}
        self._observation.update(
            model=model,
            output=redact_value(output),
            usage_details={
                "input": usage.get("prompt_tokens", 0),
                "output": usage.get("completion_tokens", 0),
            },
            level="ERROR" if error else None,
            status_message=error,
        )


class _LangfuseTrace:
    def __init__(self, client: Langfuse, trace_id: str, session_id: str, input: Any) -> None:
        self._root_cm: AbstractContextManager[Any] = client.start_as_current_observation(
            trace_context={"trace_id": trace_id},
            name="request",
            as_type="agent",
            input=redact_value(input),
        )
        self._root = self._root_cm.__enter__()
        self._attributes_cm: AbstractContextManager[Any] = propagate_attributes(
            session_id=session_id, trace_name="accident-agent"
        )
        self._attributes_cm.__enter__()

    @contextmanager
    def span(self, name: str, input: Any) -> Iterator[Span]:
        observation = self._root.start_observation(
            name=name, as_type="tool", input=redact_value(input)
        )
        try:
            yield _LangfuseSpan(observation)
        finally:
            observation.end()

    @contextmanager
    def generation(self, input: Any) -> Iterator[Generation]:
        observation = self._root.start_observation(
            name="llm", as_type="generation", input=redact_value(input)
        )
        try:
            yield _LangfuseGeneration(observation)
        finally:
            observation.end()

    def end(self, *, output: Any, metadata: dict[str, Any]) -> None:
        try:
            self._root.update(output=redact_value(output), metadata=metadata)
        finally:
            self._attributes_cm.__exit__(None, None, None)
            self._root_cm.__exit__(None, None, None)


class LangfuseTracer:
    def __init__(
        self,
        *,
        public_key: str,
        secret_key: str,
        base_url: str,
        client: Langfuse | None = None,
    ) -> None:
        self._client = client or Langfuse(
            public_key=public_key, secret_key=secret_key, base_url=base_url
        )

    def start_trace(self, *, trace_id: str, session_id: str, input: Any) -> _LangfuseTrace:
        return _LangfuseTrace(self._client, trace_id, session_id, input)

    def flush(self) -> None:
        self._client.flush()
