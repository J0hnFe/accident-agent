"""Perfilado reproducible del JSON original (tarea 1.1).

Recorre `registros` e `informes`, construye un `FieldProfile` por ruta y detecta anomalias.
Nunca incluye en la salida valores de nombre, cedula o placa, ni el contenido de los textos
libres: de esos campos solo se reportan conteos e ids de registro.

Uso: uv run python -m accident_agent.ingestion.quality_report [ruta] [--output archivo]
"""

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from collections.abc import Iterable
from enum import StrEnum
from pathlib import Path
from typing import Any, Final

from pydantic import BaseModel, ConfigDict

from accident_agent.ingestion.normalizers import normalize_key

SENSITIVE_KEYS: Final = frozenset({"nombre", "cedula", "placa", "placa_vehiculo"})
FREE_TEXT_KEYS: Final = frozenset({"narrativa", "texto"})
PLACEHOLDERS: Final = frozenset({"", "n/d", "nd", "n/a", "na", "s/d", "sin dato", "-"})
TOP_VALUES: Final = 25
MAX_IDS: Final = 15

CEDULA_PATTERN: Final = re.compile(r"\b\d{10}\b")
SUSPICIOUS_PATTERNS: Final = {
    "ignorar instrucciones": re.compile(r"ignora\w*\s+(tus|las|todas)?\s*(\w+\s+)?instruccion"),
    "mensaje dirigido al asistente": re.compile(r"asistente de ia|modelo de lenguaje"),
    "prompt de sistema": re.compile(r"system prompt|prompt de sistema"),
}

_JSON_TYPES: Final = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
    dict: "object",
    list: "array",
    type(None): "null",
}


class _Absent:
    """Marca una clave que no existe en un objeto, distinta de un valor null."""


ABSENT: Final = _Absent()


class AnomalyCode(StrEnum):
    PARTIAL_PRESENCE = "partial_presence"
    MIXED_TYPES = "mixed_types"
    FORMAT_VARIANTS = "format_variants"
    CASE_VARIANTS = "case_variants"
    MISSING_VALUES = "missing_values"
    WHITESPACE = "whitespace"
    DUPLICATE_ID = "duplicate_id"
    METADATA_MISMATCH = "metadata_mismatch"
    SUMMARY_MISMATCH = "summary_mismatch"
    REPLACEMENT_LINK = "replacement_link"
    RESTRICTED_CLASSIFICATION = "restricted_classification"
    PII_IN_TEXT = "pii_in_text"
    SUSPICIOUS_INSTRUCTION = "suspicious_instruction"


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ValueCount(_Frozen):
    value: str
    count: int


class FieldProfile(_Frozen):
    path: str
    present: int
    absent: int
    nulls: int
    empty_strings: int
    types: dict[str, int]
    distinct: int
    sensitive: bool
    free_text: bool
    top_values: list[ValueCount]
    shapes: list[ValueCount]
    min_length: int | None = None
    max_length: int | None = None


class Anomaly(_Frozen):
    code: AnomalyCode
    path: str
    detail: str
    count: int
    examples: list[str] = []
    record_ids: list[str] = []


class DatasetProfile(_Frozen):
    source_file: str
    sha256: str
    metadata: dict[str, Any]
    record_count: int
    report_count: int
    fields: list[FieldProfile]
    anomalies: list[Anomaly]


Observation = tuple[str, Any]  # (id del registro, valor o ABSENT)


def shape(value: str) -> str:
    """Forma de un texto: cada racha de digitos pasa a "9" y cada racha de letras a "a".

    Un "-" al inicio o tras espacio, coma o parentesis es signo y no separador, para que
    "0.08,-76.8" y "-1.24,-78.6" tengan la misma forma.
    """
    return re.sub(r"[^\W\d_]+", "a", re.sub(r"(?:(?<![^\s,(])-)?\d+", "9", value))


def _numeric_like(strings: Iterable[str]) -> list[str]:
    """Cadenas de un campo donde todo valor no de relleno lleva digitos; si no, lista vacia.

    Limita las formas a fechas, montos y medidas, y evita ruido en textos como nombres de via.
    """
    values = [v for v in strings if normalize_key(v) not in PLACEHOLDERS]
    if values and all(any(ch.isdigit() for ch in v) for v in values):
        return values
    return []


def profile_file(path: Path) -> DatasetProfile:
    raw = path.read_bytes()
    data = json.loads(raw)
    return profile_data(data, source_file=path.name, sha256=hashlib.sha256(raw).hexdigest())


def profile_data(data: dict[str, Any], *, source_file: str, sha256: str) -> DatasetProfile:
    records: list[dict[str, Any]] = data.get("registros", [])
    reports: list[dict[str, Any]] = data.get("informes", [])

    observations: dict[str, list[Observation]] = {}
    _walk("registros[]", [(_record_id(r, i), r) for i, r in enumerate(records)], observations)
    _walk(
        "informes[]", [(str(r.get("id", f"#{i}")), r) for i, r in enumerate(reports)], observations
    )

    fields = [_profile_field(path, obs) for path, obs in observations.items()]
    anomalies = [a for path, obs in observations.items() for a in _field_anomalies(path, obs)]
    anomalies += _record_anomalies(data, records, reports, observations)

    return DatasetProfile(
        source_file=source_file,
        sha256=sha256,
        metadata=data.get("metadata", {}),
        record_count=len(records),
        report_count=len(reports),
        fields=fields,
        anomalies=anomalies,
    )


def _record_id(record: dict[str, Any], index: int) -> str:
    return str(record.get("id_parte", f"#{index}"))


def _walk(
    path: str, items: list[tuple[str, dict[str, Any]]], out: dict[str, list[Observation]]
) -> None:
    keys = dict.fromkeys(key for _, item in items for key in item)
    for key in keys:
        child = f"{path}.{key}"
        values = [(rid, item.get(key, ABSENT)) for rid, item in items]
        out[child] = values
        nested = [(rid, v) for rid, v in values if isinstance(v, dict)]
        if nested:
            _walk(child, nested, out)
        elements = [(rid, e) for rid, v in values if isinstance(v, list) for e in v]
        objects = [(rid, e) for rid, e in elements if isinstance(e, dict)]
        if objects:
            _walk(f"{child}[]", objects, out)


def _leaf_key(path: str) -> str:
    return path.rsplit(".", 1)[-1].removesuffix("[]")


def _is_sensitive(path: str) -> bool:
    return _leaf_key(path) in SENSITIVE_KEYS


def _is_free_text(path: str) -> bool:
    return _leaf_key(path) in FREE_TEXT_KEYS


def _present(observations: list[Observation]) -> list[Observation]:
    return [(rid, v) for rid, v in observations if v is not ABSENT]


def _scalars(observations: list[Observation]) -> list[Observation]:
    return [(rid, v) for rid, v in _present(observations) if not isinstance(v, dict | list)]


def _strings(observations: list[Observation]) -> list[tuple[str, str]]:
    return [(rid, v) for rid, v in _present(observations) if isinstance(v, str)]


def _display(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)


def _counted(values: Iterable[str], limit: int | None = None) -> list[ValueCount]:
    ranked = sorted(Counter(values).items(), key=lambda item: (-item[1], item[0]))
    return [ValueCount(value=v, count=c) for v, c in ranked[:limit]]


def _ids(observations: Iterable[Observation]) -> list[str]:
    return sorted({rid for rid, _ in observations})[:MAX_IDS]


def _profile_field(path: str, observations: list[Observation]) -> FieldProfile:
    present = _present(observations)
    scalars = _scalars(observations)
    strings = _strings(observations)
    hidden = _is_sensitive(path) or _is_free_text(path)
    numeric = _numeric_like(v for _, v in strings)
    lengths = [len(v) for _, v in strings] if _is_free_text(path) else []

    return FieldProfile(
        path=path,
        present=len(present),
        absent=len(observations) - len(present),
        nulls=sum(1 for _, v in present if v is None),
        empty_strings=sum(1 for _, v in strings if v == ""),
        types=dict(Counter(_JSON_TYPES[type(v)] for _, v in present)),
        distinct=len({_display(v) for _, v in scalars}),
        sensitive=_is_sensitive(path),
        free_text=_is_free_text(path),
        top_values=[] if hidden else _counted((_display(v) for _, v in scalars), TOP_VALUES),
        shapes=[] if hidden else _counted(shape(v) for v in numeric),
        min_length=min(lengths, default=None),
        max_length=max(lengths, default=None),
    )


def _field_anomalies(path: str, observations: list[Observation]) -> list[Anomaly]:
    found: list[Anomaly] = []
    present = _present(observations)
    sensitive = _is_sensitive(path)
    hidden = sensitive or _is_free_text(path)

    if len(present) < len(observations):
        absent = [(rid, v) for rid, v in observations if v is ABSENT]
        minority = present if len(present) <= len(absent) else absent
        found.append(
            Anomaly(
                code=AnomalyCode.PARTIAL_PRESENCE,
                path=path,
                detail=f"presente en {len(present)} de {len(observations)} objetos",
                count=len(absent),
                record_ids=_ids(minority),
            )
        )

    types = Counter(_JSON_TYPES[type(v)] for _, v in present if v is not None)
    if len(types) > 1:
        examples: dict[str, str] = {}
        for _, v in present:
            if v is not None and not isinstance(v, dict | list):
                examples.setdefault(_JSON_TYPES[type(v)], _display(v))
        found.append(
            Anomaly(
                code=AnomalyCode.MIXED_TYPES,
                path=path,
                detail=", ".join(f"{t}: {c}" for t, c in sorted(types.items())),
                count=sum(types.values()),
                examples=[] if hidden else [examples[t] for t in sorted(examples)],
            )
        )

    strings = _strings(observations)
    if not hidden:
        found += _string_anomalies(path, strings)

    missing = [
        (rid, v)
        for rid, v in present
        if v is None or (isinstance(v, str) and normalize_key(v) in PLACEHOLDERS)
    ]
    if missing:
        found.append(
            Anomaly(
                code=AnomalyCode.MISSING_VALUES,
                path=path,
                detail="valores null, vacios o de relleno",
                count=len(missing),
                examples=sorted({_display(v) for _, v in missing}),
                record_ids=_ids(missing),
            )
        )

    padded = [(rid, v) for rid, v in strings if v != " ".join(v.split())]
    if padded:
        found.append(
            Anomaly(
                code=AnomalyCode.WHITESPACE,
                path=path,
                detail="espacios al inicio o al final, dobles o saltos de linea",
                count=len(padded),
                examples=[] if hidden else sorted({repr(v) for _, v in padded})[:5],
                record_ids=_ids(padded),
            )
        )
    return found


def _string_anomalies(path: str, strings: list[tuple[str, str]]) -> list[Anomaly]:
    found: list[Anomaly] = []

    by_shape: dict[str, str] = {}
    for v in _numeric_like(v for _, v in strings):
        by_shape.setdefault(shape(v), _display(v))
    if len(by_shape) > 1:
        found.append(
            Anomaly(
                code=AnomalyCode.FORMAT_VARIANTS,
                path=path,
                detail=f"{len(by_shape)} formas: " + ", ".join(sorted(by_shape)),
                count=len(by_shape),
                examples=[by_shape[s] for s in sorted(by_shape)],
            )
        )

    groups: dict[str, set[str]] = defaultdict(set)
    for _, v in strings:
        groups[normalize_key(v)].add(v)
    variants = [sorted(g) for _, g in sorted(groups.items()) if len(g) > 1]
    if variants:
        found.append(
            Anomaly(
                code=AnomalyCode.CASE_VARIANTS,
                path=path,
                detail=f"{len(variants)} valores escritos de varias formas",
                count=sum(len(g) for g in variants),
                examples=[" | ".join(g) for g in variants],
            )
        )
    return found


def _record_anomalies(
    data: dict[str, Any],
    records: list[dict[str, Any]],
    reports: list[dict[str, Any]],
    observations: dict[str, list[Observation]],
) -> list[Anomaly]:
    found: list[Anomaly] = []
    record_ids = [_record_id(r, i) for i, r in enumerate(records)]
    report_ids = [str(r.get("id")) for r in reports]

    duplicates = sorted(rid for rid, n in Counter(record_ids).items() if n > 1)
    if duplicates:
        versions = {
            rid: sorted(str(r.get("version")) for r in records if r.get("id_parte") == rid)
            for rid in duplicates
        }
        found.append(
            Anomaly(
                code=AnomalyCode.DUPLICATE_ID,
                path="registros[].id_parte",
                detail="; ".join(f"{rid}: versiones {', '.join(v)}" for rid, v in versions.items()),
                count=len(duplicates),
                record_ids=duplicates,
            )
        )

    declared = data.get("metadata", {}).get("total_registros")
    if declared is not None and declared != len(records):
        found.append(
            Anomaly(
                code=AnomalyCode.METADATA_MISMATCH,
                path="metadata.total_registros",
                detail=f"declara {declared} y hay {len(records)}",
                count=1,
            )
        )

    found += _summary_mismatches(records)
    found += _replacement_links("registros[]", records, "id_parte", set(record_ids))
    found += _replacement_links("informes[]", reports, "id", set(report_ids))

    restricted = [
        (str(r.get("id")), r.get("clasificacion"))
        for r in reports
        if r.get("clasificacion") not in (None, "PUBLICO")
    ]
    if restricted:
        found.append(
            Anomaly(
                code=AnomalyCode.RESTRICTED_CLASSIFICATION,
                path="informes[].clasificacion",
                detail="informes con clasificacion distinta de PUBLICO",
                count=len(restricted),
                examples=sorted({_display(c) for _, c in restricted}),
                record_ids=_ids(restricted),
            )
        )

    found += _pii_in_text(records, observations)
    found += _suspicious_instructions(observations)
    return found


def _summary_mismatches(records: list[dict[str, Any]]) -> list[Anomaly]:
    mismatches: list[str] = []
    ids: list[Observation] = []
    for index, record in enumerate(records):
        summary = record.get("resumen")
        if not isinstance(summary, dict):
            continue
        conditions = [
            normalize_key(str(p.get("condicion", ""))) for p in record.get("personas", [])
        ]
        derived = {
            "fallecidos": sum("fallec" in c for c in conditions),
            "heridos": sum("herid" in c for c in conditions),
            "ilesos": sum("iles" in c for c in conditions),
        }
        declared = {key: summary.get(key) for key in derived}
        if declared != derived:
            rid = _record_id(record, index)
            version = record.get("version")
            mismatches.append(f"{rid} v{version}: resumen {declared} vs personas {derived}")
            ids.append((rid, None))
    if not mismatches:
        return []
    return [
        Anomaly(
            code=AnomalyCode.SUMMARY_MISMATCH,
            path="registros[].resumen",
            detail="conteos del resumen distintos de los derivados de personas",
            count=len(mismatches),
            examples=mismatches,
            record_ids=_ids(ids),
        )
    ]


def _replacement_links(
    prefix: str, items: list[dict[str, Any]], id_key: str, known: set[str]
) -> list[Anomaly]:
    links = [(str(i.get(id_key)), str(i["reemplaza_a"])) for i in items if i.get("reemplaza_a")]
    if not links:
        return []
    parts = [
        f"{src} reemplaza a {dst}" + ("" if dst in known else " (no existe)") for src, dst in links
    ]
    return [
        Anomaly(
            code=AnomalyCode.REPLACEMENT_LINK,
            path=f"{prefix}.reemplaza_a",
            detail="; ".join(parts),
            count=len(links),
            record_ids=sorted({src for src, _ in links}),
        )
    ]


def _pii_in_text(
    records: list[dict[str, Any]], observations: dict[str, list[Observation]]
) -> list[Anomaly]:
    names = {
        normalize_key(str(p["nombre"]))
        for r in records
        for p in r.get("personas", [])
        if p.get("nombre")
    }
    plates = {
        str(v["placa"]).casefold()
        for r in records
        for v in r.get("vehiculos", [])
        if v.get("placa")
    }

    found: list[Anomaly] = []
    for path, obs in observations.items():
        if not _is_free_text(path):
            continue
        hits: list[Observation] = []
        kinds: Counter[str] = Counter()
        for rid, text in _strings(obs):
            key = normalize_key(text)
            matched = {
                "nombre": any(name in key for name in names),
                "cedula": bool(CEDULA_PATTERN.search(text)),
                "placa": any(plate in key for plate in plates),
            }
            if any(matched.values()):
                hits.append((rid, None))
                kinds.update(kind for kind, hit in matched.items() if hit)
        if hits:
            found.append(
                Anomaly(
                    code=AnomalyCode.PII_IN_TEXT,
                    path=path,
                    detail="texto libre con "
                    + ", ".join(f"{k}: {n}" for k, n in sorted(kinds.items())),
                    count=len(hits),
                    record_ids=_ids(hits),
                )
            )
    return found


def _suspicious_instructions(observations: dict[str, list[Observation]]) -> list[Anomaly]:
    found: list[Anomaly] = []
    for path, obs in observations.items():
        if not _is_free_text(path):
            continue
        hits: list[Observation] = []
        labels: set[str] = set()
        for rid, text in _strings(obs):
            key = normalize_key(text)
            matched = {label for label, rx in SUSPICIOUS_PATTERNS.items() if rx.search(key)}
            if matched:
                hits.append((rid, None))
                labels |= matched
        if hits:
            found.append(
                Anomaly(
                    code=AnomalyCode.SUSPICIOUS_INSTRUCTION,
                    path=path,
                    detail="posible prompt injection: " + ", ".join(sorted(labels)),
                    count=len(hits),
                    record_ids=_ids(hits),
                )
            )
    return found


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Perfilado del JSON de siniestros.")
    parser.add_argument("path", nargs="?", type=Path, help="Ruta del JSON (por defecto DATA_FILE)")
    parser.add_argument("--output", type=Path, help="Archivo de salida (por defecto stdout)")
    args = parser.parse_args(argv)

    if args.path is None:
        from accident_agent.config import get_settings

        args.path = get_settings().data_file

    profile = profile_file(args.path)
    # ensure_ascii mantiene el archivo en ASCII; los valores con tildes quedan como \uXXXX.
    output = json.dumps(profile.model_dump(mode="json"), ensure_ascii=True, indent=2) + "\n"
    if args.output:
        args.output.write_text(output, encoding="ascii")
        print(
            f"{args.output}: {len(profile.fields)} campos, {len(profile.anomalies)} anomalias",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
