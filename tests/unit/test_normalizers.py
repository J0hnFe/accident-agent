import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from accident_agent.domain.catalogs import (
    CAUSES,
    PERSON_CONDITIONS,
    PERSON_ROLES,
    PROVINCES,
    SEXES,
    Cause,
    PersonCondition,
    PersonRole,
    Protection,
    Province,
    Sex,
)
from accident_agent.ingestion.normalizers import (
    NormalizationError,
    RoadRef,
    clean_text,
    display_name,
    normalize_key,
    normalize_protection,
    normalize_road,
    parse_alcohol,
    parse_amount,
    parse_coordinates,
    parse_int,
    parse_km,
    parse_occurred_at,
    parse_report_date,
    parse_update_date,
    split_brand_model,
    to_canonical,
)

REAL_FILE = Path(__file__).resolve().parents[2] / "data" / "siniestros_raw.json"
UTC_MINUS_5 = timedelta(hours=-5)

# Los ejemplos salen de docs/datos/reglas_normalizacion.md (valores reales del JSON).
# Escapes \u para mantener el codigo en ASCII.


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("HERIDO LEVE", "herido leve"),
        ("Herido leve", "herido leve"),
        ("  Cami\u00f3n   liviano ", "camion liviano"),
        ("p\u00fablico", "publico"),
        ("Ca\u00f1ar", "canar"),
        ("Ruminahui", "ruminahui"),
        ("Rumi\u00f1ahui", "ruminahui"),
        ("H\u00daMEDA", "humeda"),
        ("VIA CUENCA\u2013AZOGUES", "via cuenca-azogues"),
        ("V\u00eda Ba\u00f1os\u2013Puyo", "via banos-puyo"),
        ("Via A\u2014B", "via a-b"),
        ("", ""),
    ],
)
def test_normalize_key(raw: str, expected: str) -> None:
    assert normalize_key(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("GUAYAQUIL", "Guayaquil"),
        ("Guayaquil", "Guayaquil"),
        ("Ba\u00f1os de Agua Santa", "Banos de Agua Santa"),
        ("LA MARISCAL", "La Mariscal"),
        ("EL CAMBIO", "El Cambio"),
        ("Puerto Bol\u00edvar", "Puerto Bolivar"),
        ("AV. SIMON BOLIVAR (QUITO)", "Av. Simon Bolivar (Quito)"),
        ("Av. Sim\u00f3n Bol\u00edvar (Quito)", "Av. Simon Bolivar (Quito)"),
        ("Av. de las Am\u00e9ricas (Cuenca)", "Av. de las Americas (Cuenca)"),
        ("VIA A LA COSTA (GUAYAQUIL)", "Via a la Costa (Guayaquil)"),
        ("V\u00eda Quevedo\u2013Santo Domingo", "Via Quevedo-Santo Domingo"),
        ("AUTOPISTA NARCISA DE JESUS", "Autopista Narcisa de Jesus"),
    ],
)
def test_display_name(raw: str, expected: str) -> None:
    assert display_name(raw) == expected


def test_display_name_rejects_empty() -> None:
    with pytest.raises(NormalizationError):
        display_name("   ")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Panamericana E35 (Troncal de la Sierra)",
            RoadRef("Panamericana E35 (Troncal de la Sierra)", "E35"),
        ),
        (
            "PANAMERICANA E35 (TRONCAL DE LA SIERRA)",
            RoadRef("Panamericana E35 (Troncal de la Sierra)", "E35"),
        ),
        ("E35", RoadRef("Panamericana E35 (Troncal de la Sierra)", "E35")),
        ("Troncal Amaz\u00f3nica E45", RoadRef("Troncal Amazonica E45", "E45")),
        ("TRONCAL AMAZONICA E45", RoadRef("Troncal Amazonica E45", "E45")),
        ("E15", RoadRef("E15", "E15")),
        ("VIA A LA COSTA (GUAYAQUIL)", RoadRef("Via a la Costa (Guayaquil)", None)),
        ("VIA CUENCA\u2013AZOGUES", RoadRef("Via Cuenca-Azogues", None)),
    ],
)
def test_normalize_road(raw: str, expected: RoadRef) -> None:
    assert normalize_road(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("2025-01-12T05:40:00-05:00", datetime(2025, 1, 12, 5, 40)),
        ("03/02/2025 22:15", datetime(2025, 2, 3, 22, 15)),
        ("2025-02-22 14:05:00", datetime(2025, 2, 22, 14, 5)),
        ({"fecha": "09-03-2025", "hora": "03:50"}, datetime(2025, 3, 9, 3, 50)),
        ("14/06/2026 05:10", datetime(2026, 6, 14, 5, 10)),
        ("01/03/2026 00:40", datetime(2026, 3, 1, 0, 40)),
        # Desfase distinto: se convierte a la hora de Ecuador (defensivo).
        ("2025-01-12T10:40:00+00:00", datetime(2025, 1, 12, 5, 40)),
    ],
)
def test_parse_occurred_at(raw: Any, expected: datetime) -> None:
    result = parse_occurred_at(raw)
    assert result.replace(tzinfo=None) == expected
    assert result.utcoffset() == UTC_MINUS_5
    assert result.isoformat().endswith("-05:00")


@pytest.mark.parametrize(
    "raw",
    [
        "2025-01-12T05:40:00",
        "2025/01/12 05:40",
        "02/30/2025 10:00",
        "",
        None,
        12345,
        {"fecha": "09-03-2025"},
        {"fecha": "2025-03-09", "hora": "03:50"},
    ],
)
def test_parse_occurred_at_rejects_unknown_formats(raw: Any) -> None:
    with pytest.raises(NormalizationError):
        parse_occurred_at(raw)


def test_parse_update_and_report_dates() -> None:
    assert parse_update_date("2025-05-06") == date(2025, 5, 6)
    assert parse_report_date("10/02/2025") == date(2025, 2, 10)
    assert parse_report_date("30/03/2026") == date(2026, 3, 30)
    with pytest.raises(NormalizationError):
        parse_update_date("06/05/2025")
    with pytest.raises(NormalizationError):
        parse_report_date("2025-02-10")


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (18500, 18500.0),
        ("3200", 3200.0),
        ("$6,400.00", 6400.0),
        ("21.000,00 USD", 21000.0),
        ("$4,100.00", 4100.0),
        ("$3,900.00", 3900.0),
        ("$33,800.00", 33800.0),
        ("6.200,00 USD", 6200.0),
        # Un solo tipo de separador (defensivo, sin ejemplos en los datos).
        ("1,234", 1234.0),
        ("1.234.567", 1234567.0),
        ("12,5", 12.5),
        ("12.50", 12.5),
        (99.5, 99.5),
    ],
)
def test_parse_amount(raw: Any, expected: float) -> None:
    assert parse_amount(raw) == expected


@pytest.mark.parametrize(
    "raw", ["", "abc", "$-5", "1,23,4", "1.2345", "12 EUR", None, True, -100, "1,000.000,00"]
)
def test_parse_amount_rejects_invalid(raw: Any) -> None:
    with pytest.raises(NormalizationError):
        parse_amount(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (128, 128.0),
        ("4", 4.0),
        ("12+000", 12.0),
        ("9+000", 9.0),
        ("Km 11", 11.0),
        ("Km 118", 118.0),
        ("km 3", 3.0),
        ("12+500", 12.5),
        ("", None),
        ("  ", None),
        (None, None),
    ],
)
def test_parse_km(raw: Any, expected: float | None) -> None:
    assert parse_km(raw) == expected


@pytest.mark.parametrize("raw", ["Km", "12+00", "doce", "-3", -3, True, "12 km"])
def test_parse_km_rejects_invalid(raw: Any) -> None:
    with pytest.raises(NormalizationError):
        parse_km(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("-1.2497,-78.6237", (-1.2497, -78.6237)),
        ("0.0847,-76.895", (0.0847, -76.895)),
        ({"latitud": -2.174, "longitud": -79.9224}, (-2.174, -79.9224)),
        ({"latitud": 0.9632, "longitud": -79.6499}, (0.9632, -79.6499)),
        (None, (None, None)),
    ],
)
def test_parse_coordinates(raw: Any, expected: tuple[float | None, float | None]) -> None:
    assert parse_coordinates(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "-1.2497",
        "-1.2497,-78.6237,5",
        "nan,inf",
        "91,0",
        "0,181",
        {"latitud": -2.174},
        {"latitud": "x", "longitud": -79.9},
        {"latitud": True, "longitud": -79.9},
        "",
        42,
    ],
)
def test_parse_coordinates_rejects_invalid(raw: Any) -> None:
    with pytest.raises(NormalizationError):
        parse_coordinates(raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("0,0", 0.0),
        ("0.0", 0.0),
        (0.4, 0.4),
        (0.0, 0.0),
        ("1,6", 1.6),
        ("1.3", 1.3),
        ("0,9", 0.9),
        ("", None),
        ("N/D", None),
        (None, None),
    ],
)
def test_parse_alcohol(raw: Any, expected: float | None) -> None:
    assert parse_alcohol(raw) == expected


@pytest.mark.parametrize("raw", ["-0,1", -0.1, "positivo", "1,2,3", True])
def test_parse_alcohol_rejects_invalid(raw: Any) -> None:
    with pytest.raises(NormalizationError):
        parse_alcohol(raw)


@pytest.mark.parametrize(
    ("raw", "expected"), [(29, 29), ("39", 39), ("10", 10), (2019, 2019), (" 2018 ", 2018)]
)
def test_parse_int(raw: Any, expected: int) -> None:
    assert parse_int(raw) == expected


@pytest.mark.parametrize("raw", ["39.5", 39.5, "", None, "-4", -4, True, "treinta"])
def test_parse_int_rejects_invalid(raw: Any) -> None:
    with pytest.raises(NormalizationError):
        parse_int(raw)


@pytest.mark.parametrize(
    ("vehicle", "expected"),
    [
        ({"marca_modelo": "HINO AK"}, ("HINO", "AK")),
        ({"marca_modelo": "HONDA CG 150"}, ("HONDA", "CG 150")),
        ({"marca_modelo": "CHEVROLET D-MAX"}, ("CHEVROLET", "D-MAX")),
        ({"marca_modelo": "  KIA   RIO "}, ("KIA", "RIO")),
        ({"marca": "Chevrolet", "modelo": "Aveo"}, ("CHEVROLET", "AVEO")),
        ({"marca": "Mercedes-Benz", "modelo": "OF"}, ("MERCEDES-BENZ", "OF")),
        ({"marca": "Mazda", "modelo": "BT-50"}, ("MAZDA", "BT-50")),
        ({"marca": "Honda", "modelo": "CB  125"}, ("HONDA", "CB 125")),
    ],
)
def test_split_brand_model(vehicle: dict[str, str], expected: tuple[str, str]) -> None:
    assert split_brand_model(**vehicle) == expected


@pytest.mark.parametrize(
    "vehicle",
    [
        {},
        {"marca_modelo": "HINO"},
        {"marca": "Kia"},
        {"marca_modelo": "KIA RIO", "marca": "Kia", "modelo": "Rio"},
        {"marca": "", "modelo": "Rio"},
    ],
)
def test_split_brand_model_rejects_invalid(vehicle: dict[str, str]) -> None:
    with pytest.raises(NormalizationError):
        split_brand_model(**vehicle)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("  Un bus  pierde\n el control.  ", "Un bus pierde el control."),
        ("Texto\tcon\r\nsaltos", "Texto con saltos"),
        ("Cami\u00f3n en la v\u00eda", "Cami\u00f3n en la v\u00eda"),
    ],
)
def test_clean_text(raw: str, expected: str) -> None:
    assert clean_text(raw) == expected


def test_to_canonical() -> None:
    assert to_canonical(CAUSES, "VELOCIDAD EXCESIVA") is Cause.EXCESO_DE_VELOCIDAD
    assert to_canonical(PERSON_ROLES, "peat\u00f3n") is PersonRole.PEATON
    assert to_canonical(PERSON_CONDITIONS, "HERIDO GRAVE") is PersonCondition.HERIDO_GRAVE
    assert to_canonical(SEXES, "Mujer") is Sex.F
    assert to_canonical(PROVINCES, "  los R\u00cdOS ") is Province.LOS_RIOS


@pytest.mark.parametrize("raw", ["GRANIZO DE CAUSA", None, 3, ""])
def test_to_canonical_rejects_unknown(raw: Any) -> None:
    with pytest.raises(NormalizationError, match="Cause"):
        to_canonical(CAUSES, raw)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Cintur\u00f3n de seguridad", Protection.CINTURON),
        ("SI - CASCO", Protection.CASCO),
        ("NO", Protection.NINGUNA),
        ("N/A", Protection.NO_APLICA),
        ("SIN DATO", Protection.NO_REGISTRADO),
        ("", Protection.NO_REGISTRADO),
        (None, Protection.NO_REGISTRADO),
    ],
)
def test_normalize_protection(raw: str | None, expected: Protection) -> None:
    assert normalize_protection(raw) is expected


def test_error_message_names_reason_and_value() -> None:
    with pytest.raises(NormalizationError) as info:
        parse_km("doce")
    assert info.value.value == "doce"
    assert "doce" in str(info.value)
    assert info.value.reason


# Recorrido completo del JSON real: ninguna regla falla y los resultados coinciden con las
# cifras de reglas_normalizacion.md.


@pytest.fixture(scope="module")
def raw_data() -> Any:
    return json.loads(REAL_FILE.read_text(encoding="utf-8"))


def test_real_dates(raw_data: Any) -> None:
    records = raw_data["registros"]
    parsed = [parse_occurred_at(r["fecha_hora"]) for r in records]
    assert all(p.utcoffset() == UTC_MINUS_5 for p in parsed)
    # El anio del id coincide con el de la fecha (verificado en la tarea 1.2).
    assert all(p.year == int(r["id_parte"][4:8]) for p, r in zip(parsed, records, strict=True))
    updates = [parse_update_date(r["fecha_actualizacion"]) for r in records]
    # Ninguna fecha posterior a su actualizacion (verificacion V2 del catalogo).
    assert all(p.date() <= u for p, u in zip(parsed, updates, strict=True))
    assert sorted(parse_report_date(i["fecha"]) for i in raw_data["informes"])[0] == date(
        2025, 2, 10
    )


def test_real_amounts(raw_data: Any) -> None:
    amounts = [parse_amount(r["danos_materiales"]) for r in raw_data["registros"]]
    assert (min(amounts), max(amounts)) == (1200.0, 41000.0)


def test_real_km_and_coordinates(raw_data: Any) -> None:
    locations = [r["ubicacion"] for r in raw_data["registros"]]
    km = [parse_km(loc.get("km")) for loc in locations]
    present = [k for k in km if k is not None]
    assert (len(present), km.count(None)) == (26, 5)
    assert (min(present), max(present)) == (3.0, 205.0)
    coords = [parse_coordinates(loc.get("coordenadas")) for loc in locations]
    assert sum(lat is not None for lat, _ in coords) == 29


def test_real_people(raw_data: Any) -> None:
    people = [p for r in raw_data["registros"] for p in r["personas"]]
    alcohol = [parse_alcohol(p["alcohol_gl"]) for p in people]
    present = [a for a in alcohol if a is not None]
    assert (len(present), alcohol.count(None), max(present)) == (47, 34, 1.6)
    ages = [parse_int(p["edad"]) for p in people]
    assert (min(ages), max(ages)) == (7, 71)
    assert {normalize_protection(p["proteccion"]) for p in people} == set(Protection)
    assert {to_canonical(SEXES, p["sexo"]) for p in people} == set(Sex)


def test_real_vehicles(raw_data: Any) -> None:
    vehicles = [v for r in raw_data["registros"] for v in r["vehiculos"]]
    pairs = [
        split_brand_model(v.get("marca_modelo"), v.get("marca"), v.get("modelo")) for v in vehicles
    ]
    assert len({brand for brand, _ in pairs}) == 13
    years = [parse_int(v["anio"]) for v in vehicles]
    assert (min(years), max(years)) == (2012, 2023)


def test_real_places_and_roads(raw_data: Any) -> None:
    locations = [r["ubicacion"] for r in raw_data["registros"]]
    assert len({display_name(loc["canton"]) for loc in locations}) == 22
    assert len({display_name(loc["parroquia"]) for loc in locations}) == 29
    roads = [normalize_road(loc["via"]) for loc in locations]
    assert len(set(roads)) == 20
    assert sum(road.code == "E35" for road in roads) == 6
    assert {road.code for road in roads} == {"E35", "E45", "E15", None}
    assert len({to_canonical(PROVINCES, loc["provincia"]) for loc in locations}) == 17


def test_real_texts(raw_data: Any) -> None:
    narratives = [r["narrativa"] for r in raw_data["registros"]]
    cleaned = [clean_text(n) for n in narratives]
    assert sum(c != n for c, n in zip(cleaned, narratives, strict=True)) == 10
    assert all(c == c.strip() and "  " not in c and "\n" not in c for c in cleaned)
