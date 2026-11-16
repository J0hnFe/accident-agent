"""Herramienta `generate_accident_report` (seccion 7.4 del plan, tarea 3.5).

Los hechos se vuelven a consultar por id en el repositorio: nunca salen del texto de la
conversacion. Los anulados se muestran con su reemplazo y no suman en los totales. El informe es
Markdown generado con una plantilla Jinja2 y se guarda en `REPORTS_DIR`.
"""

import hashlib
from collections import Counter
from pathlib import Path
from typing import Annotated, Final
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, BeforeValidator, Field, field_validator

from accident_agent.core.clock import Clock
from accident_agent.core.tool import Tool, ToolError, ToolInput
from accident_agent.domain.catalogs import display_label
from accident_agent.domain.models import ACCIDENT_ID_PATTERN
from accident_agent.graph.repository import AccidentRepository, AccidentView, RepositoryError
from accident_agent.ingestion.normalizers import clean_text

TEMPLATES_DIR: Final = Path(__file__).parent / "templates"
UNAVAILABLE_MESSAGE: Final = "La base de datos de siniestros no esta disponible en este momento."


def _upper_id(value: object) -> object:
    return value.strip().upper() if isinstance(value, str) else value


AccidentId = Annotated[str, BeforeValidator(_upper_id), Field(pattern=ACCIDENT_ID_PATTERN)]


class GenerateReportInput(ToolInput):
    accident_ids: list[AccidentId] = Field(
        min_length=1,
        max_length=20,
        description="Ids SIN-AAAA-NNNN de los siniestros del informe (1 a 20).",
    )
    title: str | None = Field(default=None, max_length=120, description="Titulo opcional.")
    include_narrative: bool = Field(
        default=True, description="Incluir la narrativa original de cada parte."
    )
    save_file: bool = Field(default=True, description="Guardar el informe como archivo Markdown.")

    @field_validator("title")
    @classmethod
    def _clean_title(cls, value: str | None) -> str | None:
        return clean_text(value) or None if value is not None else None


class GenerateReportOutput(BaseModel):
    report_id: str | None
    title: str
    generated_at: str
    included_ids: list[str]
    not_found_ids: list[str]
    content_markdown: str
    file_path: str | None
    warnings: list[str]


def _money(value: float) -> str:
    return f"{value:,.2f}"


def _label(value: object) -> str:
    return display_label(str(value))


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
        autoescape=False,  # noqa: S701 - salida Markdown, no HTML
    )
    env.filters["money"] = _money
    env.filters["label"] = _label
    return env


def _warnings(accidents: list[AccidentView], not_found: list[str]) -> list[str]:
    included = {a.accident_id for a in accidents}
    warnings = []
    if not_found:
        warnings.append(f"No se encontraron: {', '.join(not_found)}.")
    for a in accidents:
        if not a.is_active:
            text = f"{a.accident_id} esta anulado y no suma en los totales"
            if a.replaced_by:
                text += f"; lo reemplaza {a.replaced_by}"
                if a.replaced_by not in included:
                    text += " (no incluido en este informe)"
            warnings.append(text + ".")
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


def _counts(values: list[str]) -> list[tuple[str, int]]:
    return sorted(Counter(values).items(), key=lambda item: (-item[1], item[0]))


class GenerateReportTool(Tool[GenerateReportInput, GenerateReportOutput]):
    name = "generate_accident_report"
    description = (
        "Genera un informe en Markdown de uno o varios siniestros por su id (SIN-AAAA-NNNN): "
        "resumen con totales, distribucion por tipo y causa, detalle de cada siniestro y "
        "advertencias de calidad. Los datos se consultan de nuevo en la base. Si el usuario pide "
        "un informe de un conjunto (p. ej. 'siniestros con motocicletas'), obten antes los ids "
        "con search_accidents. Para un seguimiento usa los ids ya consultados."
    )
    input_model = GenerateReportInput
    output_model = GenerateReportOutput

    def __init__(
        self,
        repository: AccidentRepository,
        clock: Clock,
        *,
        reports_dir: Path,
        timezone: str = "America/Guayaquil",
        timeout_seconds: float = 15.0,
    ) -> None:
        self._repository = repository
        self._clock = clock
        self._reports_dir = reports_dir
        self._zone = ZoneInfo(timezone)
        self._timezone = timezone
        self._template = _environment().get_template("report.md.j2")
        self.timeout_seconds = timeout_seconds

    def run(self, params: GenerateReportInput) -> GenerateReportOutput:
        ids = list(dict.fromkeys(params.accident_ids))
        try:
            accidents = self._repository.get_by_ids(ids)
            source = self._repository.dataset_info() if accidents else None
        except RepositoryError as exc:
            raise ToolError(
                "timeout" if exc.kind == "timeout" else "execution", UNAVAILABLE_MESSAGE
            ) from exc

        found = [a.accident_id for a in accidents]
        not_found = [i for i in ids if i not in found]
        generated = self._clock.now().astimezone(self._zone)
        default_title = (
            f"Informe del siniestro {ids[0]}"
            if len(ids) == 1
            else f"Informe de {len(ids)} siniestros"
        )
        title = params.title or default_title
        warnings = _warnings(accidents, not_found)

        if not accidents:
            warnings.append("Ningun siniestro encontrado: no se genero el informe.")
            return GenerateReportOutput(
                report_id=None,
                title=title,
                generated_at=generated.isoformat(timespec="seconds"),
                included_ids=[],
                not_found_ids=not_found,
                content_markdown="",
                file_path=None,
                warnings=warnings,
            )

        digest = hashlib.sha256(",".join(found).encode()).hexdigest()[:6]
        report_id = f"RPT-{generated:%Y%m%d-%H%M%S}-{digest}"
        active = [a for a in accidents if a.is_active]
        content = self._template.render(
            title=title,
            report_id=report_id,
            generated_at=f"{generated:%Y-%m-%d %H:%M} ({self._timezone})",
            source=source,
            included=found,
            not_found=not_found,
            totals={
                "accidents": len(active),
                "deaths": sum(a.deaths for a in active),
                "injured": sum(a.injured for a in active),
                "unharmed": sum(a.unharmed for a in active),
                "damages_usd": sum(a.damages_usd for a in active),
            },
            annulled=[a.accident_id for a in accidents if not a.is_active],
            by_type=[(_label(k), n) for k, n in _counts([a.accident_type for a in active])],
            by_cause=[(_label(k), n) for k, n in _counts([a.cause for a in active])],
            accidents=accidents,
            include_narrative=params.include_narrative,
            warnings=warnings,
        )

        file_path = None
        if params.save_file:
            try:
                self._reports_dir.mkdir(parents=True, exist_ok=True)
                path = self._reports_dir / f"{report_id}.md"
                path.write_text(content, encoding="utf-8")
                file_path = str(path)
            except OSError:
                warnings.append(
                    "No se pudo guardar el archivo del informe; el contenido va en "
                    "content_markdown."
                )

        return GenerateReportOutput(
            report_id=report_id,
            title=title,
            generated_at=generated.isoformat(timespec="seconds"),
            included_ids=found,
            not_found_ids=not_found,
            content_markdown=content,
            file_path=file_path,
            warnings=warnings,
        )
