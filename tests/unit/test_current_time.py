from datetime import UTC, datetime

import pytest

from accident_agent.core.clock import FixedClock
from accident_agent.core.tool import execute
from accident_agent.tools.current_time import CurrentTimeTool

# Reloj fijo del plan (seccion 9): 2026-11-15, 12:30 en Ecuador.
INSTANT = datetime(2026, 11, 15, 17, 30, 15, tzinfo=UTC)


def _tool(default: str = "America/Guayaquil") -> CurrentTimeTool:
    return CurrentTimeTool(FixedClock(INSTANT), default_timezone=default)


def test_default_timezone_with_fixed_clock() -> None:
    result = execute(_tool(), {})
    assert result.data == {
        "iso_datetime": "2026-11-15T12:30:15-05:00",
        "date": "2026-11-15",
        "time": "12:30:15",
        "weekday": "domingo",
        "timezone": "America/Guayaquil",
        "utc_offset": "-05:00",
        "unix_timestamp": int(INSTANT.timestamp()),
    }


def test_explicit_timezone() -> None:
    result = execute(_tool(), {"timezone": "Europe/Madrid"})
    assert result.data is not None
    assert result.data["iso_datetime"] == "2026-11-15T18:30:15+01:00"
    assert result.data["utc_offset"] == "+01:00"


def test_default_comes_from_configuration() -> None:
    result = execute(_tool(default="UTC"), {})
    assert result.data is not None
    assert (result.data["timezone"], result.data["time"]) == ("UTC", "17:30:15")


@pytest.mark.parametrize("zone", ["Marte/Olimpo", "", "../../etc/passwd", "-05:00", "x" * 100])
def test_invalid_timezone_is_a_validation_error(zone: str) -> None:
    result = execute(_tool(), {"timezone": zone})
    assert result.error is not None
    assert result.error.type == "validation"
    assert "timezone" in result.error.message


def test_invalid_default_is_rejected_at_construction() -> None:
    with pytest.raises(ValueError, match="zona"):
        _tool(default="Nowhere/Land")


def test_spec_for_the_llm() -> None:
    spec = _tool().spec()
    assert spec.name == "get_current_time"
    assert "fechas relativas" in spec.description
    assert spec.parameters["properties"]["timezone"]["description"]
    assert "required" not in spec.parameters


def test_invalid_timezone_message_does_not_echo_the_input() -> None:
    result = execute(_tool(), {"timezone": "Marte/Olimpo"})
    assert result.error is not None
    assert "Marte" not in result.error.message
