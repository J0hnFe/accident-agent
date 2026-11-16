import json
from datetime import UTC, datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

import pytest
from pydantic import BaseModel, Field

from accident_agent.core.clock import FixedClock, SystemClock
from accident_agent.core.tool import Tool, ToolError, ToolInput, ToolResult, execute


class Color(StrEnum):
    RED = "rojo"
    BLUE = "azul"


class Inner(BaseModel):
    size: int = Field(ge=1, description="Tamano")


class EchoInput(ToolInput):
    text: str = Field(min_length=1, description="Texto a repetir")
    color: Color | None = None
    inner: Inner | None = None
    fail_with: str | None = None


class EchoOutput(BaseModel):
    echoed: str
    when: datetime


class EchoTool(Tool[EchoInput, EchoOutput]):
    name = "echo"
    description = "Repite el texto."
    input_model = EchoInput
    output_model = EchoOutput
    timeout_seconds = 1.0

    def run(self, params: EchoInput) -> EchoOutput:
        if params.fail_with == "not_found":
            raise ToolError("not_found", "no existe")
        if params.fail_with == "boom":
            raise RuntimeError("detalle interno con dato 1712345678")
        if params.fail_with == "bad_output":
            return EchoOutput.model_construct(echoed=1, when="x")  # type: ignore[arg-type]
        return EchoOutput(echoed=params.text, when=datetime(2026, 11, 15, tzinfo=UTC))


def test_success_envelope() -> None:
    result = execute(EchoTool(), {"text": "hola"})
    assert result.ok
    assert result.to_llm() == {
        "ok": True,
        "data": {"echoed": "hola", "when": "2026-11-15T00:00:00Z"},
    }


def test_arguments_as_json_string() -> None:
    assert execute(EchoTool(), json.dumps({"text": "hola"})).ok


@pytest.mark.parametrize(
    ("arguments", "fragment"),
    [
        ({}, "text"),
        ({"text": ""}, "text"),
        ({"text": "x", "color": "verde"}, "color"),
        ({"text": "x", "inner": {"size": 0}}, "inner.size"),
        ("{no es json", "JSON"),
        ({"text": "x", "extra": 1}, "extra"),
    ],
)
def test_validation_errors(arguments: Any, fragment: str) -> None:
    result = execute(EchoTool(), arguments)
    assert not result.ok
    assert result.error is not None
    assert result.error.type == "validation"
    assert fragment in result.error.message


def test_validation_message_does_not_echo_the_input() -> None:
    result = execute(EchoTool(), {"text": "x", "color": "cedula 1712345678"})
    assert result.error is not None
    assert "1712345678" not in result.error.message


def test_tool_error_keeps_its_type() -> None:
    result = execute(EchoTool(), {"text": "x", "fail_with": "not_found"})
    assert result.to_llm() == {"ok": False, "error": {"type": "not_found", "message": "no existe"}}


def test_unexpected_exception_is_an_execution_error_without_details() -> None:
    result = execute(EchoTool(), {"text": "x", "fail_with": "boom"})
    assert result.error is not None
    assert result.error.type == "execution"
    assert "1712345678" not in result.error.message


def test_invalid_output_is_an_execution_error() -> None:
    result = execute(EchoTool(), {"text": "x", "fail_with": "bad_output"})
    assert result.error is not None
    assert result.error.type == "execution"


def test_schema_is_generated_from_the_input_model_and_inlined() -> None:
    spec = EchoTool().spec()
    assert (spec.name, spec.description) == ("echo", "Repite el texto.")
    schema = spec.parameters
    text = json.dumps(schema)
    assert "$ref" not in text
    assert "$defs" not in text
    assert "title" not in schema["properties"]["text"]
    assert schema["required"] == ["text"]
    assert schema["additionalProperties"] is False
    color = schema["properties"]["color"]["anyOf"][0]
    assert color["enum"] == ["rojo", "azul"]
    inner = schema["properties"]["inner"]["anyOf"][0]
    assert inner["properties"]["size"] == {"type": "integer", "minimum": 1, "description": "Tamano"}


def test_result_model_requires_consistency() -> None:
    with pytest.raises(ValueError, match="ok"):
        ToolResult(ok=True)


def test_clocks() -> None:
    fixed = datetime(2026, 11, 15, 12, 0, tzinfo=timezone(timedelta(hours=-5)))
    assert FixedClock(fixed).now() == fixed
    with pytest.raises(ValueError, match="zona"):
        FixedClock(datetime(2026, 11, 15))
    now = SystemClock().now()
    assert now.tzinfo is not None
