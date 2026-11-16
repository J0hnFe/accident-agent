"""Herramientas de punta a punta contra Neo4j (tarea 3.6). Requiere: docker compose up -d neo4j."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from neo4j import Driver
from neo4j.exceptions import ClientError, ServiceUnavailable

from accident_agent.config import get_settings
from accident_agent.core.clock import FixedClock
from accident_agent.core.tool import execute
from accident_agent.graph.connection import create_driver
from accident_agent.graph.neo4j_repository import Neo4jAccidentRepository
from accident_agent.ingestion.neo4j_writer import Neo4jWriter
from accident_agent.ingestion.pipeline import run_pipeline
from accident_agent.tools.accident_report import GenerateReportTool
from accident_agent.tools.accident_search import SearchAccidentsTool
from tests.fakes import REAL_FILE

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def driver() -> Iterator[Driver]:
    neo4j_driver = create_driver(get_settings())
    try:
        neo4j_driver.verify_connectivity()
    except ServiceUnavailable:
        neo4j_driver.close()
        pytest.skip("Neo4j no esta disponible: docker compose up -d neo4j")
    Neo4jWriter(neo4j_driver).write(run_pipeline(REAL_FILE))
    yield neo4j_driver
    neo4j_driver.close()


@pytest.fixture(scope="module")
def repo(driver: Driver) -> Neo4jAccidentRepository:
    return Neo4jAccidentRepository(driver)


def _search(repo: Neo4jAccidentRepository, **arguments: Any) -> dict[str, Any]:
    result = execute(SearchAccidentsTool(repo), arguments)
    assert result.ok, result.error
    assert result.data is not None
    return result.data


def _ids(data: dict[str, Any]) -> list[str]:
    return sorted(a["accident_id"] for a in data["accidents"])


def test_search_scenarios(repo: Neo4jAccidentRepository) -> None:
    pichincha = _search(repo, province="Pichincha")
    assert pichincha["total_found"] == 5
    assert "SIN-2026-0010" not in _ids(pichincha)
    assert _ids(_search(repo, road="E35", only_fatal=True)) == [
        "SIN-2025-0001",
        "SIN-2025-0013",
        "SIN-2026-0004",
        "SIN-2026-0007",
    ]
    assert _search(repo, province="Galapagos")["total_found"] == 0
    annulled = _search(repo, accident_ids=["SIN-2026-0010"])
    assert annulled["accidents"][0]["replaced_by"] == "SIN-2026-0011"
    reports = _search(repo, mode="reports", road="E35")
    assert reports["reports"][0]["report_id"] == "INF-2026-01"


def test_text_search_ignores_accents(repo: Neo4jAccidentRepository) -> None:
    with_accent = _search(repo, text="v\u00eda", limit=50)
    without = _search(repo, text="via", limit=50)
    assert with_accent["total_found"] == without["total_found"] == 5
    assert _ids(with_accent) == _ids(without)


def test_text_with_lucene_syntax_does_not_fail(repo: Neo4jAccidentRepository) -> None:
    assert _search(repo, text='choque: (frontal) AND "bus"*')["total_found"] >= 0


def test_report_scenario_4(repo: Neo4jAccidentRepository, tmp_path: Path) -> None:
    tool = GenerateReportTool(
        repo, FixedClock(datetime(2026, 11, 15, 17, 30, tzinfo=UTC)), reports_dir=tmp_path
    )
    ids = ["SIN-2025-0001", "SIN-2025-0013", "SIN-2026-0004", "SIN-2026-0007"]
    result = execute(tool, {"accident_ids": ids})
    assert result.data is not None
    assert result.data["included_ids"] == ids
    assert "| Fallecidos | 5 |" in result.data["content_markdown"]
    assert Path(result.data["file_path"]).exists()


def test_repository_cannot_write(repo: Neo4jAccidentRepository, driver: Driver) -> None:
    with pytest.raises(ClientError):
        repo._read("CREATE (n:Probe) RETURN n")
    records, _, _ = driver.execute_query("MATCH (n:Probe) RETURN count(n) AS n")
    assert records[0]["n"] == 0
