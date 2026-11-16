from collections import Counter
from pathlib import Path

import pytest
from pydantic import SecretStr

from accident_agent.config import Settings
from accident_agent.ingestion.__main__ import run_load
from accident_agent.ingestion.neo4j_writer import graph_rows
from accident_agent.ingestion.pipeline import run_pipeline
from accident_agent.ingestion.verification import (
    CONTROL_VALUES,
    KNOWN_SHA256,
    VerificationReport,
    compare,
)

ROOT = Path(__file__).resolve().parents[2]
REAL_FILE = ROOT / "data" / "siniestros_raw.json"


def test_known_sha_matches_the_recorded_one() -> None:
    recorded = (ROOT / "data" / "siniestros_raw.json.sha256").read_text().split()[0]
    assert recorded == KNOWN_SHA256


def test_expected_graph_counts_match_the_rows_the_writer_creates() -> None:
    rows = graph_rows(run_pipeline(REAL_FILE))
    nodes = {
        "Dataset": 1,
        "Province": len(rows.provinces),
        "Canton": len(rows.cantons),
        "Parish": len(rows.parishes),
        "Road": len(rows.roads),
        "AccidentType": len(rows.accident_types),
        "Cause": len(rows.causes),
        "VehicleType": len(rows.vehicle_types),
        "Accident": len(rows.accidents),
        "Vehicle": len(rows.vehicles),
        "Person": len(rows.people),
        "Report": len(rows.reports),
        "ReportSection": len(rows.sections),
    }
    assert nodes == CONTROL_VALUES["nodes"]
    rels = Counter(
        {
            "BELONGS_TO": len(rows.cantons) + len(rows.parishes),
            "OCCURRED_IN": len(rows.accidents),
            "ON_ROAD": len(rows.accidents),
            "HAS_CAUSE": len(rows.accidents),
            "OF_TYPE": len(rows.accidents) + len(rows.vehicles),
            "REPLACED_BY": len(rows.replacements),
            "INVOLVED_IN": len(rows.vehicles),
            "PARTICIPATED_IN": len(rows.people),
            "RODE_IN": sum(p["vehicle_id"] is not None for p in rows.people),
            "HAS_SECTION": len(rows.sections),
            "SUPERSEDES": len(rows.supersedes),
            "ANALYZES_ROAD": len(rows.report_roads),
        }
    )
    assert dict(rels) == CONTROL_VALUES["relationships"]


def test_compare_reports_each_difference() -> None:
    observed = dict(CONTROL_VALUES) | {"active_accidents": 30, "nodes": {"Accident": 31}}
    mismatches = compare(observed, CONTROL_VALUES)
    assert len(mismatches) == 2
    assert mismatches[0].startswith("active_accidents: se obtuvo 30, se esperaba 29")
    assert compare(dict(CONTROL_VALUES), CONTROL_VALUES) == []


@pytest.mark.parametrize(
    ("enforced", "mismatches", "findings", "ok"),
    [
        (True, [], [], True),
        (True, ["x"], [], False),
        (False, ["x"], [], True),
        (False, [], ["Accident.narrative: cedula"], False),
    ],
)
def test_report_ok(enforced: bool, mismatches: list[str], findings: list[str], ok: bool) -> None:
    report = VerificationReport(
        observed={}, mismatches=mismatches, enforced=enforced, personal_data_findings=findings
    )
    assert report.ok is ok


def _settings(data_file: Path = REAL_FILE) -> Settings:
    # Puerto 1: nada escucha ahi, asi que Neo4j "no responde" sin esperar.
    return Settings(
        _env_file=None,
        neo4j_uri="bolt://127.0.0.1:1",
        neo4j_password=SecretStr("x"),
        data_file=data_file,
    )


def test_loader_fails_clearly_when_the_file_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run_load(_settings(data_file=tmp_path / "no.json"), wait_attempts=1) == 1
    assert "no se encontro el archivo de datos" in capsys.readouterr().out


def test_loader_fails_when_the_original_changed(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "siniestros_raw.json"
    copy.write_bytes(REAL_FILE.read_bytes() + b" ")
    (tmp_path / "siniestros_raw.json.sha256").write_text(f"{KNOWN_SHA256}  siniestros_raw.json\n")
    assert run_load(_settings(data_file=copy), wait_attempts=1) == 1
    assert "el original cambio" in capsys.readouterr().out


def test_loader_fails_clearly_when_neo4j_is_down(capsys: pytest.CaptureFixture[str]) -> None:
    assert run_load(_settings(), wait_attempts=1) == 1
    out = capsys.readouterr().out
    assert "Neo4j no responde en bolt://127.0.0.1:1" in out
    assert "carga:" not in out
