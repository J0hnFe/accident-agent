import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

from accident_agent.ingestion.quality_markdown import (
    REGENERATE_COMMAND,
    NormalizationSummary,
    build_report,
    main,
    markdown_cell,
    summarize_normalization,
)
from accident_agent.ingestion.raw_models import RawDataset

ROOT = Path(__file__).resolve().parents[2]
REAL_FILE = ROOT / "data" / "siniestros_raw.json"
COMMITTED_REPORT = ROOT / "docs" / "datos" / "reporte_calidad_datos.md"


def _ascii_guard() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "ascii_guard", ROOT / "scripts" / "ascii_guard.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def report() -> str:
    return build_report(REAL_FILE)


@pytest.fixture(scope="module")
def summary() -> NormalizationSummary:
    return summarize_normalization(RawDataset.model_validate_json(REAL_FILE.read_bytes()))


@pytest.fixture(scope="module")
def raw_json() -> Any:
    return json.loads(REAL_FILE.read_text(encoding="utf-8"))


def test_report_is_deterministic(report: str) -> None:
    assert build_report(REAL_FILE) == report


def test_committed_report_is_up_to_date(report: str) -> None:
    stale = COMMITTED_REPORT.read_text(encoding="utf-8") != report
    assert not stale, f"Reporte desactualizado; regenerar con: {REGENERATE_COMMAND}"


def test_report_follows_ascii_convention(report: str) -> None:
    assert _ascii_guard().check_markdown(report) == []


def test_report_has_no_personal_data_nor_free_text(report: str, raw_json: Any) -> None:
    leaked: list[str] = []
    for record in raw_json["registros"]:
        for person in record["personas"]:
            leaked += [v for v in (person["nombre"], person["cedula"]) if v in report]
        leaked += [v["placa"] for v in record["vehiculos"] if v["placa"] in report]
        narrative = " ".join(record["narrativa"].split())
        if narrative[:40] in report:
            leaked.append(record["id_parte"])
    for item in raw_json["informes"]:
        leaked += [item["id"] for s in item["secciones"] if s["texto"][:40] in report]
    assert leaked == []


def test_report_contains_key_findings(report: str) -> None:
    for fragment in [
        "77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280",
        "| Anomalias detectadas | 42 |",
        "`duplicate_id`",
        "SIN-2025-0007",
        "SIN-2025-0012",
        "SIN-2026-0009",
        "INF-RES-01",
        "| `registros[].causa_probable` | 17 | 10 |",
        "| `registros[].danos_materiales` | 31 | 0 | 1200 | 41000 |",
    ]:
        assert fragment in report, fragment


def test_categorical_summary(summary: NormalizationSummary) -> None:
    by_path = {c.path: c for c in summary.categorical}
    expected = {
        "registros[].tipo_siniestro": (9, 5),
        "registros[].causa_probable": (17, 10),
        "registros[].ubicacion.provincia": (21, 17),
        "registros[].ubicacion.canton": (26, 22),
        "registros[].ubicacion.parroquia": (29, 29),
        "registros[].ubicacion.via": (25, 20),
        "registros[].vehiculos[].tipo_vehiculo": (16, 10),
        "registros[].vehiculos[].marca": (21, 13),
        "registros[].personas[].sexo": (6, 2),
        "registros[].personas[].proteccion": (12, 5),
    }
    for path, counts in expected.items():
        item = by_path[path]
        assert (item.raw_distinct, item.canonical_distinct) == counts, path
        assert sum(v.count for v in item.distribution) == item.total, path


def test_numeric_and_date_summary(summary: NormalizationSummary) -> None:
    numeric = {n.path: (n.present, n.nulls, n.minimum, n.maximum) for n in summary.numeric}
    assert numeric["registros[].danos_materiales"] == (31, 0, 1200.0, 41000.0)
    assert numeric["registros[].ubicacion.km"] == (26, 5, 3.0, 205.0)
    assert numeric["registros[].personas[].alcohol_gl"] == (47, 34, 0.0, 1.6)
    assert numeric["registros[].personas[].edad"] == (81, 0, 7.0, 71.0)
    dates = {d.path: (d.minimum, d.maximum) for d in summary.dates}
    assert dates["registros[].fecha_hora"] == (
        "2025-01-12T05:40:00-05:00",
        "2026-09-02T02:25:00-05:00",
    )
    assert summary.cleaned_narratives == 10
    assert summary.excluded_report_ids == ["INF-RES-01"]


@pytest.mark.parametrize(
    ("value", "expected"),
    [("N/A", "`N/A`"), ("a|b", "`a\\|b`"), ("", '`""`'), (None, "null")],
)
def test_markdown_cell(value: str | None, expected: str) -> None:
    assert markdown_cell(value) == expected


def test_main_writes_file(tmp_path: Path, report: str) -> None:
    output = tmp_path / "reporte.md"
    assert main([str(REAL_FILE), "--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == report
