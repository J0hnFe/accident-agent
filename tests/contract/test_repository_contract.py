"""Contrato del puerto `AccidentRepository`: las mismas pruebas para el fake y para Neo4j.

Asegura que `FakeAccidentRepository` sea un sustituto valido (Liskov) en las pruebas de las
herramientas. La variante Neo4j es de integracion: uv run pytest -m integration
"""

from collections.abc import Iterator
from datetime import date

import pytest
from neo4j.exceptions import ServiceUnavailable

from accident_agent.config import get_settings
from accident_agent.domain.catalogs import Province, RecordStatus, ReportStatus, VehicleType
from accident_agent.graph.connection import create_driver
from accident_agent.graph.neo4j_repository import Neo4jAccidentRepository
from accident_agent.graph.repository import (
    AccidentFilters,
    AccidentRepository,
    AccidentView,
    GroupBy,
)
from accident_agent.ingestion.neo4j_writer import Neo4jWriter
from tests.fakes import FakeAccidentRepository

E35_FATAL = ["SIN-2025-0001", "SIN-2025-0013", "SIN-2026-0004", "SIN-2026-0007"]


@pytest.fixture(
    scope="module", params=["fake", pytest.param("neo4j", marks=pytest.mark.integration)]
)
def repo(request: pytest.FixtureRequest) -> Iterator[AccidentRepository]:
    fake = FakeAccidentRepository()
    if request.param == "fake":
        yield fake
        return
    driver = create_driver(get_settings())
    try:
        driver.verify_connectivity()
    except ServiceUnavailable:
        driver.close()
        pytest.skip("Neo4j no esta disponible: docker compose up -d neo4j")
    Neo4jWriter(driver).write(fake.dataset)
    yield Neo4jAccidentRepository(driver)
    driver.close()


def _ids(accidents: list[AccidentView]) -> list[str]:
    return [a.accident_id for a in accidents]


def test_default_search_excludes_annulled_and_sorts_by_date(repo: AccidentRepository) -> None:
    page = repo.search(AccidentFilters(), limit=3)
    assert page.total_found == 29
    assert _ids(page.accidents) == ["SIN-2026-0011", "SIN-2026-0009", "SIN-2026-0008"]


def test_include_annulled(repo: AccidentRepository) -> None:
    assert repo.search(AccidentFilters(include_annulled=True), limit=1).total_found == 30


def test_province_filter(repo: AccidentRepository) -> None:
    page = repo.search(AccidentFilters(province=Province.PICHINCHA), limit=10)
    assert page.total_found == 5
    assert "SIN-2026-0011" in _ids(page.accidents)
    assert "SIN-2026-0010" not in _ids(page.accidents)


def test_combined_filters(repo: AccidentRepository) -> None:
    page = repo.search(AccidentFilters(road_code="E35", only_fatal=True), limit=10)
    assert sorted(_ids(page.accidents)) == E35_FATAL


def test_vehicle_type_and_dates(repo: AccidentRepository) -> None:
    moto = repo.search(AccidentFilters(vehicle_type=VehicleType.MOTOCICLETA), limit=50)
    assert moto.total_found == 7
    recent = repo.search(
        AccidentFilters(date_from=date(2026, 5, 15), date_to=date(2026, 11, 15)), limit=10
    )
    assert sorted(_ids(recent.accidents)) == [
        "SIN-2026-0007",
        "SIN-2026-0008",
        "SIN-2026-0009",
        "SIN-2026-0011",
    ]


def test_road_text_filter(repo: AccidentRepository) -> None:
    page = repo.search(AccidentFilters(road_text="costa"), limit=10)
    assert page.total_found >= 1
    assert all("costa" in a.road.lower() for a in page.accidents)


def test_explicit_ids_include_annulled_and_skip_unknown(repo: AccidentRepository) -> None:
    page = repo.search(AccidentFilters(accident_ids=["SIN-2026-0010", "SIN-9999-9999"]), limit=10)
    assert _ids(page.accidents) == ["SIN-2026-0010"]
    annulled = page.accidents[0]
    assert (annulled.status, annulled.replaced_by) == (RecordStatus.ANULADO, "SIN-2026-0011")


def test_text_search(repo: AccidentRepository) -> None:
    page = repo.search(AccidentFilters(text="neblina"), limit=10)
    assert set(_ids(page.accidents)) == {
        "SIN-2025-0001",
        "SIN-2025-0009",
        "SIN-2025-0013",
        "SIN-2026-0007",
    }


def test_no_results(repo: AccidentRepository) -> None:
    page = repo.search(AccidentFilters(province=Province.GALAPAGOS), limit=10)
    assert (page.total_found, page.accidents) == (0, [])


def test_get_by_ids_keeps_order_and_details(repo: AccidentRepository) -> None:
    views = repo.get_by_ids(["SIN-2026-0011", "SIN-9999-9999", "SIN-2025-0001"])
    assert _ids(views) == ["SIN-2026-0011", "SIN-2025-0001"]
    replacement, first = views
    assert replacement.replaces == "SIN-2026-0010"
    assert (first.province, first.canton, first.parish) == (Province.TUNGURAHUA, "Ambato", "Pasa")
    assert (first.road_code, first.km, first.deaths) == ("E35", 128.0, 1)
    assert [v.vehicle_id for v in first.vehicles] == ["SIN-2025-0001-V1", "SIN-2025-0001-V2"]
    assert len(first.people) == 4
    assert first.occurred_at.isoformat() == "2025-01-12T05:40:00-05:00"


def test_stats(repo: AccidentRepository) -> None:
    years = repo.stats(AccidentFilters(), GroupBy.YEAR)
    assert [(r.group, r.accidents) for r in years] == [("2025", 19), ("2026", 10)]
    assert sum(r.deaths for r in years) == 18
    provinces = {r.group: r.accidents for r in repo.stats(AccidentFilters(), GroupBy.PROVINCE)}
    assert (provinces["Pichincha"], provinces["Guayas"]) == (5, 5)
    vehicles = {r.group: r.accidents for r in repo.stats(AccidentFilters(), GroupBy.VEHICLE_TYPE)}
    assert vehicles["motocicleta"] == 7
    e35 = repo.stats(AccidentFilters(road_code="E35"), GroupBy.CAUSE)
    assert sum(r.accidents for r in e35) == 6
    months = repo.stats(AccidentFilters(), GroupBy.MONTH)
    assert sum(r.accidents for r in months) == 29
    assert all(len(r.group) == 7 for r in months)


def test_reports_by_road_current_first(repo: AccidentRepository) -> None:
    hits = repo.search_reports(None, "E35", limit=10)
    assert [(h.report_id, h.section_order) for h in hits] == [
        ("INF-2026-01", 1),
        ("INF-2026-01", 2),
        ("INF-2025-01", 1),
        ("INF-2025-01", 2),
    ]
    assert hits[0].supersedes == "INF-2025-01"
    assert (hits[2].status, hits[2].superseded_by) == (ReportStatus.REEMPLAZADO, "INF-2026-01")


def test_reports_by_text(repo: AccidentRepository) -> None:
    hits = repo.search_reports("estrellamiento", None, limit=3)
    assert (hits[0].report_id, hits[0].section_title) == ("INF-2026-02", "Tipos de siniestro")
    assert repo.search_reports("palabrainexistente", None, limit=3) == []


def test_dataset_info(repo: AccidentRepository) -> None:
    info = repo.dataset_info()
    assert info.sha256 == "77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280"
    assert info.generated == date(2026, 11, 9)
