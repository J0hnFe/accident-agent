"""Herramienta `get_current_time` (seccion 7.2 del plan)."""

from typing import Final
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, Field, field_validator

from accident_agent.core.clock import Clock
from accident_agent.core.tool import Tool, ToolInput

WEEKDAYS: Final = ("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo")


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        # Sin repetir el valor recibido: la regla es no devolver lo que escribio el usuario.
        raise ValueError("zona horaria IANA no valida (p. ej. America/Guayaquil)") from None


class CurrentTimeInput(ToolInput):
    timezone: str | None = Field(
        default=None,
        max_length=64,
        description=(
            "Zona horaria IANA, por ejemplo America/Guayaquil o Europe/Madrid. "
            "Si se omite, se usa la zona por defecto del sistema (Ecuador)."
        ),
    )

    @field_validator("timezone")
    @classmethod
    def _valid_zone(cls, value: str | None) -> str | None:
        if value is not None:
            _zone(value)
        return value


class CurrentTimeOutput(BaseModel):
    iso_datetime: str
    date: str
    time: str
    weekday: str
    timezone: str
    utc_offset: str
    unix_timestamp: int


class CurrentTimeTool(Tool[CurrentTimeInput, CurrentTimeOutput]):
    name = "get_current_time"
    description = (
        "Devuelve la fecha y la hora actuales. Usala para responder que hora o que dia es, y "
        "para convertir fechas relativas (por ejemplo 'ultimos 6 meses' o 'este anio') en fechas "
        "exactas antes de buscar siniestros."
    )
    input_model = CurrentTimeInput
    output_model = CurrentTimeOutput

    def __init__(
        self, clock: Clock, *, default_timezone: str, timeout_seconds: float = 2.0
    ) -> None:
        _zone(default_timezone)
        self._clock = clock
        self._default_timezone = default_timezone
        self.timeout_seconds = timeout_seconds

    def run(self, params: CurrentTimeInput) -> CurrentTimeOutput:
        zone_name = params.timezone or self._default_timezone
        now = self._clock.now().astimezone(_zone(zone_name))
        offset = now.isoformat()[-6:] if now.utcoffset() else "+00:00"
        return CurrentTimeOutput(
            iso_datetime=now.isoformat(timespec="seconds"),
            date=now.date().isoformat(),
            time=now.strftime("%H:%M:%S"),
            weekday=WEEKDAYS[now.weekday()],
            timezone=zone_name,
            utc_offset=offset,
            unix_timestamp=int(now.timestamp()),
        )
