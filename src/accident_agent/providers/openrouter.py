"""Adaptador OpenRouter del puerto `LLMProvider` (seccion 7.6 del plan, tarea 4.1).

API compatible con OpenAI (`/chat/completions` con `tools`). Politica ante fallos:
- 429, 5xx, timeout o error de red: reintento con backoff exponencial que respeta `Retry-After`;
  agotados los reintentos (o si `Retry-After` excede la espera maxima) pasa al siguiente modelo.
- Respuesta mal formada o error dentro de un 200: siguiente modelo.
- 401 o 403, o clave ausente: `AuthenticationError` sin probar otros modelos (misma clave).
- Todo dentro de un presupuesto total de tiempo, para que la solicitud no quede colgada.

Limites del plan gratuito (`docs/evidencias/0.3_limites_openrouter.md`): 20 por minuto y 50 por dia.
"""

import json
import time
import uuid
from collections.abc import Callable, Sequence
from typing import Any, Final

import httpx

from accident_agent.core.llm import (
    AuthenticationError,
    InvalidResponseError,
    LLMError,
    LLMResult,
    Message,
    ProviderUnavailableError,
    RateLimitError,
    ToolCall,
    Usage,
)
from accident_agent.core.tool import ToolSpec

BASE_URL: Final = "https://openrouter.ai/api/v1"
# Modelos elegidos en la tarea 0.3 (`docs/evidencias/0.3_prueba_tool_calling.md`); se usan si
# OPENROUTER_MODELS esta vacio.
DEFAULT_MODELS: Final = (
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "nvidia/nemotron-3.5-super-vl:free",
    "google/gemma-4-31b-it:free",
)
MAX_BACKOFF_SECONDS: Final = 8.0


def _to_openai(message: Message) -> dict[str, Any]:
    if message.role == "tool":
        return {"role": "tool", "tool_call_id": message.tool_call_id, "content": message.content}
    data: dict[str, Any] = {"role": message.role, "content": message.content}
    if message.tool_calls:
        data["tool_calls"] = [
            {"id": c.id, "type": "function", "function": {"name": c.name, "arguments": c.arguments}}
            for c in message.tool_calls
        ]
    return data


def _tool_spec(spec: ToolSpec) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": spec.name,
            "description": spec.description,
            "parameters": spec.parameters,
        },
    }


def _parse_tool_call(raw: Any) -> ToolCall:
    function = raw.get("function") if isinstance(raw, dict) else None
    name = function.get("name") if isinstance(function, dict) else None
    if not isinstance(name, str) or not name:
        raise InvalidResponseError("tool_call sin nombre de funcion")
    arguments = function.get("arguments") if isinstance(function, dict) else None
    if isinstance(arguments, dict):
        arguments = json.dumps(arguments, ensure_ascii=False)
    elif arguments is None or arguments == "":
        arguments = "{}"
    elif not isinstance(arguments, str):
        raise InvalidResponseError("argumentos de tool_call con tipo no valido")
    call_id = raw.get("id") or f"call_{uuid.uuid4().hex[:12]}"
    return ToolCall(id=str(call_id), name=name, arguments=arguments)


def _parse(body: Any, requested_model: str) -> LLMResult:
    if not isinstance(body, dict):
        raise InvalidResponseError("respuesta no es un objeto JSON")
    if "error" in body:
        raise ProviderUnavailableError(
            f"error del proveedor dentro de la respuesta: {body['error']}"
        )
    choices = body.get("choices")
    if not isinstance(choices, list) or not choices:
        raise InvalidResponseError("respuesta sin choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        raise InvalidResponseError("choice sin message")
    content = message.get("content")
    raw_calls = message.get("tool_calls") or []
    if not isinstance(raw_calls, list):
        raise InvalidResponseError("tool_calls no es una lista")
    raw_usage = body.get("usage")
    usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
    return LLMResult(
        content=content if isinstance(content, str) else None,
        tool_calls=[_parse_tool_call(c) for c in raw_calls],
        model=str(body.get("model") or requested_model),
        usage=Usage(**{k: v for k, v in usage.items() if k in Usage.model_fields}),
    )


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


class OpenRouterProvider:
    def __init__(
        self,
        *,
        api_key: str,
        models: Sequence[str],
        timeout_seconds: float = 30.0,
        max_retries: int = 1,
        total_budget_seconds: float = 90.0,
        base_url: str = BASE_URL,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        if not models:
            raise ValueError("OPENROUTER_MODELS no tiene modelos configurados")
        self._api_key = api_key
        self._models = list(models)
        self._max_retries = max_retries
        self._budget = total_budget_seconds
        self._url = f"{base_url}/chat/completions"
        self._client = client or httpx.Client(timeout=httpx.Timeout(timeout_seconds))
        self._sleep = sleep
        self._monotonic = monotonic

    @property
    def models(self) -> list[str]:
        return list(self._models)

    def complete(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> LLMResult:
        if not self._api_key:
            raise AuthenticationError("falta OPENROUTER_API_KEY en la configuracion")
        deadline = self._monotonic() + self._budget
        payload = {
            "messages": [_to_openai(m) for m in messages],
            "tools": [_tool_spec(t) for t in tools],
            "tool_choice": "auto",
            "temperature": 0.2,
        }
        failures = 0
        last_error: LLMError = ProviderUnavailableError("sin intentos")
        for model in self._models:
            for attempt in range(self._max_retries + 1):
                try:
                    result = self._call(model, payload)
                    return result.model_copy(update={"retries": failures})
                except AuthenticationError:
                    raise
                except InvalidResponseError as exc:
                    # Otro intento con el mismo modelo daria el mismo formato: siguiente modelo.
                    failures += 1
                    last_error = exc
                    break
                except (RateLimitError, ProviderUnavailableError) as exc:
                    failures += 1
                    last_error = exc
                    if attempt == self._max_retries:
                        break
                    wait = (
                        exc.retry_after
                        if isinstance(exc, RateLimitError) and exc.retry_after is not None
                        else min(2.0**attempt, MAX_BACKOFF_SECONDS)
                    )
                    if wait > MAX_BACKOFF_SECONDS or self._monotonic() + wait > deadline:
                        break
                    self._sleep(wait)
            if self._monotonic() >= deadline:
                break
        raise last_error

    def _call(self, model: str, payload: dict[str, Any]) -> LLMResult:
        try:
            response = self._client.post(
                self._url,
                json={"model": model, **payload},
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "X-Title": "accident-agent",
                },
            )
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError(f"{model}: tiempo de espera agotado") from exc
        except httpx.HTTPError as exc:
            raise ProviderUnavailableError(f"{model}: error de red") from exc
        status = response.status_code
        if status in (401, 403):
            raise AuthenticationError("OpenRouter rechazo la clave (OPENROUTER_API_KEY)")
        if status == 429:
            raise RateLimitError(f"{model}: limite de uso alcanzado", _retry_after(response))
        if status >= 400:
            raise ProviderUnavailableError(f"{model}: HTTP {status}")
        try:
            body = response.json()
        except ValueError as exc:
            raise InvalidResponseError(f"{model}: respuesta que no es JSON") from exc
        return _parse(body, model)
