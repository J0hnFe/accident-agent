"""Contrato base de herramienta (seccion 7.1 del plan).

- Una herramienta declara `name`, `description` (en espanol, para el LLM), `input_model`,
  `output_model` y `timeout_seconds`, e implementa `run`.
- El JSON Schema que recibe el LLM se genera desde `input_model`, sin duplicar definiciones.
- `execute` valida la entrada, ejecuta, valida la salida y devuelve siempre un `ToolResult`:
  `{"ok": true, "data": ...}` o `{"ok": false, "error": {"type": ..., "message": ...}}`.
  Nunca propaga excepciones. El timeout lo aplica el orquestador (tarea 4.3).
"""

import json
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import Any, Final, Literal, Self

from pydantic import BaseModel, ConfigDict, ValidationError, model_validator

ErrorType = Literal["validation", "timeout", "execution", "not_found"]

_GENERIC_EXECUTION_MESSAGE: Final = "la herramienta fallo al ejecutarse"


class ToolError(Exception):
    """Error esperado de una herramienta, con su tipo para el LLM."""

    def __init__(self, error_type: ErrorType, message: str) -> None:
        self.error_type: ErrorType = error_type
        self.message = message
        super().__init__(message)


class ToolInput(BaseModel):
    """Base de las entradas: rechaza argumentos que el contrato no declara."""

    model_config = ConfigDict(extra="forbid")


class ToolErrorInfo(BaseModel):
    type: ErrorType
    message: str


class ToolResult(BaseModel):
    ok: bool
    data: dict[str, Any] | None = None
    error: ToolErrorInfo | None = None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.ok != (self.data is not None) or self.ok == (self.error is not None):
            raise ValueError("ok=true lleva data; ok=false lleva error")
        return self

    @classmethod
    def failure(cls, error_type: ErrorType, message: str) -> "ToolResult":
        return cls(ok=False, error=ToolErrorInfo(type=error_type, message=message))

    def to_llm(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude_none=True)


class ToolSpec(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


def _inline(node: Any, defs: Mapping[str, Any]) -> Any:
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            return _inline(defs[ref.rsplit("/", 1)[-1]], defs)
        return {k: _inline(v, defs) for k, v in node.items() if k not in {"$defs", "title"}}
    if isinstance(node, list):
        return [_inline(v, defs) for v in node]
    return node


def inline_schema(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Esquema sin `$ref`, `$defs` ni `title`: los modelos gratuitos manejan mejor uno plano."""
    result: dict[str, Any] = _inline(dict(schema), schema.get("$defs", {}))
    return result


def _validation_message(exc: ValidationError) -> str:
    # Solo campo y motivo: la entrada puede traer datos personales escritos por el usuario.
    parts = []
    for error in exc.errors(include_input=False, include_url=False):
        location = ".".join(str(p) for p in error["loc"]) or "argumentos"
        parts.append(f"{location}: {error['msg']}")
    return "; ".join(parts)


class Tool[InputT: BaseModel, OutputT: BaseModel](ABC):
    name: str
    description: str
    input_model: type[InputT]
    output_model: type[OutputT]
    timeout_seconds: float = 10.0

    @abstractmethod
    def run(self, params: InputT) -> OutputT: ...

    def spec(self) -> ToolSpec:
        return ToolSpec(
            name=self.name,
            description=self.description,
            parameters=inline_schema(self.input_model.model_json_schema()),
        )


def execute(tool: Tool[Any, Any], arguments: Mapping[str, Any] | str) -> ToolResult:
    """Ejecuta la herramienta con argumentos del LLM (dict o texto JSON) y envuelve el resultado."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return ToolResult.failure("validation", "los argumentos no son JSON valido")
    try:
        params = tool.input_model.model_validate(arguments)
    except ValidationError as exc:
        return ToolResult.failure("validation", _validation_message(exc))
    try:
        output = tool.run(params)
        checked = tool.output_model.model_validate(output.model_dump(warnings=False))
    except ToolError as exc:
        return ToolResult.failure(exc.error_type, exc.message)
    except Exception:
        # El detalle va al log del orquestador (tarea 4.6), no al LLM.
        return ToolResult.failure("execution", _GENERIC_EXECUTION_MESSAGE)
    return ToolResult(ok=True, data=checked.model_dump(mode="json"))
