"""Puerto de acceso a los siniestros (tarea 3.2) y sus DTOs de lectura.

Las herramientas dependen de este puerto, no de Neo4j. Los DTOs son listas blancas
(`extra="ignore"`): solo salen los campos declarados, sin nombres, cedulas ni placas, aunque el
grafo tuviera otras propiedades.
"""

from collections.abc import Sequence
from datetime import date, datetime
from enum import StrEnum
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from accident_agent.domain.catalogs import (
    AccidentType,
    Cause,
    Lighting,
    PersonCondition,
    PersonRole,
    Protection,
    Province,
    RecordStatus,
    ReportStatus,
    Sex,
    Surface,
    VehicleService,
    VehicleType,
    Weather,
)


class GroupBy(StrEnum):
    PROVINCE = "province"
    CAUSE = "cause"
    ACCIDENT_TYPE = "accident_type"
    MONTH = "month"
    YEAR = "year"
    WEATHER = "weather"
    VEHICLE_TYPE = "vehicle_type"


class AccidentFilters(BaseModel):
    """Filtros ya canonicos: los normaliza la herramienta antes de llamar al repositorio."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    accident_ids: list[str] = Field(default_factory=list)
    province: Province | None = None
    canton: str | None = None
    road_code: str | None = None
    # Fragmento en minusculas y sin tildes del nombre de la via, cuando no trae codigo.
    road_text: str | None = None
    accident_type: AccidentType | None = None
    cause: Cause | None = None
    weather: Weather | None = None
    surface: Surface | None = None
    lighting: Lighting | None = None
    vehicle_type: VehicleType | None = None
    date_from: date | None = None
    date_to: date | None = None
    only_fatal: bool = False
    # Texto libre ya plegado (sin tildes, minusculas); el repositorio lo escapa para Lucene.
    text: str | None = None
    include_annulled: bool = False


class _View(BaseModel):
    # Neo4j no guarda propiedades nulas: los campos opcionales tienen None por defecto.
    model_config = ConfigDict(frozen=True, extra="ignore")


class VehicleView(_View):
    vehicle_id: str
    vehicle_type: VehicleType
    brand: str
    model: str
    year: int
    service: VehicleService


class PersonView(_View):
    person_id: str
    role: PersonRole
    age: int
    sex: Sex
    condition: PersonCondition
    alcohol_gl: float | None = None
    protection: Protection
    days_until_death: int | None = None
    vehicle_id: str | None = None


class AccidentView(_View):
    accident_id: str
    status: RecordStatus
    is_active: bool
    version: int
    versions_count: int
    occurred_at: datetime
    date: date
    accident_type: AccidentType
    cause: Cause
    province: Province
    canton: str
    parish: str
    road: str
    road_code: str | None = None
    km: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    weather: Weather
    surface: Surface
    lighting: Lighting
    damages_usd: float
    deaths: int
    injured: int
    unharmed: int
    summary_mismatch: bool
    narrative: str
    annulment_reason: str | None = None
    replaced_by: str | None = None
    replaces: str | None = None
    vehicles: list[VehicleView]
    people: list[PersonView]


class SearchPage(_View):
    total_found: int
    accidents: list[AccidentView]


class StatsRow(_View):
    group: str
    accidents: int
    deaths: int
    injured: int
    damages_usd: float


class ReportHit(_View):
    report_id: str
    title: str
    date: date
    status: ReportStatus
    road_code: str | None = None
    section_order: int
    section_title: str
    text: str
    score: float | None = None
    supersedes: str | None = None
    superseded_by: str | None = None


class DatasetSummary(_View):
    source: str
    source_file: str
    sha256: str
    generated: date


class RepositoryError(Exception):
    """La base no respondio a tiempo o no esta disponible."""

    def __init__(self, kind: Literal["timeout", "unavailable"], message: str) -> None:
        self.kind: Literal["timeout", "unavailable"] = kind
        super().__init__(message)


class AccidentRepository(Protocol):
    def search(self, filters: AccidentFilters, limit: int) -> SearchPage: ...

    def get_by_ids(self, accident_ids: Sequence[str]) -> list[AccidentView]:
        """Siniestros por id, incluidos los anulados, en el orden pedido; omite los inexistentes."""
        ...

    def stats(self, filters: AccidentFilters, group_by: GroupBy) -> list[StatsRow]: ...

    def search_reports(
        self, text: str | None, road_code: str | None, limit: int
    ) -> list[ReportHit]: ...

    def dataset_info(self) -> DatasetSummary: ...
