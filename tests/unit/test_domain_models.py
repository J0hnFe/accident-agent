from datetime import date, datetime
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from accident_agent.domain.catalogs import (
    AccidentType,
    Cause,
    Classification,
    Lighting,
    PersonCondition,
    PersonRole,
    Protection,
    Province,
    RecordStatus,
    ReportStatus,
    Sex,
    Surface,
    VehicleService,
    VehicleType,
    Weather,
)
from accident_agent.domain.models import (
    Accident,
    CleanDataset,
    Location,
    Person,
    Report,
    ReportSection,
    Vehicle,
)
from accident_agent.ingestion.normalizers import DATA_TIMEZONE

AID = "SIN-2025-0001"


def _vehicle(n: int = 1, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "vehicle_id": f"{AID}-V{n}",
        "vehicle_type": VehicleType.BUS,
        "brand": "HINO",
        "model": "AK",
        "year": 2018,
        "service": VehicleService.PUBLICO,
    }
    data.update(overrides)
    return data


def _person(n: int = 1, **overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "person_id": f"{AID}-P{n}",
        "role": PersonRole.CONDUCTOR,
        "age": 40,
        "sex": Sex.M,
        "condition": PersonCondition.HERIDO_LEVE,
        "alcohol_gl": 0.0,
        "protection": Protection.CINTURON,
        "days_until_death": None,
        "vehicle_id": f"{AID}-V1",
    }
    data.update(overrides)
    return data


def _location(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "province": Province.CHIMBORAZO,
        "canton": "Riobamba",
        "parish": "Lizarzaburu",
        "road": "Panamericana E35 (Troncal de la Sierra)",
        "road_code": "E35",
        "km": 128.0,
        "latitude": -1.2497,
        "longitude": -78.6237,
    }
    data.update(overrides)
    return data


def _accident(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "accident_id": AID,
        "version": 1,
        "versions_count": 1,
        "status": RecordStatus.VIGENTE,
        "updated_at": date(2025, 1, 13),
        "occurred_at": datetime(2025, 1, 12, 5, 40, tzinfo=DATA_TIMEZONE),
        "accident_type": AccidentType.CHOQUE,
        "cause": Cause.EXCESO_DE_VELOCIDAD,
        "weather": Weather.NEBLINA,
        "surface": Surface.HUMEDA,
        "lighting": Lighting.AMANECER_ATARDECER,
        "damages_usd": 18500.0,
        "location": Location(**_location()),
        "vehicles": [Vehicle(**_vehicle(1)), Vehicle(**_vehicle(2))],
        "people": [
            Person(**_person(1, condition=PersonCondition.FALLECIDO, days_until_death=6)),
            Person(**_person(2, condition=PersonCondition.HERIDO_GRAVE)),
            Person(**_person(3, vehicle_id=f"{AID}-V2")),
            Person(**_person(4, condition=PersonCondition.ILESO, vehicle_id=f"{AID}-V2")),
        ],
        "summary_mismatch": False,
        "narrative": "Choque frontal en la Panamericana.",
        "annulment_reason": None,
        "replaced_by": None,
    }
    data.update(overrides)
    return data


def _report(**overrides: Any) -> dict[str, Any]:
    data: dict[str, Any] = {
        "report_id": "INF-2026-01",
        "title": "Informe del corredor E35",
        "date": date(2026, 2, 12),
        "status": ReportStatus.VIGENTE,
        "classification": Classification.PUBLICO,
        "road": "Panamericana E35 (Troncal de la Sierra)",
        "road_code": "E35",
        "supersedes": None,
        "sections": [
            ReportSection(order=1, title="Resumen", text="Texto uno."),
            ReportSection(order=2, title="Causas", text="Texto dos."),
        ],
    }
    data.update(overrides)
    return data


def test_valid_accident_and_derived_fields() -> None:
    accident = Accident(**_accident())
    assert (accident.deaths, accident.injured, accident.unharmed) == (1, 2, 1)
    assert accident.is_active is True
    assert accident.date == date(2025, 1, 12)
    assert (accident.year, accident.month, accident.hour) == (2025, 1, 5)
    dumped = accident.model_dump()
    for key in ("deaths", "injured", "unharmed", "is_active", "date", "year", "month", "hour"):
        assert key in dumped


def test_annulled_accident() -> None:
    accident = Accident(
        **_accident(
            status=RecordStatus.ANULADO,
            annulment_reason="Ubicacion erronea",
            replaced_by="SIN-2025-0002",
        )
    )
    assert accident.is_active is False


PII_FIELD_NAMES = {"nombre", "cedula", "placa", "placa_vehiculo", "name", "plate", "national_id"}


@pytest.mark.parametrize(
    "model", [Accident, Person, Vehicle, Location, Report, ReportSection, CleanDataset]
)
def test_models_have_no_personal_data_fields(model: type[BaseModel]) -> None:
    assert not (set(model.model_fields) & PII_FIELD_NAMES)


@pytest.mark.parametrize(("builder", "model"), [(_person, Person), (_vehicle, Vehicle)])
@pytest.mark.parametrize("extra", ["name", "cedula", "plate"])
def test_extra_fields_are_rejected(builder: Any, model: type[BaseModel], extra: str) -> None:
    with pytest.raises(ValidationError, match=extra):
        model(**builder(**{extra: "x"}))


@pytest.mark.parametrize(
    ("builder", "model", "overrides"),
    [
        (_person, Person, {"age": "40"}),
        (_person, Person, {"role": "conductor"}),
        (_person, Person, {"age": 121}),
        (_person, Person, {"alcohol_gl": -0.1}),
        (_person, Person, {"person_id": "SIN-2025-0001-X1"}),
        (_person, Person, {"condition": PersonCondition.HERIDO_LEVE, "days_until_death": 3}),
        (_person, Person, {"condition": PersonCondition.FALLECIDO, "days_until_death": 31}),
        (_person, Person, {"role": PersonRole.PEATON}),
        (_vehicle, Vehicle, {"brand": "Hino"}),
        (_vehicle, Vehicle, {"model": " AK"}),
        (_vehicle, Vehicle, {"year": 1800}),
        (_location, Location, {"road_code": "35"}),
        (_location, Location, {"latitude": None}),
        (_location, Location, {"canton": "Rio  bamba"}),
        (_location, Location, {"km": -1.0}),
        (_report, Report, {"report_id": "INF-RES-01"}),
        (_report, Report, {"classification": Classification.RESERVADO}),
        (_report, Report, {"supersedes": "INF-2026-01"}),
        (_report, Report, {"road": None}),
        (
            _report,
            Report,
            {"sections": [ReportSection(order=2, title="Unica", text="Texto.")]},
        ),
    ],
)
def test_invalid_values_are_rejected(
    builder: Any, model: type[BaseModel], overrides: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        model(**builder(**overrides))


def test_pedestrian_without_vehicle_is_valid() -> None:
    person = Person(**_person(role=PersonRole.PEATON, vehicle_id=None))
    assert person.vehicle_id is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"accident_id": "SIN-25-1"},
        {"occurred_at": datetime(2025, 1, 12, 5, 40)},
        {"updated_at": date(2025, 1, 11)},
        {"damages_usd": -1.0},
        {"narrative": "  texto con espacios "},
        {"vehicles": []},
        {"people": []},
        {"vehicles": [Vehicle(**_vehicle(1, vehicle_id="SIN-2025-0002-V1"))]},
        {"people": [Person(**_person(1, vehicle_id=f"{AID}-V9"))]},
        {"vehicles": [Vehicle(**_vehicle(1)), Vehicle(**_vehicle(1))]},
        {"annulment_reason": "No aplica a un vigente"},
        {"replaced_by": "SIN-2025-0002"},
        {"status": RecordStatus.ANULADO, "replaced_by": AID},
        {"versions_count": 0},
    ],
)
def test_accident_invariants(overrides: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Accident(**_accident(**overrides))


def test_models_are_frozen() -> None:
    accident = Accident(**_accident())
    with pytest.raises(ValidationError):
        accident.damages_usd = 1.0  # type: ignore[misc]


def _dataset(accidents: list[Accident], reports: list[Report]) -> CleanDataset:
    return CleanDataset(accidents=accidents, reports=reports)


def test_valid_dataset_with_replacement_and_superseded_report() -> None:
    annulled = Accident(
        **_accident(
            status=RecordStatus.ANULADO,
            annulment_reason="Ubicacion erronea",
            replaced_by="SIN-2025-0002",
        )
    )
    replacement = Accident(**_replace_id(_accident(), "SIN-2025-0002"))
    old = Report(**_report(report_id="INF-2025-01", status=ReportStatus.REEMPLAZADO))
    new = Report(**_report(supersedes="INF-2025-01"))
    dataset = _dataset([annulled, replacement], [old, new])
    assert len(dataset.accidents) == 2


def _replace_id(data: dict[str, Any], accident_id: str) -> dict[str, Any]:
    data["accident_id"] = accident_id
    data["vehicles"] = [
        Vehicle(**_vehicle(n, vehicle_id=f"{accident_id}-V{n}")) for n in range(1, 3)
    ]
    data["people"] = [
        Person(**_person(1, person_id=f"{accident_id}-P1", vehicle_id=f"{accident_id}-V1"))
    ]
    return data


def test_dataset_rejects_duplicate_ids() -> None:
    accident = Accident(**_accident())
    with pytest.raises(ValidationError, match="duplicado"):
        _dataset([accident, accident], [])
    report = Report(**_report())
    with pytest.raises(ValidationError, match="duplicado"):
        _dataset([], [report, report])


def test_dataset_rejects_broken_replacement_links() -> None:
    annulled = Accident(
        **_accident(
            status=RecordStatus.ANULADO,
            annulment_reason="Ubicacion erronea",
            replaced_by="SIN-2025-0002",
        )
    )
    with pytest.raises(ValidationError, match="SIN-2025-0002"):
        _dataset([annulled], [])
    also_annulled = Accident(
        **_replace_id(
            _accident(status=RecordStatus.ANULADO, annulment_reason="Otro motivo"),
            "SIN-2025-0002",
        )
    )
    with pytest.raises(ValidationError, match="vigente"):
        _dataset([annulled, also_annulled], [])


def test_dataset_rejects_broken_supersedes_links() -> None:
    new = Report(**_report(supersedes="INF-2025-01"))
    with pytest.raises(ValidationError, match="INF-2025-01"):
        _dataset([], [new])
    old_still_active = Report(**_report(report_id="INF-2025-01"))
    with pytest.raises(ValidationError, match="reemplazado"):
        _dataset([], [old_still_active, new])
