import json
import logging
from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog

from accident_agent.observability.logging import configure_logging, get_logger, redact_value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("cedula 1712345678", "cedula [CEDULA]"),
        ("placa PBX-1234 en SIN-2026-0009", "placa [PLACA] en SIN-2026-0009"),
        ("Bearer sk-or-v1-abcdef0123456789", "Bearer [SECRETO]"),
        ("clave sk-or-v1-abcdef0123456789 y pk-lf-1234-abcd", "clave [SECRETO] y [SECRETO]"),
        ("sk-lf-0a1b2c3d-4e5f", "[SECRETO]"),
        (
            {"params": {"text": "dueno 1712345678"}, "n": 3, "ids": ["SIN-2025-0001", "ABC-1234"]},
            {"params": {"text": "dueno [CEDULA]"}, "n": 3, "ids": ["SIN-2025-0001", "[PLACA]"]},
        ),
    ],
)
def test_redact_value(value: object, expected: object) -> None:
    assert redact_value(value) == expected


def _reset() -> None:
    for handler in logging.getLogger("accident_agent").handlers:
        handler.close()
    logging.getLogger("accident_agent").handlers = []
    structlog.reset_defaults()


@pytest.fixture
def log_file(tmp_path: Path) -> Iterator[Path]:
    configure_logging("INFO", tmp_path, stdout=False)
    yield tmp_path / "agent.jsonl"
    _reset()


def test_events_are_json_lines_with_redaction(log_file: Path) -> None:
    logger = get_logger()
    logger.info(
        "tool_call", tool="search_accidents", params={"text": "cedula 1712345678"}, duration_ms=12
    )
    logger.debug("detalle", x=1)
    lines = log_file.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["event"] == "tool_call"
    assert record["level"] == "info"
    assert record["timestamp"].endswith("Z")
    assert record["params"] == {"text": "cedula [CEDULA]"}
    assert record["duration_ms"] == 12


def test_logs_directory_is_created(tmp_path: Path) -> None:
    configure_logging("WARNING", tmp_path / "nuevo", stdout=False)
    get_logger().warning("aviso")
    assert (tmp_path / "nuevo" / "agent.jsonl").exists()
    _reset()
