"""Reloj inyectable: las herramientas no leen la hora del sistema directamente (pruebas)."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime:
        """Instante actual con zona horaria."""
        ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FixedClock:
    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None:
            raise ValueError("FixedClock requiere un datetime con zona horaria")
        self._instant = instant

    def now(self) -> datetime:
        return self._instant
