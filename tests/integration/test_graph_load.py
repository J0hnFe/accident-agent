"""Pruebas de integracion de la carga (tarea 2.7). Requieren Neo4j: docker compose up -d neo4j.

Ejecutar con: uv run pytest -m integration
"""

import json
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from neo4j import Driver, RoutingControl
from neo4j.exceptions import ServiceUnavailable

from accident_agent.config import get_settings
from accident_agent.domain.models import CleanDataset
from accident_agent.graph.connection import create_driver
from accident_agent.ingestion import neo4j_writer
from accident_agent.ingestion.neo4j_writer import LoadMismatchError, Neo4jWriter
from accident_agent.ingestion.pipeline import run_pipeline
from accident_agent.ingestion.verification import collect, verify
from tests.integration.example_queries import EXAMPLES

pytestmark = pytest.mark.integration

REAL_FILE = Path(__file__).resolve().parents[2] / "data" / "siniestros_raw.json"


@pytest.fixture(scope="module")
def dataset() -> CleanDataset:
    return run_pipeline(REAL_FILE)


@pytest.fixture(scope="module")
def driver(dataset: CleanDataset) -> Iterator[Driver]:
    neo4j_driver = create_driver(get_settings())
    try:
        neo4j_driver.verify_connectivity()
    except ServiceUnavailable:
        neo4j_driver.close()
        pytest.skip("Neo4j no esta disponible: docker compose up -d neo4j")
    Neo4jWriter(neo4j_driver).write(dataset)
    yield neo4j_driver
    neo4j_driver.close()


def _read(driver: Driver, cypher: Any, **params: Any) -> list[dict[str, Any]]:
    records, _, _ = driver.execute_query(cypher, params, routing_=RoutingControl.READ)
    return [record.data() for record in records]


def _example(driver: Driver, name: str) -> list[dict[str, Any]]:
    query = EXAMPLES[name]
    return _read(driver, query.cypher, **query.params)


def test_control_values_and_no_personal_data(driver: Driver, dataset: CleanDataset) -> None:
    report = verify(driver, dataset.info.sha256)
    assert report.enforced
    assert report.mismatches == []
    assert report.personal_data_findings == []


def test_no_value_from_the_personal_data_roster(driver: Driver) -> None:
    raw = json.loads(REAL_FILE.read_text(encoding="utf-8"))
    roster: set[str] = set()
    for record in raw["registros"]:
        for person in record["personas"]:
            roster |= {person["nombre"].casefold(), person["cedula"]}
        roster |= {v["placa"].casefold() for v in record["vehiculos"]}
    for item in raw["informes"]:
        if item["clasificacion"] != "PUBLICO":
            roster |= {s["texto"][:40].casefold() for s in item["secciones"]}
    texts = _read(
        driver,
        "MATCH (n) UNWIND keys(n) AS key WITH n[key] AS value WHERE value IS :: STRING"
        " RETURN value",
    )
    leaked = [v for t in texts for v in roster if v in t["value"].casefold()]
    assert leaked == []


def test_reload_is_idempotent(driver: Driver, dataset: CleanDataset) -> None:
    before = collect(driver)
    Neo4jWriter(driver).write(dataset)
    assert collect(driver) == before
    assert _read(driver, "MATCH (d:Dataset) RETURN count(d) AS n") == [{"n": 1}]


def test_failed_load_rolls_back_and_keeps_the_previous_graph(
    driver: Driver, dataset: CleanDataset, monkeypatch: pytest.MonkeyPatch
) -> None:
    before = collect(driver)
    original = neo4j_writer.graph_rows

    def broken_rows(data: CleanDataset) -> neo4j_writer.GraphRows:
        rows = original(data)
        rows.accidents[0]["parish_id"] = "No|Existe|Parroquia"
        return rows

    monkeypatch.setattr(neo4j_writer, "graph_rows", broken_rows)
    with pytest.raises(LoadMismatchError, match="accidents"):
        Neo4jWriter(driver).write(dataset)
    assert collect(driver) == before


def test_schema(driver: Driver) -> None:
    constraints = _read(driver, "SHOW CONSTRAINTS YIELD name RETURN name")
    assert len(constraints) == 13
    indexes = {r["name"]: r["type"] for r in _read(driver, "SHOW INDEXES YIELD name, type")}
    assert indexes["accident_narratives"] == "FULLTEXT"
    assert indexes["report_texts"] == "FULLTEXT"
    assert indexes["accident_date"] == "RANGE"


def test_datetime_round_trip(driver: Driver) -> None:
    rows = _read(
        driver,
        "MATCH (a:Accident {accident_id: $id}) RETURN a.occurred_at AS at, a.date AS d",
        id="SIN-2025-0001",
    )
    assert rows[0]["at"].to_native().isoformat() == "2025-01-12T05:40:00-05:00"
    assert rows[0]["d"].to_native() == date(2025, 1, 12)


def test_fulltext_ignores_accents_and_plurals(driver: Driver) -> None:
    def ids(text: str) -> list[str]:
        query = EXAMPLES["narrative_search"]
        return [r["accident_id"] for r in _read(driver, query.cypher, text=text)]

    assert ids("neblina")
    assert ids("vehiculo") == ids("veh\u00edculo")
    assert ids("neblinas") == ids("neblina")


def test_reports_fulltext(driver: Driver) -> None:
    rows = _read(
        driver,
        "CALL db.index.fulltext.queryNodes('report_texts', $text) YIELD node"
        " MATCH (r:Report)-[:HAS_SECTION]->(node) RETURN DISTINCT r.report_id AS id",
        text="estrellamiento",
    )
    assert {"id": "INF-2026-02"} in rows


def test_example_queries(driver: Driver) -> None:
    provinces = {r["province"]: r["accidents"] for r in _example(driver, "by_province")}
    assert (provinces["Pichincha"], provinces["Guayas"]) == (5, 5)
    assert [r["accident_id"] for r in _example(driver, "fatal_on_road")] == [
        "SIN-2025-0001",
        "SIN-2025-0013",
        "SIN-2026-0004",
        "SIN-2026-0007",
    ]
    assert _example(driver, "by_vehicle_type") == [{"accidents": 7}]
    assert [r["accident_id"] for r in _example(driver, "date_range")] == [
        "SIN-2026-0007",
        "SIN-2026-0008",
        "SIN-2026-0009",
        "SIN-2026-0011",
    ]
    trace = _example(driver, "annulled_trace")[0]
    assert (trace["status"], trace["replaced_by"]) == ("anulado", "SIN-2026-0011")
    reports = _example(driver, "road_reports")
    assert [(r["report_id"], r["status"]) for r in reports] == [
        ("INF-2026-01", "vigente"),
        ("INF-2025-01", "reemplazado"),
    ]
    assert reports[0]["supersedes"] == "INF-2025-01"
    assert _example(driver, "accident_subgraph")[0]["paths"] > 0
