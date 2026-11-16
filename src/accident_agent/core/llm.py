"""Puerto del proveedor de IA (seccion 7.6 del plan).

El orquestador solo conoce estos tipos; el formato de cada API vive en su adaptador.
"""

from collections.abc import Sequence
from typing import Literal, Protocol

from pydantic import BaseModel, Field

from accident_agent.core.tool import ToolSpec

Role = Literal["system", "user", "assistant", "tool"]


class ToolCall(BaseModel):
    id: str
    name: str
    # Texto JSON tal como lo envia el modelo; lo valida `core.tool.execute`.
    arguments: str


class Message(BaseModel):
    role: Role
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_call_id: str | None = None


class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class LLMResult(BaseModel):
    content: str | None
    tool_calls: list[ToolCall]
    model: str
    usage: Usage = Field(default_factory=Usage)
    # Intentos fallidos antes de esta respuesta (reintentos y modelos de respaldo).
    retries: int = 0


class LLMError(Exception):
    """Fallo del proveedor; el orquestador lo convierte en un mensaje amigable."""


class RateLimitError(LLMError):
    def __init__(self, message: str, retry_after: float | None = None) -> None:
        self.retry_after = retry_after
        super().__init__(message)


class ProviderUnavailableError(LLMError):
    """Timeout, error 5xx o modelo que no puede atender la solicitud."""


class InvalidResponseError(LLMError):
    """Respuesta sin el formato esperado (p. ej. un tool_call sin nombre)."""


class AuthenticationError(LLMError):
    """Clave ausente o rechazada: no tiene sentido probar otro modelo."""


class LLMProvider(Protocol):
    def complete(self, messages: Sequence[Message], tools: Sequence[ToolSpec]) -> LLMResult: ...
