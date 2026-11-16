"""Logs estructurados en JSON (seccion 7.8 del plan, tarea 4.6).

Cada evento (`request`, `llm_call`, `tool_call`, `grounding_violation`, `tracer_error`) es una
linea JSON en stdout y en `logs/agent.jsonl`. Antes de escribir se redactan todos los textos:
datos personales con los patrones de la regla P6 y claves de API.
"""

import logging
import re
import sys
from collections.abc import MutableMapping
from pathlib import Path
from typing import Any, Final

import structlog

from accident_agent.domain.privacy import redact

_SECRETS: Final = re.compile(r"\b(?:sk-or-v1-[A-Za-z0-9]+|sk-lf-[A-Za-z0-9-]+|pk-lf-[A-Za-z0-9-]+)")
LOG_FILE_NAME: Final = "agent.jsonl"


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(_SECRETS.sub("[SECRETO]", value))
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [redact_value(v) for v in value]
    return value


def _redact(_: Any, __: str, event_dict: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    return {k: redact_value(v) for k, v in event_dict.items()}


def configure_logging(
    level: str = "INFO", logs_dir: Path | None = None, *, stdout: bool = True
) -> None:
    """stdout=False para la CLI interactiva: los logs van solo al archivo."""
    handlers: list[logging.Handler] = []
    if stdout:
        handlers.append(logging.StreamHandler(sys.stdout))
    if logs_dir is not None:
        logs_dir.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(logs_dir / LOG_FILE_NAME, encoding="utf-8"))
    root = logging.getLogger("accident_agent")
    root.handlers = handlers
    root.setLevel(logging.DEBUG)
    root.propagate = False
    for handler in handlers:
        handler.setFormatter(logging.Formatter("%(message)s"))

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,
    )


def get_logger() -> Any:
    return structlog.get_logger("accident_agent")
