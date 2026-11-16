from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from accident_agent.ingestion.neo4j_writer import GraphRows, graph_rows
from accident_agent.ingestion.pipeline import run_pipeline

REAL_FILE = Path(__file__).resolve().parents[2] / "data" / "siniestros_raw.json"
ALLOWED_TYPES = (str, int, float, bool, date, datetime, type(None))
PII_KEYS = {"nombre", "cedula", "placa", "placa_vehiculo", "plate", "name_person"}


@pytest.fixture(scope="module")
def rows() -> GraphRows:
    return graph_rows(run_pipeline(REAL_FILE))


def test_row_counts_match_the_graph_model(rows: GraphRows) -> None:
    counts = {name: len(value) for name, value in rows.model_dump().items() if name != "dataset"}
    assert counts == {
        "provinces": 17,
        "cantons": 22,
        "parishes": 30,
        "roads": 20,
        "accident_types": 5,
        "causes": 10,
        "vehicle_types": 10,
        "accidents": 30,
        "replacements": 1,
        "vehicles": 49,
        "people": 80,
        "reports": 4,
        "sections": 9,
        "supersedes": 1,
        "report_roads": 2,
    }


def _values(obj: Any) -> list[Any]:
    if isinstance(obj, dict):
        return [v for value in obj.values() for v in _values(value)]
    if isinstance(obj, list):
        return [v for value in obj for v in _values(value)]
    return [obj]


def _keys(obj: Any) -> set[str]:
    if isinstance(obj, dict):
        return set(obj) | {k for value in obj.values() for k in _keys(value)}
    if isinstance(obj, list):
        return {k for value in obj for k in _keys(value)}
    return set()


def test_rows_only_contain_driver_friendly_values(rows: GraphRows) -> None:
    values = _values(rows.model_dump())
    assert all(isinstance(v, ALLOWED_TYPES) for v in values)
    assert not any(isinstance(v, Enum) for v in values)


def test_rows_have_no_personal_data_keys(rows: GraphRows) -> None:
    assert not (_keys(rows.model_dump()) & PII_KEYS)


def test_accident_row(rows: GraphRows) -> None:
    row = next(r for r in rows.accidents if r["props"]["accident_id"] == "SIN-2025-0001")
    props = row["props"]
    assert props["status"] == "vigente"
    assert props["is_active"] is True
    assert (props["deaths"], props["year"], props["hour"]) == (1, 2025, 5)
    assert props["occurred_at"].utcoffset() is not None
    assert props["date"] == date(2025, 1, 12)
    assert (props["latitude"], props["longitude"]) == (-1.2497, -78.6237)
    assert "km" not in props
    assert row["km"] == 128.0
    assert row["road"] == "Panamericana E35 (Troncal de la Sierra)"
    assert row["parish_id"] == "Tungurahua|Ambato|Pasa"
    assert (row["accident_type"], row["cause"]) == ("choque", "invadir_carril")


def test_ids_and_links(rows: GraphRows) -> None:
    assert {
        "canton_id": "Pichincha|Quito",
        "name": "Quito",
        "province": "Pichincha",
    } in rows.cantons
    assert rows.replacements == [{"annulled": "SIN-2026-0010", "replacement": "SIN-2026-0011"}]
    assert rows.supersedes == [{"report_id": "INF-2026-01", "previous": "INF-2025-01"}]
    assert sum(r["vehicle_id"] is None for r in rows.people) == 5
    assert {s["props"]["section_id"] for s in rows.sections} >= {"INF-2026-02-S1", "INF-2026-02-S3"}


def test_catalog_nodes(rows: GraphRows) -> None:
    types = {t["code"]: t for t in rows.accident_types}
    assert types["perdida_de_pista"]["name"] == "Perdida de pista"
    assert types["choque"]["definition"].startswith("colisi")
    assert {"code": "exceso_de_velocidad", "name": "Exceso de velocidad"} in rows.causes
    assert {"name": "E15", "code": "E15"} in rows.roads
    assert rows.dataset["sha256"] == (
        "77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280"
    )


def test_datetimes_use_a_fixed_offset_not_zoneinfo(rows: GraphRows) -> None:
    # Regresion: el driver con ZoneInfo provoca un fallo de segmentacion en Python 3.12.15.
    datetimes = [v for v in _values(rows.model_dump()) if isinstance(v, datetime)]
    assert len(datetimes) == 30
    assert all(isinstance(v.tzinfo, timezone) for v in datetimes)
    assert not any(isinstance(v.tzinfo, ZoneInfo) for v in datetimes)
    assert {v.isoformat()[-6:] for v in datetimes} == {"-05:00"}


def test_search_copies_are_accent_folded(rows: GraphRows) -> None:
    accident = rows.accidents[0]["props"]
    assert accident["narrative_search"].isascii()
    assert accident["narrative_search"] == accident["narrative_search"].casefold()
    section = rows.sections[0]["props"]
    assert section["text_search"].isascii()
    assert section["title_search"].isascii()
    # El texto original se conserva para mostrarlo.
    assert any(not s["props"]["text"].isascii() for s in rows.sections)
