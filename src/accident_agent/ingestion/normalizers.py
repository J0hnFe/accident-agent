"""Funciones puras de normalizacion de los valores del JSON original (tarea 1.7).

Especificacion: `docs/datos/reglas_normalizacion.md` (reglas N01 a N12). Cada funcion recibe un
valor original y devuelve su valor canonico o lanza `NormalizationError`. Solo se aceptan los
formatos listados en las reglas: un valor desconocido detiene la carga en lugar de entrar como
dato silencioso. El id del registro y la ruta del campo los agrega el pipeline (tarea 2.2).
"""

import math
import re
import unicodedata
from collections.abc import Mapping
from datetime import date, datetime
from enum import StrEnum
from typing import Final, NamedTuple
from zoneinfo import ZoneInfo

from accident_agent.domain.catalogs import PROTECTIONS, ROAD_ALIASES, Protection

# Zona declarada en la metadata del JSON; no depende de la configuracion de la aplicacion.
DATA_TIMEZONE: Final = ZoneInfo("America/Guayaquil")

# Raya (U+2013) y raya larga (U+2014), presentes en nombres de via.
_DASHES: Final = str.maketrans({0x2013: "-", 0x2014: "-"})
_LOWERCASE_WORDS: Final = frozenset({"de", "del", "la", "las", "los", "el", "a", "y"})
_WORD_START: Final = re.compile(r"(^|[(\-])([a-z])")
_ROAD_CODE: Final = re.compile(r"\bE\d{2,3}\b")

_DATETIME_WITH_OFFSET: Final = "%Y-%m-%dT%H:%M:%S%z"
_DATETIME_LOCAL: Final = ("%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M:%S")

_DIGITS: Final = re.compile(r"\d+")
_DECIMAL: Final = re.compile(r"\d+(?:\.\d+)?")
_SIGNED_DECIMAL: Final = re.compile(r"-?\d+(?:\.\d+)?")
_KM_PREFIXED: Final = re.compile(r"km\s*(\d+(?:[.,]\d+)?)", re.IGNORECASE)
_KM_ABSCISSA: Final = re.compile(r"(\d+)\+(\d{3})")
_ALCOHOL_MISSING: Final = frozenset({"", "n/d"})


class NormalizationError(ValueError):
    """Valor que ninguna regla reconoce.

    Los normalizadores nunca reciben nombres, cedulas ni placas, por eso el valor puede ir en el
    mensaje.
    """

    def __init__(self, reason: str, value: object) -> None:
        self.reason = reason
        self.value = value
        super().__init__(f"{reason}: {value!r}")


class RoadRef(NamedTuple):
    name: str
    code: str | None


def _is_number(value: object) -> bool:
    # bool hereda de int: True no debe leerse como 1.
    return isinstance(value, int | float) and not isinstance(value, bool)


def _require_str(value: object, reason: str) -> str:
    if not isinstance(value, str):
        raise NormalizationError(reason, value)
    return value


def normalize_key(value: str) -> str:
    """N01. Clave de comparacion: rayas a guion, sin tildes, minusculas y espacios colapsados.

    La enie tambien se reduce a "n" para que coincida con la convencion ASCII de los catalogos.
    """
    decomposed = unicodedata.normalize("NFKD", value.translate(_DASHES))
    without_marks = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(without_marks.casefold().split())


def display_name(value: object) -> str:
    """N02. Nombre visible de canton, parroquia y via, derivado de la clave."""
    key = normalize_key(_require_str(value, "se esperaba texto"))
    if not key:
        raise NormalizationError("nombre vacio", value)
    words = key.split(" ")
    return " ".join(
        word
        if index > 0 and word in _LOWERCASE_WORDS
        else _WORD_START.sub(lambda m: m.group(1) + m.group(2).upper(), word)
        for index, word in enumerate(words)
    )


def normalize_road(value: object) -> RoadRef:
    """N03. Nombre canonico de la via y codigo de red vial tomado del propio texto."""
    key = normalize_key(_require_str(value, "se esperaba texto"))
    key = ROAD_ALIASES.get(key, key)
    match = _ROAD_CODE.search(key.upper())
    return RoadRef(display_name(key), match.group() if match else None)


def parse_occurred_at(value: object, tz: ZoneInfo = DATA_TIMEZONE) -> datetime:
    """N04. Fecha y hora del siniestro en 4 formatos explicitos, dia primero."""
    if isinstance(value, dict):
        if set(value) != {"fecha", "hora"}:
            raise NormalizationError("objeto de fecha sin las claves fecha y hora", value)
        text = f"{value['fecha']} {value['hora']}"
        try:
            return datetime.strptime(text, "%d-%m-%Y %H:%M").replace(tzinfo=tz)
        except ValueError:
            raise NormalizationError("fecha fuera de formato", value) from None
    text = _require_str(value, "fecha fuera de formato")
    try:
        return datetime.strptime(text, _DATETIME_WITH_OFFSET).astimezone(tz)
    except ValueError:
        pass
    for fmt in _DATETIME_LOCAL:
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=tz)
        except ValueError:
            continue
    raise NormalizationError("fecha fuera de formato", value)


def _parse_date(value: object, fmt: str) -> date:
    text = _require_str(value, "fecha fuera de formato")
    try:
        return datetime.strptime(text, fmt).date()
    except ValueError:
        raise NormalizationError("fecha fuera de formato", value) from None


def parse_update_date(value: object) -> date:
    """N05. `fecha_actualizacion` de los registros (`aaaa-mm-dd`)."""
    return _parse_date(value, "%Y-%m-%d")


def parse_report_date(value: object) -> date:
    """N05. `fecha` de los informes (`dd/mm/aaaa`)."""
    return _parse_date(value, "%d/%m/%Y")


def parse_amount(value: object) -> float:
    """N06. Monto en USD; detecta el separador decimal de cada escritura."""
    if _is_number(value):
        amount = float(value)  # type: ignore[arg-type]
        if amount < 0 or not math.isfinite(amount):
            raise NormalizationError("monto negativo o no finito", value)
        return amount
    text = _require_str(value, "monto no reconocido")
    text = text.replace("$", "").replace("USD", "").replace(" ", "")
    if _DIGITS.fullmatch(text):
        return float(text)
    if "," in text and "." in text:
        decimal_sep = "," if text.rfind(",") > text.rfind(".") else "."
        thousands_sep = "." if decimal_sep == "," else ","
        thousands, decimal = re.escape(thousands_sep), re.escape(decimal_sep)
        if re.fullmatch(rf"\d{{1,3}}(?:{thousands}\d{{3}})+{decimal}\d{{1,2}}", text):
            return float(text.replace(thousands_sep, "").replace(decimal_sep, "."))
    else:
        for sep in (",", "."):
            escaped = re.escape(sep)
            if re.fullmatch(rf"\d+{escaped}\d{{1,2}}", text):
                return float(text.replace(sep, "."))
            if re.fullmatch(rf"\d{{1,3}}(?:{escaped}\d{{3}})+", text):
                return float(text.replace(sep, ""))
    raise NormalizationError("monto no reconocido", value)


def parse_km(value: object) -> float | None:
    """N07. Kilometro: numero, texto, prefijo `Km` o abscisa `K+MMM`; vacio es null."""
    if value is None:
        return None
    if _is_number(value):
        km = float(value)  # type: ignore[arg-type]
        if km < 0 or not math.isfinite(km):
            raise NormalizationError("kilometro negativo o no finito", value)
        return km
    text = _require_str(value, "kilometro no reconocido").strip()
    if not text:
        return None
    if _DIGITS.fullmatch(text):
        return float(text)
    if match := _KM_PREFIXED.fullmatch(text):
        return float(match.group(1).replace(",", "."))
    if match := _KM_ABSCISSA.fullmatch(text):
        return int(match.group(1)) + int(match.group(2)) / 1000
    raise NormalizationError("kilometro no reconocido", value)


def _coordinate(value: object, limit: float, original: object) -> float:
    if _is_number(value):
        number = float(value)  # type: ignore[arg-type]
    elif isinstance(value, str) and _SIGNED_DECIMAL.fullmatch(value.strip()):
        number = float(value)
    else:
        raise NormalizationError("coordenada no reconocida", original)
    if not math.isfinite(number) or abs(number) > limit:
        raise NormalizationError("coordenada fuera de rango", original)
    return number


def parse_coordinates(value: object) -> tuple[float | None, float | None]:
    """N08. Latitud y longitud desde texto `"lat,lon"` u objeto; null da ambas null."""
    if value is None:
        return None, None
    if isinstance(value, dict):
        if set(value) != {"latitud", "longitud"}:
            raise NormalizationError("objeto sin latitud y longitud", value)
        lat, lon = value["latitud"], value["longitud"]
    elif isinstance(value, str):
        parts = value.split(",")
        if len(parts) != 2:
            raise NormalizationError("se esperaban dos numeros separados por coma", value)
        lat, lon = parts
    else:
        raise NormalizationError("coordenadas no reconocidas", value)
    return _coordinate(lat, 90, value), _coordinate(lon, 180, value)


def parse_alcohol(value: object) -> float | None:
    """N09. Alcoholemia en g/L; vacio, `N/D` y null son null (prueba no realizada)."""
    if value is None:
        return None
    if _is_number(value):
        number = float(value)  # type: ignore[arg-type]
    else:
        text = _require_str(value, "alcoholemia no reconocida").strip()
        if text.casefold() in _ALCOHOL_MISSING:
            return None
        text = text.replace(",", ".")
        if not _DECIMAL.fullmatch(text):
            raise NormalizationError("alcoholemia no reconocida", value)
        number = float(text)
    if number < 0 or not math.isfinite(number):
        raise NormalizationError("alcoholemia negativa o no finita", value)
    return number


def parse_int(value: object) -> int:
    """N10. Entero no negativo, como numero o como texto de digitos."""
    if isinstance(value, int) and not isinstance(value, bool):
        if value < 0:
            raise NormalizationError("entero negativo", value)
        return value
    if isinstance(value, str) and _DIGITS.fullmatch(value.strip()):
        return int(value.strip())
    raise NormalizationError("entero no reconocido", value)


def split_brand_model(
    marca_modelo: object = None, marca: object = None, modelo: object = None
) -> tuple[str, str]:
    """N11. Marca y modelo en mayusculas, desde `marca_modelo` o desde el par separado."""
    if marca_modelo is not None:
        if marca is not None or modelo is not None:
            raise NormalizationError("vehiculo con marca_modelo y con marca o modelo", marca_modelo)
        brand, _, model = clean_text(marca_modelo).partition(" ")
        if not brand or not model:
            raise NormalizationError("marca_modelo sin marca o sin modelo", marca_modelo)
        return brand.upper(), model.upper()
    if marca is None or modelo is None:
        raise NormalizationError("vehiculo sin marca o sin modelo", (marca, modelo))
    brand, model = clean_text(marca), clean_text(modelo)
    if not brand or not model:
        raise NormalizationError("vehiculo con marca o modelo vacio", (marca, modelo))
    return brand.upper(), model.upper()


def clean_text(value: object) -> str:
    """N12. Texto libre recortado y con espacios colapsados; el resto no cambia."""
    return " ".join(_require_str(value, "se esperaba texto").split())


def to_canonical[E: StrEnum](lookup: Mapping[str, E], value: object) -> E:
    """Valor canonico de un catalogo cerrado (seccion 3 de las reglas)."""
    catalog = type(next(iter(lookup.values()))).__name__
    if isinstance(value, str) and (member := lookup.get(normalize_key(value))) is not None:
        return member
    raise NormalizationError(f"valor fuera del catalogo {catalog}", value)


def normalize_protection(value: object) -> Protection:
    """Proteccion: null tambien es `no_registrado`, a diferencia de los demas catalogos."""
    if value is None:
        return Protection.NO_REGISTRADO
    return to_canonical(PROTECTIONS, value)
