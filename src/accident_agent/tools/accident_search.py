"""Herramienta `search_accidents`: RAG sobre Neo4j (seccion 7.3 del plan, tarea 3.4).

Normaliza los filtros con las mismas reglas de la ingesta (catalogos, N02 y N03), consulta el
repositorio y agrega advertencias explicitas para que el LLM no complete datos que no existen.
"""

import difflib
from collections.abc import Callable, Mapping
from datetime import date
from enum import StrEnum
from typing import Annotated, Any, Final, Self

from pydantic import BaseModel, BeforeValidator, Field, field_validator, model_validator

from accident_agent.core.tool import Tool, ToolError, ToolInput
from accident_agent.domain import catalogs
from accident_agent.domain.catalogs import (
    AccidentType,
    Cause,
    Lighting,
    Province,
    RecordStatus,
    ReportStatus,
    Surface,
    VehicleType,
    Weather,
)
from accident_agent.domain.models import ACCIDENT_ID_PATTERN
from accident_agent.graph.repository import (
    AccidentFilters,
    AccidentRepository,
    AccidentView,
    GroupBy,
    ReportHit,
    RepositoryError,
    StatsRow,
)
from accident_agent.ingestion import normalizers as norm

MAX_IDS: Final = 20
UNAVAILABLE_MESSAGE: Final = "La base de datos de siniestros no esta disponible en este momento."


class SearchMode(StrEnum):
    SEARCH = "search"
    STATS = "stats"
    REPORTS = "reports"


def _canonical[E: StrEnum](lookup: Mapping[str, E], label: str) -> Callable[[object], object]:
    """Acepta las escrituras del catalogo; ante un valor desconocido sugiere sin repetirlo."""
    options = sorted({member.value for member in lookup.values()})

    def convert(value: object) -> object:
        if value is None or isinstance(value, StrEnum):
            return value
        try:
            return norm.to_canonical(lookup, value)
        except norm.NormalizationError:
            keys = {norm.normalize_key(o): o for o in options}
            close = difflib.get_close_matches(
                norm.normalize_key(str(value)), list(keys), n=3, cutoff=0.6
            )
            hint = f"; quiza: {', '.join(keys[c] for c in close)}" if close else ""
            raise ValueError(
                f"valor de {label} no reconocido{hint}. Valores validos: {', '.join(options)}"
            ) from None

    return convert


def _upper_id(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


AccidentId = Annotated[str, BeforeValidator(_upper_id), Field(pattern=ACCIDENT_ID_PATTERN)]


class SearchAccidentsInput(ToolInput):
    mode: SearchMode = Field(
        default=SearchMode.SEARCH,
        description=(
            "search: lista de siniestros; stats: conteos agrupados (requiere group_by); "
            "reports: busqueda en los informes de analisis."
        ),
    )
    accident_ids: list[AccidentId] | None = Field(
        default=None,
        max_length=MAX_IDS,
        description="Ids SIN-AAAA-NNNN (maximo 20). Incluye anulados si se piden por id.",
    )
    province: Annotated[
        Province | None, BeforeValidator(_canonical(catalogs.PROVINCES, "provincia"))
    ] = Field(default=None, description="Provincia del Ecuador.")
    canton: str | None = Field(default=None, max_length=80, description="Canton, p. ej. Quito.")
    road: str | None = Field(
        default=None,
        max_length=120,
        description="Codigo de via (E35, E45, E15) o parte del nombre (p. ej. 'Via a la Costa').",
    )
    accident_type: Annotated[
        AccidentType | None, BeforeValidator(_canonical(catalogs.ACCIDENT_TYPES, "tipo"))
    ] = None
    cause: Annotated[Cause | None, BeforeValidator(_canonical(catalogs.CAUSES, "causa"))] = None
    weather: Annotated[Weather | None, BeforeValidator(_canonical(catalogs.WEATHERS, "clima"))] = (
        None
    )
    surface: Annotated[
        Surface | None, BeforeValidator(_canonical(catalogs.SURFACES, "superficie"))
    ] = None
    lighting: Annotated[
        Lighting | None, BeforeValidator(_canonical(catalogs.LIGHTINGS, "iluminacion"))
    ] = None
    vehicle_type: Annotated[
        VehicleType | None, BeforeValidator(_canonical(catalogs.VEHICLE_TYPES, "tipo de vehiculo"))
    ] = Field(default=None, description="Siniestros con al menos un vehiculo de este tipo.")
    date_from: date | None = Field(default=None, description="Fecha inicial AAAA-MM-DD, incluida.")
    date_to: date | None = Field(default=None, description="Fecha final AAAA-MM-DD, incluida.")
    only_fatal: bool = Field(default=False, description="Solo siniestros con fallecidos.")
    text: str | None = Field(
        default=None,
        max_length=200,
        description="Palabras a buscar en las narrativas o, con mode=reports, en los informes.",
    )
    group_by: GroupBy | None = Field(default=None, description="Agrupacion para mode=stats.")
    include_annulled: bool = Field(
        default=False, description="Incluir registros anulados (solo para trazabilidad)."
    )
    limit: int = Field(default=10, ge=1, le=50, description="Maximo de resultados (1 a 50).")

    @field_validator("canton", "road", "text")
    @classmethod
    def _blank_is_none(cls, value: str | None) -> str | None:
        return value if value is None or value.strip() else None

    @model_validator(mode="after")
    def _check(self) -> Self:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from no puede ser posterior a date_to")
        if self.mode is SearchMode.STATS and self.group_by is None:
            raise ValueError("group_by es obligatorio cuando mode=stats")
        return self


class SearchAccidentsOutput(BaseModel):
    mode: SearchMode
    total_found: int
    accidents: list[AccidentView] = Field(default_factory=list)
    stats: list[StatsRow] = Field(default_factory=list)
    reports: list[ReportHit] = Field(default_factory=list)
    applied_filters: dict[str, Any]
    warnings: list[str]


# Filtros que no aplican a mode=reports (los informes se filtran por texto y via).
_ACCIDENT_ONLY_FIELDS: Final = (
    "accident_ids",
    "province",
    "canton",
    "accident_type",
    "cause",
    "weather",
    "surface",
    "lighting",
    "vehicle_type",
    "date_from",
    "date_to",
    "only_fatal",
    "group_by",
    "include_annulled",
)


def _filters(params: SearchAccidentsInput) -> AccidentFilters:
    road_code = road_text = None
    if params.road:
        road = norm.normalize_road(params.road)
        road_code = road.code
        road_text = None if road.code else norm.normalize_key(params.road)
    text = norm.normalize_key(params.text) if params.text else None
    return AccidentFilters(
        accident_ids=params.accident_ids or [],
        province=params.province,
        canton=norm.display_name(params.canton) if params.canton else None,
        road_code=road_code,
        road_text=road_text,
        accident_type=params.accident_type,
        cause=params.cause,
        weather=params.weather,
        surface=params.surface,
        lighting=params.lighting,
        vehicle_type=params.vehicle_type,
        date_from=params.date_from,
        date_to=params.date_to,
        only_fatal=params.only_fatal,
        text=text or None,
        include_annulled=params.include_annulled,
    )


def _accident_warnings(accidents: list[AccidentView]) -> list[str]:
    warnings = []
    for a in accidents:
        if a.status is RecordStatus.ANULADO:
            reason = f" ({a.annulment_reason})" if a.annulment_reason else ""
            replacement = f"; lo reemplaza {a.replaced_by}" if a.replaced_by else ""
            warnings.append(
                f"{a.accident_id} esta ANULADO{reason}{replacement}. No cuenta en estadisticas."
            )
        if a.replaces:
            warnings.append(f"{a.accident_id} reemplaza al registro anulado {a.replaces}.")
        if a.summary_mismatch:
            warnings.append(
                f"{a.accident_id}: el resumen original del parte no coincide con las personas "
                "registradas; los conteos se calcularon a partir de las personas."
            )
        for person in a.people:
            if person.days_until_death is not None:
                warnings.append(
                    f"{a.accident_id}: una persona fallecio {person.days_until_death} dias despues "
                    "del siniestro; cuenta como fallecida (hasta 30 dias, INF-2026-02)."
                )
    return warnings


def _report_warnings(reports: list[ReportHit]) -> list[str]:
    first_hit: dict[str, ReportHit] = {}
    for hit in reports:
        first_hit.setdefault(hit.report_id, hit)
    warnings = []
    for report_id, hit in sorted(first_hit.items()):
        if hit.superseded_by:
            warnings.append(
                f"{report_id} fue REEMPLAZADO por {hit.superseded_by}; prioriza el informe vigente."
            )
        elif hit.status is ReportStatus.REEMPLAZADO:
            warnings.append(f"{report_id} esta en estado reemplazado.")
    return warnings


class SearchAccidentsTool(Tool[SearchAccidentsInput, SearchAccidentsOutput]):
    name = "search_accidents"
    description = (
        "Consulta los siniestros de transito del Ecuador guardados en la base (unica fuente de "
        "hechos). mode=search lista siniestros con su detalle; mode=stats cuenta y suma por "
        "group_by (provincia, causa, tipo, mes, anio, clima o tipo de vehiculo); "
        "mode=reports busca en los informes de analisis (causas de una via, definiciones como "
        "'estrellamiento'). "
        "Los filtros se combinan. Los registros anulados se excluyen salvo que se pidan por id. "
        "Para fechas relativas ('ultimos 6 meses') llama antes a get_current_time y usa "
        "date_from y date_to. Si total_found es 0, informa que no hay datos."
    )
    input_model = SearchAccidentsInput
    output_model = SearchAccidentsOutput

    def __init__(self, repository: AccidentRepository, *, timeout_seconds: float = 10.0) -> None:
        self._repository = repository
        self.timeout_seconds = timeout_seconds

    def run(self, params: SearchAccidentsInput) -> SearchAccidentsOutput:
        filters = _filters(params)
        applied = {
            "mode": params.mode.value,
            "limit": params.limit,
            **filters.model_dump(mode="json", exclude_defaults=True),
        }
        if params.group_by:
            applied["group_by"] = params.group_by.value
        try:
            if params.mode is SearchMode.REPORTS:
                return self._reports(params, filters, applied)
            if params.mode is SearchMode.STATS:
                return self._stats(params, filters, applied)
            return self._search(params, filters, applied)
        except RepositoryError as exc:
            raise ToolError(
                "timeout" if exc.kind == "timeout" else "execution", UNAVAILABLE_MESSAGE
            ) from exc

    def _search(
        self, params: SearchAccidentsInput, filters: AccidentFilters, applied: dict[str, Any]
    ) -> SearchAccidentsOutput:
        if params.group_by:
            applied.pop("group_by")
        # Con ids explicitos el limite los cubre a todos, para no darlos por inexistentes.
        limit = max(params.limit, len(filters.accident_ids))
        page = self._repository.search(filters, limit)
        warnings = []
        if page.total_found == 0:
            warnings.append(
                "No hay siniestros que cumplan los filtros aplicados; no completes con otros datos."
            )
        elif len(page.accidents) < page.total_found:
            warnings.append(
                f"Se muestran {len(page.accidents)} de {page.total_found}; usa filtros mas "
                "especificos o limit (maximo 50)."
            )
        returned = {a.accident_id for a in page.accidents}
        if missing := [i for i in filters.accident_ids if i not in returned]:
            warnings.append(f"No existen o no cumplen los filtros: {', '.join(missing)}.")
        warnings += _accident_warnings(page.accidents)
        return SearchAccidentsOutput(
            mode=params.mode,
            total_found=page.total_found,
            accidents=page.accidents,
            applied_filters=applied,
            warnings=warnings,
        )

    def _stats(
        self, params: SearchAccidentsInput, filters: AccidentFilters, applied: dict[str, Any]
    ) -> SearchAccidentsOutput:
        if params.group_by is None:
            raise ToolError("validation", "group_by es obligatorio cuando mode=stats")
        rows = self._repository.stats(filters, params.group_by)
        total = self._repository.search(filters, 1).total_found
        warnings = []
        if total == 0:
            warnings.append(
                "No hay siniestros que cumplan los filtros aplicados; no completes con otros datos."
            )
        if params.group_by is GroupBy.VEHICLE_TYPE:
            warnings.append(
                "Un siniestro con varios tipos de vehiculo cuenta en cada grupo: la suma de los "
                "grupos puede superar total_found."
            )
        if not params.include_annulled:
            warnings.append("Las estadisticas excluyen los registros anulados.")
        return SearchAccidentsOutput(
            mode=params.mode,
            total_found=total,
            stats=rows,
            applied_filters=applied,
            warnings=warnings,
        )

    def _reports(
        self, params: SearchAccidentsInput, filters: AccidentFilters, applied: dict[str, Any]
    ) -> SearchAccidentsOutput:
        hits = self._repository.search_reports(filters.text, filters.road_code, params.limit)
        warnings = []
        ignored = [f for f in _ACCIDENT_ONLY_FIELDS if f in params.model_fields_set]
        if ignored:
            warnings.append(
                f"En mode=reports se ignoran los filtros: {', '.join(ignored)}. "
                "Para siniestros usa mode=search."
            )
            for name in ignored:
                applied.pop(name, None)
        if filters.road_text:
            warnings.append("Los informes solo se filtran por codigo de via (p. ej. E35).")
            applied.pop("road_text", None)
        if not hits:
            warnings.append("No hay informes que coincidan; no completes con otros datos.")
        warnings += _report_warnings(hits)
        return SearchAccidentsOutput(
            mode=params.mode,
            total_found=len(hits),
            reports=hits,
            applied_filters=applied,
            warnings=warnings,
        )
