"""Reporte de calidad de datos en Markdown (tarea 1.9).

Combina dos fuentes:
- el perfilado de la tarea 1.1 (`quality_report`): estado del JSON original y anomalias;
- los normalizadores de la tarea 1.7 aplicados sobre `RawDataset`: efecto de cada regla.

La salida es determinista (sin fechas de ejecucion) para que la misma entrada genere siempre el
mismo archivo y una prueba pueda comprobar que el reporte versionado esta al dia. Hereda la
privacidad de sus fuentes: el perfilado no muestra nombre, cedula, placa ni textos libres, y
`RawDataset` descarta nombre, cedula e informes reservados al leer.

Uso: uv run python -m accident_agent.ingestion.quality_markdown [ruta] [--output archivo]
"""

import argparse
import hashlib
import json
import sys
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict

from accident_agent.domain import catalogs
from accident_agent.ingestion import normalizers as norm
from accident_agent.ingestion.quality_report import DatasetProfile, ValueCount, profile_data
from accident_agent.ingestion.raw_models import RawDataset, RawRecord

REGENERATE_COMMAND: Final = (
    "uv run python -m accident_agent.ingestion.quality_markdown "
    "--output docs/datos/reporte_calidad_datos.md"
)
TOP_VALUES: Final = 5


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class CategoricalSummary(_Frozen):
    path: str
    rule: str
    total: int
    raw_distinct: int
    canonical_distinct: int
    distribution: list[ValueCount]


class NumericSummary(_Frozen):
    path: str
    rule: str
    present: int
    nulls: int
    minimum: float | None
    maximum: float | None


class DateSummary(_Frozen):
    path: str
    rule: str
    count: int
    minimum: str
    maximum: str


class NormalizationSummary(_Frozen):
    categorical: list[CategoricalSummary]
    numeric: list[NumericSummary]
    dates: list[DateSummary]
    cleaned_narratives: int
    excluded_report_ids: list[str]


def _plain(value: Any) -> Any:
    # Los normalizadores reciben valores JSON; los objetos anidados llegan como modelos crudos.
    return value.model_dump() if isinstance(value, BaseModel) else value


def _vehicles(ds: RawDataset) -> list[Any]:
    return [v for r in ds.registros for v in r.vehiculos]


def _people(ds: RawDataset) -> list[Any]:
    return [p for r in ds.registros for p in r.personas]


def _brand(vehicle: Any) -> str:
    return str(vehicle.marca_modelo.split()[0] if vehicle.marca_modelo else vehicle.marca)


def _canonical_brand(vehicle: Any) -> str:
    return norm.split_brand_model(vehicle.marca_modelo, vehicle.marca, vehicle.modelo)[0]


def _records(get: Callable[[RawRecord], Any]) -> Callable[[RawDataset], list[Any]]:
    return lambda ds: [get(r) for r in ds.registros]


# (ruta, regla, valores originales, normalizador)
_CATEGORICAL: Final[
    list[tuple[str, str, Callable[[RawDataset], list[Any]], Callable[[Any], str]]]
] = [
    (
        "registros[].estado",
        "3.1",
        _records(lambda r: r.estado),
        lambda v: norm.to_canonical(catalogs.RECORD_STATUSES, v),
    ),
    (
        "registros[].tipo_siniestro",
        "3.1",
        _records(lambda r: r.tipo_siniestro),
        lambda v: norm.to_canonical(catalogs.ACCIDENT_TYPES, v),
    ),
    (
        "registros[].causa_probable",
        "3.1",
        _records(lambda r: r.causa_probable),
        lambda v: norm.to_canonical(catalogs.CAUSES, v),
    ),
    (
        "registros[].condiciones.clima",
        "3.1",
        _records(lambda r: r.condiciones.clima),
        lambda v: norm.to_canonical(catalogs.WEATHERS, v),
    ),
    (
        "registros[].condiciones.superficie",
        "3.1",
        _records(lambda r: r.condiciones.superficie),
        lambda v: norm.to_canonical(catalogs.SURFACES, v),
    ),
    (
        "registros[].condiciones.iluminacion",
        "3.1",
        _records(lambda r: r.condiciones.iluminacion),
        lambda v: norm.to_canonical(catalogs.LIGHTINGS, v),
    ),
    (
        "registros[].ubicacion.provincia",
        "3.2",
        _records(lambda r: r.ubicacion.provincia),
        lambda v: norm.to_canonical(catalogs.PROVINCES, v),
    ),
    (
        "registros[].ubicacion.canton",
        "N02",
        _records(lambda r: r.ubicacion.canton),
        norm.display_name,
    ),
    (
        "registros[].ubicacion.parroquia",
        "N02",
        _records(lambda r: r.ubicacion.parroquia),
        norm.display_name,
    ),
    (
        "registros[].ubicacion.via",
        "N03",
        _records(lambda r: r.ubicacion.via),
        lambda v: norm.normalize_road(v).name,
    ),
    (
        "registros[].vehiculos[].tipo_vehiculo",
        "3.1",
        lambda ds: [v.tipo_vehiculo for v in _vehicles(ds)],
        lambda v: norm.to_canonical(catalogs.VEHICLE_TYPES, v),
    ),
    (
        "registros[].vehiculos[].servicio",
        "3.1",
        lambda ds: [v.servicio for v in _vehicles(ds)],
        lambda v: norm.to_canonical(catalogs.VEHICLE_SERVICES, v),
    ),
    ("registros[].vehiculos[].marca", "N11", lambda ds: _vehicles(ds), _canonical_brand),
    (
        "registros[].personas[].rol",
        "3.1",
        lambda ds: [p.rol for p in _people(ds)],
        lambda v: norm.to_canonical(catalogs.PERSON_ROLES, v),
    ),
    (
        "registros[].personas[].condicion",
        "3.1",
        lambda ds: [p.condicion for p in _people(ds)],
        lambda v: norm.to_canonical(catalogs.PERSON_CONDITIONS, v),
    ),
    (
        "registros[].personas[].sexo",
        "3.1",
        lambda ds: [p.sexo for p in _people(ds)],
        lambda v: norm.to_canonical(catalogs.SEXES, v),
    ),
    (
        "registros[].personas[].proteccion",
        "3.1",
        lambda ds: [p.proteccion for p in _people(ds)],
        norm.normalize_protection,
    ),
    (
        "informes[].estado",
        "3.1",
        lambda ds: [i.estado for i in ds.informes],
        lambda v: norm.to_canonical(catalogs.REPORT_STATUSES, v),
    ),
]

_NUMERIC: Final[list[tuple[str, str, Callable[[RawDataset], list[Any]], Callable[[Any], Any]]]] = [
    (
        "registros[].danos_materiales",
        "N06",
        _records(lambda r: r.danos_materiales),
        norm.parse_amount,
    ),
    ("registros[].ubicacion.km", "N07", _records(lambda r: r.ubicacion.km), norm.parse_km),
    (
        "registros[].ubicacion.coordenadas (latitud)",
        "N08",
        _records(lambda r: r.ubicacion.coordenadas),
        lambda v: norm.parse_coordinates(_plain(v))[0],
    ),
    (
        "registros[].ubicacion.coordenadas (longitud)",
        "N08",
        _records(lambda r: r.ubicacion.coordenadas),
        lambda v: norm.parse_coordinates(_plain(v))[1],
    ),
    (
        "registros[].vehiculos[].anio",
        "N10",
        lambda ds: [v.anio for v in _vehicles(ds)],
        norm.parse_int,
    ),
    (
        "registros[].personas[].edad",
        "N10",
        lambda ds: [p.edad for p in _people(ds)],
        norm.parse_int,
    ),
    (
        "registros[].personas[].alcohol_gl",
        "N09",
        lambda ds: [p.alcohol_gl for p in _people(ds)],
        norm.parse_alcohol,
    ),
]


def _raw_key(value: Any) -> str:
    return _brand(value) if hasattr(value, "tipo_vehiculo") else json.dumps(value)


def _distribution(values: Iterable[str]) -> list[ValueCount]:
    ranked = sorted(Counter(values).items(), key=lambda item: (-item[1], item[0]))
    return [ValueCount(value=v, count=c) for v, c in ranked]


def summarize_normalization(raw: RawDataset) -> NormalizationSummary:
    """Aplica los normalizadores a cada campo y resume el antes y el despues."""
    categorical = []
    for path, rule, get, normalize in _CATEGORICAL:
        values = get(raw)
        canonical = [str(normalize(v)) for v in values]
        categorical.append(
            CategoricalSummary(
                path=path,
                rule=rule,
                total=len(values),
                raw_distinct=len({_raw_key(v) for v in values}),
                canonical_distinct=len(set(canonical)),
                distribution=_distribution(canonical),
            )
        )

    numeric = []
    for path, rule, get, parse in _NUMERIC:
        parsed = [parse(v) for v in get(raw)]
        present = [float(p) for p in parsed if p is not None]
        numeric.append(
            NumericSummary(
                path=path,
                rule=rule,
                present=len(present),
                nulls=len(parsed) - len(present),
                minimum=min(present, default=None),
                maximum=max(present, default=None),
            )
        )

    occurred = [norm.parse_occurred_at(_plain(r.fecha_hora)) for r in raw.registros]
    updated = [norm.parse_update_date(r.fecha_actualizacion) for r in raw.registros]
    report_dates = [norm.parse_report_date(i.fecha) for i in raw.informes]
    dates = [
        DateSummary(
            path="registros[].fecha_hora",
            rule="N04",
            count=len(occurred),
            minimum=min(occurred).isoformat(),
            maximum=max(occurred).isoformat(),
        ),
        DateSummary(
            path="registros[].fecha_actualizacion",
            rule="N05",
            count=len(updated),
            minimum=min(updated).isoformat(),
            maximum=max(updated).isoformat(),
        ),
        DateSummary(
            path="informes[].fecha",
            rule="N05",
            count=len(report_dates),
            minimum=min(report_dates).isoformat(),
            maximum=max(report_dates).isoformat(),
        ),
    ]

    return NormalizationSummary(
        categorical=categorical,
        numeric=numeric,
        dates=dates,
        cleaned_narratives=sum(norm.clean_text(r.narrativa) != r.narrativa for r in raw.registros),
        excluded_report_ids=list(raw.excluded_report_ids),
    )


def markdown_cell(value: str | None) -> str:
    """Valor original citado entre comillas invertidas, como pide la convencion ASCII."""
    if value is None:
        return "null"
    text = value if value else '""'
    return "`" + text.replace("|", "\\|") + "`"


def _number(value: float | None) -> str:
    return "-" if value is None else f"{value:g}"


def _table(header: list[str], rows: Iterable[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join("---" for _ in header) + " |"]
    lines += ["| " + " | ".join(row) + " |" for row in rows]
    return lines


def _top(values: list[ValueCount], limit: int | None = TOP_VALUES) -> str:
    shown = values if limit is None else values[:limit]
    text = ", ".join(f"{markdown_cell(v.value)} ({v.count})" for v in shown)
    return text + (", ..." if limit is not None and len(values) > limit else "")


def render_markdown(profile: DatasetProfile, summary: NormalizationSummary) -> str:
    anomaly_counts = Counter(a.code.value for a in profile.anomalies)
    lines = [
        "# Reporte de calidad de datos",
        "",
        "Archivo generado por codigo (tarea 1.9); no se edita a mano. Para regenerarlo:",
        "",
        f"`{REGENERATE_COMMAND}`",
        "",
        f"- **Archivo:** `{profile.source_file}`.",
        f"- **SHA-256:** `{profile.sha256}`.",
        f"- **Extracto generado:** {markdown_cell(str(profile.metadata.get('generado')))}.",
        "- **Privacidad:** no se muestran nombres, cedulas, placas ni textos libres "
        "(narrativas y secciones de informes); de esos campos solo hay conteos.",
        "- **Referencias:** decisiones en `docs/datos/catalogo_anomalias.md`; reglas en "
        "`docs/datos/reglas_normalizacion.md`. Los valores entre comillas invertidas son "
        "textos originales del JSON.",
        "",
        "## 1. Resumen",
        "",
        *_table(
            ["Indicador", "Valor"],
            [
                ["Registros", str(profile.record_count)],
                ["Informes", str(profile.report_count)],
                ["Rutas perfiladas", str(len(profile.fields))],
                ["Anomalias detectadas", str(len(profile.anomalies))],
                ["Informes excluidos al leer", ", ".join(summary.excluded_report_ids) or "-"],
                ["Narrativas con espacios corregidos (N12)", str(summary.cleaned_narratives)],
            ],
        ),
        "",
        "Anomalias por codigo:",
        "",
        *_table(
            ["Codigo", "Cantidad"],
            [[f"`{code}`", str(n)] for code, n in sorted(anomaly_counts.items())],
        ),
        "",
        "## 2. Anomalias detectadas",
        "",
        *_table(
            ["Codigo", "Ruta", "Detalle", "Casos", "Registros"],
            [
                [
                    f"`{a.code.value}`",
                    f"`{a.path}`",
                    markdown_cell(a.detail)[1:-1].replace("`", "'"),
                    str(a.count),
                    ", ".join(a.record_ids) or "-",
                ]
                for a in profile.anomalies
            ],
        ),
        "",
        "## 3. Perfil por campo (JSON original)",
        "",
        "Valores mas frecuentes en formato JSON (los textos van entre comillas dobles).",
        "",
        *_table(
            ["Ruta", "Presentes", "Ausentes", "Nulos", "Vacios", "Tipos", "Distintos", "Valores"],
            [
                [
                    f"`{f.path}`",
                    str(f.present),
                    str(f.absent),
                    str(f.nulls),
                    str(f.empty_strings),
                    ", ".join(f"{t} ({n})" for t, n in sorted(f.types.items())),
                    str(f.distinct),
                    "(oculto: dato personal)"
                    if f.sensitive
                    else f"(texto libre: {f.min_length} a {f.max_length} caracteres)"
                    if f.free_text
                    else _top(f.top_values),
                ]
                for f in profile.fields
            ],
        ),
        "",
        "## 4. Resultado de la normalizacion",
        "",
        f"Conteos sobre los {profile.record_count} registros del archivo, antes de quedarse con "
        "una version por siniestro (R01) y sin excluir anulados (R02). Por eso pueden diferir de "
        "los valores de control de la Etapa 2, que cuentan siniestros vigentes.",
        "",
        "### 4.1 Valores categoricos",
        "",
        *_table(
            ["Campo", "Escrituras originales", "Valores canonicos", "Regla", "Distribucion"],
            [
                [
                    f"`{c.path}`",
                    str(c.raw_distinct),
                    str(c.canonical_distinct),
                    c.rule,
                    _top(c.distribution, limit=None),
                ]
                for c in summary.categorical
            ],
        ),
        "",
        "### 4.2 Valores numericos",
        "",
        *_table(
            ["Campo", "Con dato", "Null", "Minimo", "Maximo", "Regla"],
            [
                [
                    f"`{n.path}`",
                    str(n.present),
                    str(n.nulls),
                    _number(n.minimum),
                    _number(n.maximum),
                    n.rule,
                ]
                for n in summary.numeric
            ],
        ),
        "",
        "### 4.3 Fechas",
        "",
        *_table(
            ["Campo", "Valores", "Minimo", "Maximo", "Regla"],
            [[f"`{d.path}`", str(d.count), d.minimum, d.maximum, d.rule] for d in summary.dates],
        ),
        "",
    ]
    return "\n".join(lines)


def build_report(path: Path) -> str:
    raw = path.read_bytes()
    profile = profile_data(
        json.loads(raw), source_file=path.name, sha256=hashlib.sha256(raw).hexdigest()
    )
    summary = summarize_normalization(RawDataset.model_validate_json(raw))
    return render_markdown(profile, summary)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reporte de calidad de datos en Markdown.")
    parser.add_argument("path", nargs="?", type=Path, help="Ruta del JSON (por defecto DATA_FILE)")
    parser.add_argument("--output", type=Path, help="Archivo de salida (por defecto stdout)")
    args = parser.parse_args(argv)

    if args.path is None:
        from accident_agent.config import get_settings

        args.path = get_settings().data_file

    report = build_report(args.path)
    if args.output:
        args.output.write_text(report, encoding="utf-8")
        print(f"{args.output}: reporte generado", file=sys.stderr)
    else:
        sys.stdout.write(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
