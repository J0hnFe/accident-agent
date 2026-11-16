import json
import re
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest

from accident_agent.domain.catalogs import (
    ACCIDENT_TYPES,
    CAUSES,
    CLASSIFICATIONS,
    LIGHTINGS,
    PERSON_CONDITIONS,
    PERSON_ROLES,
    PROTECTIONS,
    PROVINCES,
    RECORD_STATUSES,
    REPORT_STATUSES,
    ROAD_ALIASES,
    SEXES,
    SURFACES,
    VEHICLE_SERVICES,
    VEHICLE_TYPES,
    WEATHERS,
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
    build_lookup,
)
from accident_agent.ingestion.normalizers import normalize_key

REAL_FILE = Path(__file__).resolve().parents[2] / "data" / "siniestros_raw.json"

ALL_LOOKUPS: dict[str, Mapping[str, StrEnum]] = {
    "accident_type": ACCIDENT_TYPES,
    "cause": CAUSES,
    "weather": WEATHERS,
    "surface": SURFACES,
    "lighting": LIGHTINGS,
    "vehicle_type": VEHICLE_TYPES,
    "vehicle_service": VEHICLE_SERVICES,
    "person_role": PERSON_ROLES,
    "person_condition": PERSON_CONDITIONS,
    "sex": SEXES,
    "protection": PROTECTIONS,
    "record_status": RECORD_STATUSES,
    "report_status": REPORT_STATUSES,
    "classification": CLASSIFICATIONS,
    "province": PROVINCES,
}


def _resolve(lookup: Mapping[str, StrEnum], raw: str) -> StrEnum:
    return lookup[normalize_key(raw)]


# Todas las escrituras observadas en el JSON (reglas_normalizacion.md, seccion 3).
# Escapes \u para mantener el codigo en ASCII.
@pytest.mark.parametrize(
    ("lookup", "raw", "expected"),
    [
        (ACCIDENT_TYPES, "CHOQUE", AccidentType.CHOQUE),
        (ACCIDENT_TYPES, "Choque", AccidentType.CHOQUE),
        (ACCIDENT_TYPES, "Atropello", AccidentType.ATROPELLO),
        (ACCIDENT_TYPES, "ATROPELLO", AccidentType.ATROPELLO),
        (ACCIDENT_TYPES, "Estrellamiento", AccidentType.ESTRELLAMIENTO),
        (ACCIDENT_TYPES, "PERDIDA DE PISTA", AccidentType.PERDIDA_DE_PISTA),
        (ACCIDENT_TYPES, "P\u00e9rdida de pista", AccidentType.PERDIDA_DE_PISTA),
        (ACCIDENT_TYPES, "VOLCAMIENTO", AccidentType.VOLCAMIENTO),
        (ACCIDENT_TYPES, "Volcamiento", AccidentType.VOLCAMIENTO),
        (CAUSES, "EXCESO DE VELOCIDAD", Cause.EXCESO_DE_VELOCIDAD),
        (CAUSES, "Exceso de velocidad", Cause.EXCESO_DE_VELOCIDAD),
        (CAUSES, "VELOCIDAD EXCESIVA", Cause.EXCESO_DE_VELOCIDAD),
        (
            CAUSES,
            "CONDUCIR BAJO EFECTOS DEL ALCOHOL",
            Cause.CONDUCIR_BAJO_EFECTOS_DEL_ALCOHOL,
        ),
        (
            CAUSES,
            "Conducir bajo efectos del alcohol",
            Cause.CONDUCIR_BAJO_EFECTOS_DEL_ALCOHOL,
        ),
        (CAUSES, "CONDUCIR EN ESTADO DE EBRIEDAD", Cause.CONDUCIR_BAJO_EFECTOS_DEL_ALCOHOL),
        (CAUSES, "Invadir carril", Cause.INVADIR_CARRIL),
        (CAUSES, "Distracci\u00f3n del conductor", Cause.DISTRACCION_DEL_CONDUCTOR),
        (CAUSES, "DISTRACCION DEL CONDUCTOR", Cause.DISTRACCION_DEL_CONDUCTOR),
        (CAUSES, "PEATON EN LA VIA", Cause.PEATON_EN_LA_VIA),
        (CAUSES, "Peat\u00f3n en la v\u00eda", Cause.PEATON_EN_LA_VIA),
        (CAUSES, "MAL ESTADO DE LA VIA", Cause.MAL_ESTADO_DE_LA_VIA),
        (CAUSES, "No respetar sem\u00e1foro", Cause.NO_RESPETAR_SEMAFORO),
        (CAUSES, "SOMNOLENCIA", Cause.SOMNOLENCIA),
        (CAUSES, "ADELANTAMIENTO INDEBIDO", Cause.ADELANTAMIENTO_INDEBIDO),
        (CAUSES, "Adelantamiento indebido", Cause.ADELANTAMIENTO_INDEBIDO),
        (CAUSES, "FALLO MECANICO", Cause.FALLO_MECANICO),
        (WEATHERS, "DESPEJADO", Weather.DESPEJADO),
        (WEATHERS, "LLUVIA", Weather.LLUVIA),
        (WEATHERS, "NEBLINA", Weather.NEBLINA),
        (SURFACES, "SECA", Surface.SECA),
        (SURFACES, "MOJADA", Surface.MOJADA),
        (SURFACES, "HUMEDA", Surface.HUMEDA),
        (LIGHTINGS, "DIURNA", Lighting.DIURNA),
        (LIGHTINGS, "NOCTURNA_CON_ILUMINACION", Lighting.NOCTURNA_CON_ILUMINACION),
        (LIGHTINGS, "NOCTURNA_SIN_ILUMINACION", Lighting.NOCTURNA_SIN_ILUMINACION),
        (LIGHTINGS, "AMANECER_ATARDECER", Lighting.AMANECER_ATARDECER),
        (VEHICLE_TYPES, "AUTOMOVIL", VehicleType.AUTOMOVIL),
        (VEHICLE_TYPES, "Autom\u00f3vil", VehicleType.AUTOMOVIL),
        (VEHICLE_TYPES, "Camioneta", VehicleType.CAMIONETA),
        (VEHICLE_TYPES, "CAMIONETA", VehicleType.CAMIONETA),
        (VEHICLE_TYPES, "MOTOCICLETA", VehicleType.MOTOCICLETA),
        (VEHICLE_TYPES, "Motocicleta", VehicleType.MOTOCICLETA),
        (VEHICLE_TYPES, "BUS", VehicleType.BUS),
        (VEHICLE_TYPES, "Bus", VehicleType.BUS),
        (VEHICLE_TYPES, "Cami\u00f3n", VehicleType.CAMION),
        (VEHICLE_TYPES, "CAMION", VehicleType.CAMION),
        (VEHICLE_TYPES, "Cami\u00f3n liviano", VehicleType.CAMION_LIVIANO),
        (VEHICLE_TYPES, "CAMION PESADO", VehicleType.CAMION_PESADO),
        (VEHICLE_TYPES, "Cami\u00f3n pesado", VehicleType.CAMION_PESADO),
        (VEHICLE_TYPES, "SUV", VehicleType.SUV),
        (VEHICLE_TYPES, "Taxi", VehicleType.TAXI),
        (VEHICLE_TYPES, "Tr\u00e1iler", VehicleType.TRAILER),
        (VEHICLE_SERVICES, "PARTICULAR", VehicleService.PARTICULAR),
        (VEHICLE_SERVICES, "particular", VehicleService.PARTICULAR),
        (VEHICLE_SERVICES, "carga", VehicleService.CARGA),
        (VEHICLE_SERVICES, "CARGA", VehicleService.CARGA),
        (VEHICLE_SERVICES, "p\u00fablico", VehicleService.PUBLICO),
        (VEHICLE_SERVICES, "PUBLICO", VehicleService.PUBLICO),
        (PERSON_ROLES, "CONDUCTOR", PersonRole.CONDUCTOR),
        (PERSON_ROLES, "conductor", PersonRole.CONDUCTOR),
        (PERSON_ROLES, "PASAJERO", PersonRole.PASAJERO),
        (PERSON_ROLES, "pasajero", PersonRole.PASAJERO),
        (PERSON_ROLES, "peat\u00f3n", PersonRole.PEATON),
        (PERSON_CONDITIONS, "FALLECIDO", PersonCondition.FALLECIDO),
        (PERSON_CONDITIONS, "Fallecido", PersonCondition.FALLECIDO),
        (PERSON_CONDITIONS, "HERIDO GRAVE", PersonCondition.HERIDO_GRAVE),
        (PERSON_CONDITIONS, "Herido grave", PersonCondition.HERIDO_GRAVE),
        (PERSON_CONDITIONS, "Herido leve", PersonCondition.HERIDO_LEVE),
        (PERSON_CONDITIONS, "HERIDO LEVE", PersonCondition.HERIDO_LEVE),
        (PERSON_CONDITIONS, "Ileso", PersonCondition.ILESO),
        (PERSON_CONDITIONS, "ILESO", PersonCondition.ILESO),
        (SEXES, "M", Sex.M),
        (SEXES, "Hombre", Sex.M),
        (SEXES, "MASCULINO", Sex.M),
        (SEXES, "FEMENINO", Sex.F),
        (SEXES, "F", Sex.F),
        (SEXES, "Mujer", Sex.F),
        (PROTECTIONS, "CINTURON", Protection.CINTURON),
        (PROTECTIONS, "SI - CINTURON", Protection.CINTURON),
        (PROTECTIONS, "Cintur\u00f3n de seguridad", Protection.CINTURON),
        (PROTECTIONS, "SI - CASCO", Protection.CASCO),
        (PROTECTIONS, "CASCO", Protection.CASCO),
        (PROTECTIONS, "NINGUNO", Protection.NINGUNA),
        (PROTECTIONS, "NO", Protection.NINGUNA),
        (PROTECTIONS, "N/A", Protection.NO_APLICA),
        (PROTECTIONS, "NO APLICA", Protection.NO_APLICA),
        (PROTECTIONS, "SIN DATO", Protection.NO_REGISTRADO),
        (PROTECTIONS, "", Protection.NO_REGISTRADO),
        (RECORD_STATUSES, "ACTIVO", RecordStatus.VIGENTE),
        (RECORD_STATUSES, "ANULADO", RecordStatus.ANULADO),
        (REPORT_STATUSES, "VIGENTE", ReportStatus.VIGENTE),
        (REPORT_STATUSES, "REEMPLAZADO", ReportStatus.REEMPLAZADO),
        (CLASSIFICATIONS, "PUBLICO", Classification.PUBLICO),
        (CLASSIFICATIONS, "RESERVADO", Classification.RESERVADO),
        (PROVINCES, "Pichincha", Province.PICHINCHA),
        (PROVINCES, "PICHINCHA", Province.PICHINCHA),
        (PROVINCES, "GUAYAS", Province.GUAYAS),
        (PROVINCES, "MANABI", Province.MANABI),
        (PROVINCES, "El Oro", Province.EL_ORO),
        (PROVINCES, "CANAR", Province.CANAR),
        (PROVINCES, "Los R\u00edos", Province.LOS_RIOS),
        (PROVINCES, "SUCUMBIOS", Province.SUCUMBIOS),
        (
            PROVINCES,
            "Santo Domingo de los Tsachilas",
            Province.SANTO_DOMINGO_DE_LOS_TSACHILAS,
        ),
        # Escenario 10: provincia valida sin siniestros en los datos.
        (PROVINCES, "Gal\u00e1pagos", Province.GALAPAGOS),
    ],
)
def test_observed_spellings_resolve(
    lookup: Mapping[str, StrEnum], raw: str, expected: StrEnum
) -> None:
    assert _resolve(lookup, raw) is expected


@pytest.fixture(scope="module")
def raw_data() -> Any:
    return json.loads(REAL_FILE.read_text(encoding="utf-8"))


def _observed(data: Any) -> dict[str, list[str]]:
    records = data["registros"]
    vehicles = [v for r in records for v in r["vehiculos"]]
    people = [p for r in records for p in r["personas"]]
    return {
        "accident_type": [r["tipo_siniestro"] for r in records],
        "cause": [r["causa_probable"] for r in records],
        "weather": [r["condiciones"]["clima"] for r in records],
        "surface": [r["condiciones"]["superficie"] for r in records],
        "lighting": [r["condiciones"]["iluminacion"] for r in records],
        "vehicle_type": [v["tipo_vehiculo"] for v in vehicles],
        "vehicle_service": [v["servicio"] for v in vehicles],
        "person_role": [p["rol"] for p in people],
        "person_condition": [p["condicion"] for p in people],
        "sex": [p["sexo"] for p in people],
        # null tambien es no_registrado, pero lo resuelve el normalizador (tarea 1.7).
        "protection": [p["proteccion"] for p in people if p["proteccion"] is not None],
        "record_status": [r["estado"] for r in records],
        "report_status": [i["estado"] for i in data["informes"]],
        "classification": [i["clasificacion"] for i in data["informes"]],
        "province": [r["ubicacion"]["provincia"] for r in records],
    }


# Canonicos distintos tras resolver los valores reales (reglas_normalizacion.md, seccion 3).
EXPECTED_DISTINCT = {
    "accident_type": 5,
    "cause": 10,
    "weather": 3,
    "surface": 3,
    "lighting": 4,
    "vehicle_type": 10,
    "vehicle_service": 3,
    "person_role": 3,
    "person_condition": 4,
    "sex": 2,
    "protection": 5,
    "record_status": 2,
    "report_status": 2,
    "classification": 2,
    "province": 17,
}


def test_every_real_value_resolves(raw_data: Any) -> None:
    observed = _observed(raw_data)
    for field, values in observed.items():
        lookup = ALL_LOOKUPS[field]
        missing = sorted({v for v in values if normalize_key(v) not in lookup})
        assert missing == [], field
        distinct = {_resolve(lookup, v) for v in values}
        assert len(distinct) == EXPECTED_DISTINCT[field], field


def test_closed_catalogs_are_fully_used_except_provinces(raw_data: Any) -> None:
    # Cada valor canonico existe por los datos o por el diccionario INF-2026-02;
    # solo las provincias incluyen valores sin siniestros (24 frente a 17).
    for field, values in _observed(raw_data).items():
        lookup = ALL_LOOKUPS[field]
        enum_cls = type(next(iter(lookup.values())))
        used = {_resolve(lookup, v) for v in values}
        if field == "province":
            assert len(enum_cls) == 24
        else:
            assert used == set(enum_cls), field


@pytest.mark.parametrize("field", sorted(ALL_LOOKUPS))
def test_lookup_keys_are_normalized(field: str) -> None:
    # Una clave que normalize_key no produce nunca se encontraria.
    for key in ALL_LOOKUPS[field]:
        assert normalize_key(key) == key


@pytest.mark.parametrize("field", sorted(ALL_LOOKUPS))
def test_canonical_values_are_ascii(field: str) -> None:
    enum_cls = type(next(iter(ALL_LOOKUPS[field].values())))
    for member in enum_cls:
        assert member.value.isascii()
        assert member.name == re.sub(r"[ -]", "_", member.value).upper()


@pytest.mark.parametrize(
    "enum_cls",
    [
        AccidentType,
        Cause,
        Weather,
        Surface,
        Lighting,
        VehicleType,
        VehicleService,
        PersonRole,
        PersonCondition,
        Protection,
        RecordStatus,
        ReportStatus,
        Classification,
    ],
)
def test_codes_are_snake_case(enum_cls: type[StrEnum]) -> None:
    for member in enum_cls:
        assert re.fullmatch(r"[a-z]+(_[a-z]+)*", member.value)


def test_every_member_is_reachable_by_its_own_value() -> None:
    for lookup in ALL_LOOKUPS.values():
        for member in set(lookup.values()):
            assert lookup[normalize_key(member.value)] is member
            assert lookup[normalize_key(member.value.replace("_", " "))] is member


def test_unknown_values_are_not_resolved() -> None:
    assert normalize_key("GRANIZO") not in WEATHERS
    assert normalize_key("Santo Domingo") not in PROVINCES
    assert normalize_key("Peaton") not in PROTECTIONS


def test_road_aliases() -> None:
    assert ROAD_ALIASES == {"e35": "panamericana e35 (troncal de la sierra)"}
    for alias, target in ROAD_ALIASES.items():
        assert normalize_key(alias) == alias
        assert normalize_key(target) == target


class _Color(StrEnum):
    ROJO = "rojo"
    VERDE = "verde"


def test_build_lookup_includes_own_forms_and_synonyms() -> None:
    lookup = build_lookup(_Color, {"colorado": _Color.ROJO})
    assert dict(lookup) == {"rojo": _Color.ROJO, "verde": _Color.VERDE, "colorado": _Color.ROJO}


def test_build_lookup_rejects_conflicting_synonym() -> None:
    with pytest.raises(ValueError, match="verde"):
        build_lookup(_Color, {"verde": _Color.ROJO})


def test_lookups_are_read_only() -> None:
    with pytest.raises(TypeError):
        WEATHERS["granizo"] = Weather.LLUVIA  # type: ignore[index]
