import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from accident_agent.ingestion.raw_models import RawDataset, RawPerson, RawRecord

REAL_FILE = Path(__file__).resolve().parents[2] / "data" / "siniestros_raw.json"


@pytest.fixture(scope="module")
def raw_bytes() -> bytes:
    return REAL_FILE.read_bytes()


@pytest.fixture(scope="module")
def raw_json(raw_bytes: bytes) -> Any:
    return json.loads(raw_bytes)


@pytest.fixture(scope="module")
def dataset(raw_bytes: bytes) -> RawDataset:
    return RawDataset.model_validate_json(raw_bytes)


def _pii_values(raw_json: Any) -> set[str]:
    values: set[str] = set()
    for record in raw_json["registros"]:
        for person in record["personas"]:
            values.update({person["nombre"], person["cedula"]})
            if person["placa_vehiculo"]:
                values.add(person["placa_vehiculo"])
        values.update(v["placa"] for v in record["vehiculos"])
    return values


def test_real_file_is_accepted(dataset: RawDataset) -> None:
    assert len(dataset.registros) == 31
    assert sum(len(r.vehiculos) for r in dataset.registros) == 50
    assert sum(len(r.personas) for r in dataset.registros) == 81
    assert dataset.metadata.total_registros == 31


def test_reserved_report_is_dropped_on_read(dataset: RawDataset) -> None:
    assert [r.id for r in dataset.informes] == [
        "INF-2025-01",
        "INF-2026-01",
        "INF-2026-02",
        "INF-2026-03",
    ]
    assert dataset.excluded_report_ids == ["INF-RES-01"]


def test_original_types_are_preserved(dataset: RawDataset) -> None:
    damages = {type(r.danos_materiales) for r in dataset.registros}
    assert damages == {int, str}
    ages = {type(p.edad) for r in dataset.registros for p in r.personas}
    assert ages == {int, str}
    alcohol = {type(p.alcohol_gl) for r in dataset.registros for p in r.personas}
    assert alcohol == {float, str, type(None)}
    dates = {type(r.fecha_hora).__name__ for r in dataset.registros}
    assert dates == {"str", "RawDateParts"}


def test_personal_data_never_reaches_the_model(dataset: RawDataset, raw_json: Any) -> None:
    person = dataset.registros[0].personas[0]
    assert not hasattr(person, "nombre")
    assert not hasattr(person, "cedula")
    dumped = dataset.model_dump_json()
    shown = repr(dataset)
    leaked = [v for v in _pii_values(raw_json) if v in dumped or v in shown]
    assert leaked == []


def test_plates_stay_available_for_linking(dataset: RawDataset) -> None:
    record = dataset.registros[0]
    plates = {v.placa for v in record.vehiculos}
    assert all(p.placa_vehiculo in plates for p in record.personas if p.placa_vehiculo)


def _record(raw_json: Any) -> dict[str, Any]:
    return deepcopy(raw_json["registros"][0])


def test_unknown_key_is_rejected(raw_json: Any) -> None:
    record = _record(raw_json)
    record["personas"][0]["telefono"] = "0999999999"
    with pytest.raises(ValidationError, match="telefono"):
        RawRecord.model_validate(record)


def test_missing_key_is_rejected_but_null_is_accepted(raw_json: Any) -> None:
    record = _record(raw_json)
    record["ubicacion"]["km"] = None
    assert RawRecord.model_validate(record).ubicacion.km is None
    del record["ubicacion"]["km"]
    with pytest.raises(ValidationError, match="km"):
        RawRecord.model_validate(record)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("personas", 0, "edad"), 39.5),
        (("danos_materiales",), [1]),
        (("version",), "2"),
        (("ubicacion", "coordenadas"), [1.0, 2.0]),
    ],
)
def test_types_outside_the_observed_ones_are_rejected(
    raw_json: Any, path: tuple[Any, ...], value: Any
) -> None:
    record = _record(raw_json)
    target = record
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValidationError):
        RawRecord.model_validate(record)


def test_errors_do_not_show_input_values(raw_json: Any) -> None:
    person = deepcopy(raw_json["registros"][0]["personas"][0])
    person["edad"] = [person["cedula"]]
    with pytest.raises(ValidationError) as info:
        RawPerson.model_validate(person)
    message = str(info.value)
    assert person["cedula"] not in message
    assert person["nombre"] not in message
    assert person["placa_vehiculo"] not in message
