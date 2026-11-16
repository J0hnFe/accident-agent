"""Modelos de dominio estrictos y canonicos (tarea 1.8).

Es lo que produce el pipeline (tarea 2.2) y lo que se escribe en Neo4j. Reglas:
- Estrictos, inmutables y sin campos extra: solo entran valores ya normalizados (enums de
  `catalogs`, numeros y fechas), nunca textos sin convertir.
- Sin datos personales: no hay campos para nombre, cedula ni placa, y `extra="forbid"` impide
  agregarlos.
- Los conteos y los derivados de la fecha se calculan, de modo que no pueden contradecirse.
- Las invariantes de `docs/datos/reglas_normalizacion.md` (R01 a R05) se validan aqui.
"""

import datetime as dt
from collections import Counter
from collections.abc import Iterable
from typing import Annotated, Literal, Self

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
    model_validator,
)

from accident_agent.domain.catalogs import (
    AccidentType,
    Cause,
    Classification,
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

ACCIDENT_ID_PATTERN = r"^SIN-\d{4}-\d{4}$"
REPORT_ID_PATTERN = r"^INF-\d{4}-\d{2}$"


def _clean(value: str) -> str:
    if not value or value != " ".join(value.split()):
        raise ValueError("texto vacio o con espacios sin normalizar")
    return value


def _upper(value: str) -> str:
    if value != value.upper():
        raise ValueError("se esperaba texto en mayusculas")
    return value


CleanText = Annotated[str, AfterValidator(_clean)]
UpperText = Annotated[str, AfterValidator(_clean), AfterValidator(_upper)]
AccidentId = Annotated[str, Field(pattern=ACCIDENT_ID_PATTERN)]
ReportId = Annotated[str, Field(pattern=REPORT_ID_PATTERN)]
RoadCode = Annotated[str, Field(pattern=r"^E\d{2,3}$")]


def _duplicates(ids: Iterable[str]) -> list[str]:
    return sorted(i for i, n in Counter(ids).items() if n > 1)


class _DomainModel(BaseModel):
    model_config = ConfigDict(strict=True, frozen=True, extra="forbid")


class Vehicle(_DomainModel):
    vehicle_id: Annotated[str, Field(pattern=r"^SIN-\d{4}-\d{4}-V\d+$")]
    vehicle_type: VehicleType
    brand: UpperText
    model: UpperText
    year: int = Field(ge=1900, le=2100)
    service: VehicleService


class Person(_DomainModel):
    person_id: Annotated[str, Field(pattern=r"^SIN-\d{4}-\d{4}-P\d+$")]
    role: PersonRole
    age: int = Field(ge=0, le=120)
    sex: Sex
    condition: PersonCondition
    alcohol_gl: float | None = Field(ge=0)
    protection: Protection
    # INF-2026-02 cuenta como fallecido a quien muere hasta 30 dias despues del siniestro.
    days_until_death: int | None = Field(ge=0, le=30)
    vehicle_id: Annotated[str, Field(pattern=r"^SIN-\d{4}-\d{4}-V\d+$")] | None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.days_until_death is not None and self.condition is not PersonCondition.FALLECIDO:
            raise ValueError("days_until_death solo aplica a personas fallecidas")
        if self.role is PersonRole.PEATON and self.vehicle_id is not None:
            raise ValueError("un peaton no viaja en un vehiculo")
        return self


class Location(_DomainModel):
    province: Province
    canton: CleanText
    parish: CleanText
    road: CleanText
    road_code: RoadCode | None
    km: float | None = Field(ge=0)
    latitude: float | None = Field(ge=-90, le=90)
    longitude: float | None = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("latitud y longitud van juntas o ambas null")
        return self


class Accident(_DomainModel):
    accident_id: AccidentId
    version: int = Field(ge=1)
    versions_count: int = Field(ge=1)
    status: RecordStatus
    updated_at: dt.date
    occurred_at: AwareDatetime
    accident_type: AccidentType
    cause: Cause
    weather: Weather
    surface: Surface
    lighting: Lighting
    damages_usd: float = Field(ge=0)
    location: Location
    vehicles: list[Vehicle] = Field(min_length=1)
    people: list[Person] = Field(min_length=1)
    summary_mismatch: bool
    narrative: CleanText
    annulment_reason: CleanText | None
    replaced_by: AccidentId | None

    @computed_field  # type: ignore[prop-decorator]
    @property
    def is_active(self) -> bool:
        return self.status is RecordStatus.VIGENTE

    @computed_field  # type: ignore[prop-decorator]
    @property
    def date(self) -> dt.date:
        return self.occurred_at.date()

    @computed_field  # type: ignore[prop-decorator]
    @property
    def year(self) -> int:
        return self.occurred_at.year

    @computed_field  # type: ignore[prop-decorator]
    @property
    def month(self) -> int:
        return self.occurred_at.month

    @computed_field  # type: ignore[prop-decorator]
    @property
    def hour(self) -> int:
        return self.occurred_at.hour

    def _count(self, *conditions: PersonCondition) -> int:
        return sum(p.condition in conditions for p in self.people)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def deaths(self) -> int:
        return self._count(PersonCondition.FALLECIDO)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def injured(self) -> int:
        return self._count(PersonCondition.HERIDO_GRAVE, PersonCondition.HERIDO_LEVE)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def unharmed(self) -> int:
        return self._count(PersonCondition.ILESO)

    @model_validator(mode="after")
    def _check(self) -> Self:
        prefix = f"{self.accident_id}-"
        vehicle_ids = [v.vehicle_id for v in self.vehicles]
        person_ids = [p.person_id for p in self.people]
        if any(not i.startswith(prefix) for i in vehicle_ids + person_ids):
            raise ValueError(f"los ids de vehiculos y personas deben empezar con {prefix}")
        if repeated := _duplicates(vehicle_ids + person_ids):
            raise ValueError(f"ids duplicados en el siniestro: {repeated}")
        unknown = {p.vehicle_id for p in self.people if p.vehicle_id} - set(vehicle_ids)
        if unknown:
            raise ValueError(f"personas enlazadas a vehiculos inexistentes: {sorted(unknown)}")
        if self.status is RecordStatus.VIGENTE and (self.annulment_reason or self.replaced_by):
            raise ValueError("annulment_reason y replaced_by solo aplican a anulados")
        if self.replaced_by == self.accident_id:
            raise ValueError("un siniestro no puede reemplazarse a si mismo")
        if self.occurred_at.date() > self.updated_at:
            raise ValueError("la fecha del siniestro es posterior a su actualizacion")
        return self


class ReportSection(_DomainModel):
    order: int = Field(ge=1)
    title: CleanText
    text: CleanText = Field(repr=False)


class Report(_DomainModel):
    report_id: ReportId
    title: CleanText
    date: dt.date
    status: ReportStatus
    # Solo informes publicos: uno reservado no se puede ni construir (regla P3).
    classification: Literal[Classification.PUBLICO]
    road: CleanText | None
    road_code: RoadCode | None
    supersedes: ReportId | None
    sections: list[ReportSection] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> Self:
        if [s.order for s in self.sections] != list(range(1, len(self.sections) + 1)):
            raise ValueError("las secciones deben numerarse 1..n en orden")
        if self.supersedes == self.report_id:
            raise ValueError("un informe no puede reemplazarse a si mismo")
        if self.road_code is not None and self.road is None:
            raise ValueError("road_code requiere road")
        return self


class CleanDataset(_DomainModel):
    """Resultado completo del pipeline, con la integridad referencial ya verificada."""

    accidents: list[Accident]
    reports: list[Report]

    @model_validator(mode="after")
    def _check(self) -> Self:
        accidents = {a.accident_id: a for a in self.accidents}
        reports = {r.report_id: r for r in self.reports}
        if repeated := _duplicates(a.accident_id for a in self.accidents):
            raise ValueError(f"accident_id duplicado: {repeated}")
        if repeated := _duplicates(r.report_id for r in self.reports):
            raise ValueError(f"report_id duplicado: {repeated}")
        for accident in self.accidents:
            if accident.replaced_by is None:
                continue
            target = accidents.get(accident.replaced_by)
            if target is None:
                raise ValueError(
                    f"{accident.accident_id} apunta a {accident.replaced_by}, inexistente"
                )
            if not target.is_active:
                raise ValueError(f"el reemplazo {target.accident_id} debe estar vigente")
        for report in self.reports:
            if report.supersedes is None:
                continue
            previous = reports.get(report.supersedes)
            if previous is None:
                raise ValueError(f"{report.report_id} reemplaza a {report.supersedes}, inexistente")
            if previous.status is not ReportStatus.REEMPLAZADO:
                raise ValueError(f"{previous.report_id} debe estar en estado reemplazado")
        return self
