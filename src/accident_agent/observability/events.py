"""Interfaz minima de log de eventos que usa el nucleo (structlog la cumple)."""

from typing import Any, Protocol


class EventLogger(Protocol):
    def info(self, event: str, **fields: Any) -> Any: ...

    def warning(self, event: str, **fields: Any) -> Any: ...
