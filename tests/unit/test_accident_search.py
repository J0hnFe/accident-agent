import json
from typing import Any

import pytest

from accident_agent.core.tool import ToolResult, execute
from accident_agent.graph.repository import RepositoryError
from accident_agent.tools.accident_search import SearchAccidentsTool
from tests.fakes import FakeAccidentRepository

PII_KEYS = {"nombre", "cedula", "placa", "placa_vehiculo", "name", "plate"}


@pytest.fixture(scope="module")
def repo() -> FakeAccidentRepository:
    return FakeAccidentRepository()


@pytest.fixture
def tool(repo: FakeAccidentRepository) -> SearchAccidentsTool:
    repo.fail_with = None
    return SearchAccidentsTool(repo)


def _run(tool: SearchAccidentsTool, **arguments: Any) -> dict[str, Any]:
    result = execute(tool, arguments)
    assert result.ok, result.error
    assert result.data is not None
    return result.data


def _error(tool: SearchAccidentsTool, **arguments: Any) -> str:
    result: ToolResult = execute(tool, arguments)
    assert result.error is not None
    assert result.error.type == "validation"
    return result.error.message


def _ids(data: dict[str, Any]) -> list[str]:
    return [a["accident_id"] for a in data["accidents"]]


# Escenarios de la seccion 9 del plan.


def test_scenario_2_province(tool: SearchAccidentsTool) -> None:
    data = _run(tool, province="pichincha")
    assert data["total_found"] == 5
    assert "SIN-2026-0011" in _ids(data)
    assert "SIN-2026-0010" not in _ids(data)
    assert data["applied_filters"]["province"] == "Pichincha"


def test_scenario_3_fatal_on_road(tool: SearchAccidentsTool) -> None:
    data = _run(tool, road="E35", only_fatal=True)
    assert sorted(_ids(data)) == [
        "SIN-2025-0001",
        "SIN-2025-0013",
        "SIN-2026-0004",
        "SIN-2026-0007",
    ]
    assert data["applied_filters"]["road_code"] == "E35"


def test_scenario_5_date_range(tool: SearchAccidentsTool) -> None:
    data = _run(tool, date_from="2026-05-15", date_to="2026-11-15")
    assert sorted(_ids(data)) == [
        "SIN-2026-0007",
        "SIN-2026-0008",
        "SIN-2026-0009",
        "SIN-2026-0011",
    ]


def test_scenario_8_reports_current_first(tool: SearchAccidentsTool) -> None:
    data = _run(tool, mode="reports", road="E35")
    assert data["reports"][0]["report_id"] == "INF-2026-01"
    assert any("INF-2025-01" in w and "INF-2026-01" in w for w in data["warnings"])


def test_scenario_9_definition_from_reports(tool: SearchAccidentsTool) -> None:
    data = _run(tool, mode="reports", text="estrellamiento")
    first = data["reports"][0]
    assert (first["report_id"], first["section_title"]) == ("INF-2026-02", "Tipos de siniestro")


def test_scenario_10_no_results(tool: SearchAccidentsTool) -> None:
    data = _run(tool, province="Gal\u00e1pagos")
    assert (data["total_found"], data["accidents"]) == (0, [])
    assert any("No hay siniestros" in w for w in data["warnings"])


def test_scenario_12_annulled_by_id(tool: SearchAccidentsTool) -> None:
    data = _run(tool, accident_ids=["sin-2026-0010"])
    assert _ids(data) == ["SIN-2026-0010"]
    assert data["accidents"][0]["status"] == "anulado"
    assert any("ANULADO" in w and "SIN-2026-0011" in w for w in data["warnings"])


# Normalizacion de entradas.


@pytest.mark.parametrize(
    ("arguments", "field", "expected"),
    [
        ({"accident_type": "P\u00e9rdida de pista"}, "accident_type", "perdida_de_pista"),
        ({"cause": "VELOCIDAD EXCESIVA"}, "cause", "exceso_de_velocidad"),
        ({"vehicle_type": "Motocicleta"}, "vehicle_type", "motocicleta"),
        ({"weather": "LLUVIA"}, "weather", "lluvia"),
        ({"surface": "h\u00fameda"}, "surface", "humeda"),
        ({"lighting": "diurna"}, "lighting", "diurna"),
        ({"canton": "RUMI\u00d1AHUI"}, "canton", "Ruminahui"),
        ({"road": "Panamericana"}, "road_text", "panamericana"),
        ({"text": "  V\u00eda  MOJADA "}, "text", "via mojada"),
    ],
)
def test_inputs_are_normalized(
    tool: SearchAccidentsTool, arguments: dict[str, Any], field: str, expected: str
) -> None:
    assert _run(tool, **arguments)["applied_filters"][field] == expected


def test_road_name_fragment(tool: SearchAccidentsTool) -> None:
    data = _run(tool, road="panamericana", limit=50)
    assert data["total_found"] == 6
    assert all(a["road_code"] == "E35" for a in data["accidents"])


def test_unknown_value_gets_suggestions_without_echoing_input(tool: SearchAccidentsTool) -> None:
    message = _error(tool, province="Pichinca")
    assert "Pichincha" in message
    assert "Pichinca" not in message
    assert "motocicleta" in _error(tool, vehicle_type="motocicletas")


@pytest.mark.parametrize(
    ("arguments", "fragment"),
    [
        ({"date_from": "2026-11-15", "date_to": "2026-01-01"}, "date_from"),
        ({"mode": "stats"}, "group_by"),
        ({"accident_ids": ["SIN-26-1"]}, "accident_ids"),
        ({"accident_ids": [f"SIN-2025-{i:04d}" for i in range(21)]}, "accident_ids"),
        ({"limit": 0}, "limit"),
        ({"limit": 51}, "limit"),
        ({"text": "x" * 201}, "text"),
        ({"mode": "listar"}, "mode"),
        ({"province": "Pichincha", "color": "rojo"}, "color"),
    ],
)
def test_invalid_inputs(
    tool: SearchAccidentsTool, arguments: dict[str, Any], fragment: str
) -> None:
    assert fragment in _error(tool, **arguments)


# Advertencias.


def test_truncation_warning(tool: SearchAccidentsTool) -> None:
    data = _run(tool)
    assert (data["total_found"], len(data["accidents"])) == (29, 10)
    assert any("Se muestran 10 de 29" in w for w in data["warnings"])


def test_unknown_ids_warning(tool: SearchAccidentsTool) -> None:
    data = _run(tool, accident_ids=["SIN-9999-9999"])
    assert data["total_found"] == 0
    assert any("SIN-9999-9999" in w for w in data["warnings"])


def test_data_quality_warnings(tool: SearchAccidentsTool) -> None:
    data = _run(tool, accident_ids=["SIN-2025-0012", "SIN-2026-0011"])
    warnings = data["warnings"]
    assert any(w.startswith("SIN-2025-0012") and "resumen" in w for w in warnings)
    assert any(w.startswith("SIN-2026-0011") and "6 dias" in w for w in warnings)
    assert "SIN-2026-0011 reemplaza al registro anulado SIN-2026-0010." in warnings


def test_reports_mode_ignores_accident_filters(tool: SearchAccidentsTool) -> None:
    data = _run(tool, mode="reports", text="motocicletas", province="Guayas")
    assert any("province" in w and "se ignoran" in w for w in data["warnings"])


# Estadisticas.


def test_stats(tool: SearchAccidentsTool) -> None:
    data = _run(tool, mode="stats", group_by="province")
    assert data["total_found"] == 29
    groups = {row["group"]: row["accidents"] for row in data["stats"]}
    assert (groups["Pichincha"], groups["Guayas"]) == (5, 5)
    assert data["accidents"] == []


def test_stats_by_vehicle_type_warns_about_double_counting(tool: SearchAccidentsTool) -> None:
    data = _run(tool, mode="stats", group_by="vehicle_type")
    assert any("varios tipos de vehiculo" in w for w in data["warnings"])


# Errores y privacidad.


@pytest.mark.parametrize(
    ("kind", "error_type"), [("unavailable", "execution"), ("timeout", "timeout")]
)
def test_repository_errors_are_friendly(
    tool: SearchAccidentsTool, repo: FakeAccidentRepository, kind: Any, error_type: str
) -> None:
    repo.fail_with = RepositoryError(kind, "detalle interno")
    result = execute(tool, {"province": "Guayas"})
    assert result.error is not None
    assert result.error.type == error_type
    assert "detalle interno" not in result.error.message
    assert "base de datos" in result.error.message


def _keys(obj: Any) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | {k for v in obj.values() for k in _keys(v)}
    if isinstance(obj, list):
        return {k for v in obj for k in _keys(v)}
    return set()


def test_output_has_no_personal_data_fields(tool: SearchAccidentsTool) -> None:
    data = _run(tool, accident_ids=["SIN-2026-0009"])
    assert not (_keys(data) & PII_KEYS)
    assert data["accidents"][0]["people"]


def test_spec_for_the_llm(tool: SearchAccidentsTool) -> None:
    spec = tool.spec()
    assert spec.name == "search_accidents"
    text = json.dumps(spec.parameters)
    assert "$ref" not in text
    assert "perdida_de_pista" in text
    assert "Pichincha" in text
    assert "required" not in spec.parameters
    for word in ("stats", "reports", "get_current_time"):
        assert word in spec.description


def test_many_ids_are_not_cut_by_the_default_limit(tool: SearchAccidentsTool) -> None:
    ids = [f"SIN-2025-{i:04d}" for i in range(1, 21)]
    data = _run(tool, accident_ids=ids)
    assert len(data["accidents"]) == 19  # SIN-2025-0020 no existe
    assert any("SIN-2025-0020" in w for w in data["warnings"])
    assert not any("Se muestran" in w for w in data["warnings"])
