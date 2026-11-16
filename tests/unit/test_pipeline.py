import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from accident_agent.domain.catalogs import (
    AccidentType,
    PersonRole,
    Province,
    RecordStatus,
    ReportStatus,
    VehicleType,
)
from accident_agent.domain.models import CleanDataset
from accident_agent.ingestion.pipeline import (
    IngestionError,
    build_dataset,
    parse_raw,
    run_pipeline,
    verify_integrity,
)
from accident_agent.ingestion.raw_models import RawDataset

ROOT = Path(__file__).resolve().parents[2]
REAL_FILE = ROOT / "data" / "siniestros_raw.json"
SHA_FILE = ROOT / "data" / "siniestros_raw.json.sha256"
REAL_SHA = "77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280"


@pytest.fixture(scope="module")
def dataset() -> CleanDataset:
    return run_pipeline(REAL_FILE)


@pytest.fixture
def raw_json() -> Any:
    return json.loads(REAL_FILE.read_text(encoding="utf-8"))


def _build(data: Any) -> CleanDataset:
    return build_dataset(RawDataset.model_validate(data), sha256=REAL_SHA, source_file="x.json")


def _active(dataset: CleanDataset) -> list[Any]:
    return [a for a in dataset.accidents if a.is_active]


# Valores de control de la Etapa 2 (seccion 8 del plan) que no requieren Neo4j.


def test_control_values(dataset: CleanDataset) -> None:
    active = _active(dataset)
    assert len(dataset.accidents) == 30
    assert len(active) == 29
    annulled = [(a.accident_id, a.replaced_by) for a in dataset.accidents if not a.is_active]
    assert annulled == [("SIN-2026-0010", "SIN-2026-0011")]
    assert sum(a.deaths for a in active) == 18
    assert sum(a.injured for a in active) == 44
    assert sum(a.deaths > 0 for a in active) == 15
    moto = [a for a in active if any(v.vehicle_type is VehicleType.MOTOCICLETA for v in a.vehicles)]
    assert len(moto) == 7
    provinces = [a.location.province for a in active]
    assert (provinces.count(Province.PICHINCHA), provinces.count(Province.GUAYAS)) == (5, 5)
    e35 = [a for a in active if a.location.road_code == "E35"]
    assert len(e35) == 6
    assert sorted(a.accident_id for a in e35 if a.deaths) == [
        "SIN-2025-0001",
        "SIN-2025-0013",
        "SIN-2026-0004",
        "SIN-2026-0007",
    ]
    assert len(dataset.reports) == 4


def test_latest_version_is_loaded(dataset: CleanDataset) -> None:
    accident = next(a for a in dataset.accidents if a.accident_id == "SIN-2025-0007")
    assert (accident.version, accident.versions_count, accident.damages_usd) == (2, 2, 4100.0)


def test_annulled_record(dataset: CleanDataset) -> None:
    annulled = next(a for a in dataset.accidents if a.accident_id == "SIN-2026-0010")
    assert annulled.status is RecordStatus.ANULADO
    assert annulled.annulment_reason is not None
    assert annulled.annulment_reason.startswith("Ubicaci")


def test_summary_mismatch_is_derived_from_people(dataset: CleanDataset) -> None:
    flagged = [a.accident_id for a in dataset.accidents if a.summary_mismatch]
    assert flagged == ["SIN-2025-0012"]
    accident = next(a for a in dataset.accidents if a.accident_id == "SIN-2025-0012")
    assert accident.injured == 2


def test_synthetic_ids_and_vehicle_links(dataset: CleanDataset) -> None:
    accident = next(a for a in dataset.accidents if a.accident_id == "SIN-2025-0001")
    assert [v.vehicle_id for v in accident.vehicles] == ["SIN-2025-0001-V1", "SIN-2025-0001-V2"]
    assert accident.people[0].person_id == "SIN-2025-0001-P1"
    assert all(p.vehicle_id is not None for p in accident.people)
    people = [p for a in dataset.accidents for p in a.people]
    assert len(people) == 80
    pedestrians = [p for p in people if p.role is PersonRole.PEATON]
    assert len(pedestrians) == 5
    assert all(p.vehicle_id is None for p in pedestrians)
    assert sum(len(a.vehicles) for a in dataset.accidents) == 49


def test_reports(dataset: CleanDataset) -> None:
    reports = {r.report_id: r for r in dataset.reports}
    assert sorted(reports) == ["INF-2025-01", "INF-2026-01", "INF-2026-02", "INF-2026-03"]
    assert reports["INF-2026-01"].supersedes == "INF-2025-01"
    assert reports["INF-2025-01"].status is ReportStatus.REEMPLAZADO
    assert {r.report_id for r in dataset.reports if r.road_code == "E35"} == {
        "INF-2025-01",
        "INF-2026-01",
    }
    assert [s.order for s in reports["INF-2026-02"].sections] == [1, 2, 3]


def test_accident_type_definitions_come_from_the_dictionary(dataset: CleanDataset) -> None:
    definitions = dataset.accident_type_definitions
    assert set(definitions) == set(AccidentType)
    assert definitions[AccidentType.CHOQUE].startswith("colisi")
    assert "objeto fijo" in definitions[AccidentType.ESTRELLAMIENTO]
    assert "calzada" in definitions[AccidentType.PERDIDA_DE_PISTA]


def test_dataset_info(dataset: CleanDataset) -> None:
    assert dataset.info.sha256 == REAL_SHA
    assert dataset.info.source_file == "siniestros_raw.json"
    assert dataset.info.generated.isoformat() == "2026-11-09"
    assert dataset.info.timezone.startswith("America/Guayaquil")


def test_output_is_sorted_and_deterministic(dataset: CleanDataset) -> None:
    ids = [a.accident_id for a in dataset.accidents]
    assert ids == sorted(ids)
    assert run_pipeline(REAL_FILE) == dataset


def test_order_of_records_does_not_matter(raw_json: Any) -> None:
    reversed_data = deepcopy(raw_json)
    reversed_data["registros"].reverse()
    reversed_data["informes"].reverse()
    assert _build(reversed_data) == _build(raw_json)


def test_normalization_error_carries_record_and_path(raw_json: Any) -> None:
    record = raw_json["registros"][3]
    record["ubicacion"]["km"] = "doce"
    with pytest.raises(IngestionError) as info:
        _build(raw_json)
    error = info.value
    assert (error.record_id, error.path) == (record["id_parte"], "registros[].ubicacion.km")
    assert "doce" in str(error)


def test_unknown_category_is_an_error(raw_json: Any) -> None:
    raw_json["registros"][0]["personas"][1]["condicion"] = "DESAPARECIDO"
    with pytest.raises(IngestionError, match="personas"):
        _build(raw_json)


def test_duplicate_id_and_version_is_an_error(raw_json: Any) -> None:
    raw_json["registros"].append(deepcopy(raw_json["registros"][0]))
    with pytest.raises(IngestionError, match="version"):
        _build(raw_json)


def test_replacement_must_point_to_an_annulled_record(raw_json: Any) -> None:
    replacer = next(r for r in raw_json["registros"] if r.get("reemplaza_a"))
    replacer["reemplaza_a"] = "SIN-2025-0001"
    with pytest.raises(IngestionError, match="anulado"):
        _build(raw_json)
    replacer["reemplaza_a"] = "SIN-2099-0001"
    with pytest.raises(IngestionError, match="SIN-2099-0001"):
        _build(raw_json)


def test_unknown_plate_is_an_error_without_showing_it(raw_json: Any) -> None:
    person = raw_json["registros"][0]["personas"][0]
    person["placa_vehiculo"] = "ZZZ-0000"
    with pytest.raises(IngestionError) as info:
        _build(raw_json)
    assert "ZZZ-0000" not in str(info.value)
    assert info.value.record_id == raw_json["registros"][0]["id_parte"]


def test_missing_definitions_are_an_error(raw_json: Any) -> None:
    for report in raw_json["informes"]:
        report["secciones"] = [
            s for s in report["secciones"] if "tipos de siniestro" not in s["titulo"].lower()
        ]
    with pytest.raises(IngestionError, match="definicion"):
        _build(raw_json)


def test_invalid_structure_is_reported_without_values(raw_json: Any) -> None:
    person = raw_json["registros"][0]["personas"][0]
    person["telefono"] = "0999999999"
    with pytest.raises(IngestionError) as info:
        parse_raw(json.dumps(raw_json).encode())
    message = str(info.value)
    assert "telefono" in message
    assert "0999999999" not in message
    assert person["cedula"] not in message


def test_verify_integrity(tmp_path: Path) -> None:
    assert verify_integrity(REAL_FILE, SHA_FILE) == REAL_SHA
    copy = tmp_path / "datos.json"
    copy.write_bytes(REAL_FILE.read_bytes() + b"\n")
    sha_file = tmp_path / "datos.json.sha256"
    sha_file.write_text(f"{REAL_SHA}  datos.json\n")
    with pytest.raises(IngestionError, match="SHA-256"):
        verify_integrity(copy, sha_file)
    # Sin archivo de referencia solo se calcula.
    assert (
        verify_integrity(copy, tmp_path / "no-existe")
        == hashlib.sha256(copy.read_bytes()).hexdigest()
    )
