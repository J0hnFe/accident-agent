import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from accident_agent.core.clock import FixedClock
from accident_agent.core.tool import execute
from accident_agent.domain.catalogs import VehicleType
from accident_agent.graph.repository import AccidentFilters, RepositoryError
from accident_agent.tools.accident_report import GenerateReportTool
from tests.fakes import REAL_FILE, FakeAccidentRepository

INSTANT = datetime(2026, 11, 15, 17, 30, tzinfo=UTC)
E35_FATAL = ["SIN-2025-0001", "SIN-2025-0013", "SIN-2026-0004", "SIN-2026-0007"]


@pytest.fixture(scope="module")
def repo() -> FakeAccidentRepository:
    return FakeAccidentRepository()


@pytest.fixture
def tool(repo: FakeAccidentRepository, tmp_path: Path) -> GenerateReportTool:
    repo.fail_with = None
    repo.calls.clear()
    return GenerateReportTool(
        repo, FixedClock(INSTANT), reports_dir=tmp_path, timezone="America/Guayaquil"
    )


def _run(tool: GenerateReportTool, **arguments: Any) -> dict[str, Any]:
    result = execute(tool, arguments)
    assert result.ok, result.error
    assert result.data is not None
    return result.data


def test_scenario_4_report_of_several_accidents(
    tool: GenerateReportTool, repo: FakeAccidentRepository, tmp_path: Path
) -> None:
    data = _run(tool, accident_ids=E35_FATAL)
    assert data["included_ids"] == E35_FATAL
    assert data["not_found_ids"] == []
    assert data["generated_at"] == "2026-11-15T12:30:00-05:00"
    assert data["report_id"].startswith("RPT-20261115-123000-")
    content = data["content_markdown"]
    for accident_id in E35_FATAL:
        assert f"### {accident_id}" in content
    assert "| Fallecidos | 5 |" in content
    assert "| Siniestros vigentes | 4 |" in content
    assert "77e2ca6e3f29" in content
    assert "Nota de privacidad" in content
    path = Path(data["file_path"])
    assert path.parent == tmp_path
    assert path.read_text(encoding="utf-8") == content
    # Los hechos se vuelven a consultar en el repositorio.
    assert "get_by_ids" in repo.calls


def test_scenario_6_report_from_a_previous_search(
    tool: GenerateReportTool, repo: FakeAccidentRepository
) -> None:
    moto = repo.search(AccidentFilters(vehicle_type=VehicleType.MOTOCICLETA), limit=50)
    ids = [a.accident_id for a in moto.accidents]
    data = _run(tool, accident_ids=ids, title="Siniestros con motocicletas")
    assert len(data["included_ids"]) == 7
    assert data["content_markdown"].startswith("# Siniestros con motocicletas")


def test_scenario_11_unknown_id(tool: GenerateReportTool, tmp_path: Path) -> None:
    data = _run(tool, accident_ids=["SIN-9999-9999"])
    assert (data["included_ids"], data["not_found_ids"]) == ([], ["SIN-9999-9999"])
    assert (data["report_id"], data["file_path"], data["content_markdown"]) == (None, None, "")
    assert any("SIN-9999-9999" in w for w in data["warnings"])
    assert list(tmp_path.iterdir()) == []


def test_found_and_not_found(tool: GenerateReportTool) -> None:
    data = _run(tool, accident_ids=["SIN-2025-0001", "SIN-9999-9999"])
    assert (data["included_ids"], data["not_found_ids"]) == (["SIN-2025-0001"], ["SIN-9999-9999"])
    assert "SIN-9999-9999" in data["content_markdown"]


def test_annulled_record_is_shown_but_not_counted(tool: GenerateReportTool) -> None:
    data = _run(tool, accident_ids=["SIN-2026-0010", "SIN-2026-0011"])
    content = data["content_markdown"]
    assert "| Siniestros vigentes | 1 |" in content
    assert "ANULADO" in content
    assert "- **Reemplazado por:** SIN-2026-0011" in content
    assert any("SIN-2026-0010" in w and "no suma" in w for w in data["warnings"])


def test_annulled_without_its_replacement_suggests_it(tool: GenerateReportTool) -> None:
    data = _run(tool, accident_ids=["SIN-2026-0010"])
    assert "| Siniestros vigentes | 0 |" in data["content_markdown"]
    assert any("SIN-2026-0011" in w for w in data["warnings"])


def test_quality_warnings(tool: GenerateReportTool) -> None:
    data = _run(tool, accident_ids=["SIN-2025-0012", "SIN-2026-0011"])
    content = data["content_markdown"]
    assert "SIN-2025-0012: el resumen original" in content
    assert "6 dias despues" in content


def test_single_accident_with_default_title(tool: GenerateReportTool) -> None:
    data = _run(tool, accident_ids=["SIN-2025-0001", "sin-2025-0001"])
    assert data["included_ids"] == ["SIN-2025-0001"]
    assert data["title"] == "Informe del siniestro SIN-2025-0001"


def test_narrative_is_optional(tool: GenerateReportTool, repo: FakeAccidentRepository) -> None:
    narrative = repo.views["SIN-2026-0009"].narrative
    with_text = _run(tool, accident_ids=["SIN-2026-0009"])["content_markdown"]
    without = _run(tool, accident_ids=["SIN-2026-0009"], include_narrative=False)
    assert f"> {narrative}" in with_text
    assert narrative not in without["content_markdown"]


def test_without_saving(tool: GenerateReportTool, tmp_path: Path) -> None:
    data = _run(tool, accident_ids=["SIN-2025-0001"], save_file=False)
    assert data["file_path"] is None
    assert data["content_markdown"]
    assert list(tmp_path.iterdir()) == []


def test_save_error_is_a_warning(repo: FakeAccidentRepository, tmp_path: Path) -> None:
    blocked = tmp_path / "archivo"
    blocked.write_text("no es carpeta")
    tool = GenerateReportTool(repo, FixedClock(INSTANT), reports_dir=blocked)
    data = _run(tool, accident_ids=["SIN-2025-0001"])
    assert data["file_path"] is None
    assert data["content_markdown"]
    assert any("No se pudo guardar" in w for w in data["warnings"])


def test_report_id_is_deterministic(tool: GenerateReportTool) -> None:
    first = _run(tool, accident_ids=E35_FATAL, save_file=False)["report_id"]
    second = _run(tool, accident_ids=E35_FATAL, save_file=False)["report_id"]
    other = _run(tool, accident_ids=["SIN-2025-0001"], save_file=False)["report_id"]
    assert first == second != other


def test_no_personal_data(tool: GenerateReportTool) -> None:
    raw = json.loads(REAL_FILE.read_text(encoding="utf-8"))
    roster = set()
    for record in raw["registros"]:
        roster |= {p["nombre"] for p in record["personas"]} | {
            p["cedula"] for p in record["personas"]
        }
        roster |= {v["placa"] for v in record["vehiculos"]}
    ids = sorted({r["id_parte"] for r in raw["registros"]})[:20]
    content = _run(tool, accident_ids=ids)["content_markdown"]
    assert [v for v in roster if v in content] == []


@pytest.mark.parametrize(
    "arguments",
    [
        {"accident_ids": []},
        {"accident_ids": [f"SIN-2025-{i:04d}" for i in range(21)]},
        {"accident_ids": ["SIN-25-1"]},
        {"accident_ids": ["SIN-2025-0001"], "title": "x" * 121},
        {},
    ],
)
def test_invalid_inputs(tool: GenerateReportTool, arguments: dict[str, Any]) -> None:
    result = execute(tool, arguments)
    assert result.error is not None
    assert result.error.type == "validation"


def test_repository_failure(tool: GenerateReportTool, repo: FakeAccidentRepository) -> None:
    repo.fail_with = RepositoryError("unavailable", "detalle")
    result = execute(tool, {"accident_ids": ["SIN-2025-0001"]})
    assert result.error is not None
    assert result.error.type == "execution"
    assert "base de datos" in result.error.message


def test_spec(tool: GenerateReportTool) -> None:
    spec = tool.spec()
    assert spec.name == "generate_accident_report"
    assert spec.parameters["required"] == ["accident_ids"]
    assert "search_accidents" in spec.description
