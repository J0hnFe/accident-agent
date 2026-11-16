"""Pipeline de ingesta: JSON original -> `CleanDataset` (tarea 2.2).

Aplica las reglas por registro R01 a R06 de `docs/datos/reglas_normalizacion.md` sobre los
valores normalizados por `normalizers` (reglas N01 a N12). No escribe en Neo4j: eso lo hace
`neo4j_writer` con el resultado.

Todo error se reporta como `IngestionError` con el id del registro, la ruta del campo y el
motivo. Nunca incluye nombres, cedulas ni placas: los dos primeros no existen en los modelos
crudos y la placa solo se compara, no se muestra.
"""

import hashlib
import re
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Final

from pydantic import ValidationError

from accident_agent.domain import catalogs
from accident_agent.domain.catalogs import (
    AccidentType,
    Classification,
    PersonCondition,
    RecordStatus,
)
from accident_agent.domain.models import (
    Accident,
    CleanDataset,
    DatasetInfo,
    Location,
    Person,
    Report,
    ReportSection,
    Vehicle,
)
from accident_agent.ingestion import normalizers as norm
from accident_agent.ingestion.raw_models import (
    RawDataset,
    RawPerson,
    RawRecord,
    RawReport,
    RawSection,
    RawVehicle,
    to_json_value,
)

# Seccion de INF-2026-02 con las definiciones de los tipos de siniestro (A24).
DEFINITIONS_SECTION_KEY: Final = "tipos de siniestro"
_SENTENCE_END: Final = re.compile(r"(?<=\.)\s+")
_MISSING: Final = object()


class IngestionError(Exception):
    """Error de carga con su contexto: registro, ruta del campo y motivo."""

    def __init__(
        self,
        reason: str,
        *,
        record_id: str | None = None,
        path: str | None = None,
        value: object = _MISSING,
    ) -> None:
        self.reason = reason
        self.record_id = record_id
        self.path = path
        detail = f"{record_id or '-'} {path or '-'}: {reason}"
        if value is not _MISSING:
            detail += f": {value!r}"
        super().__init__(detail)


def verify_integrity(path: Path, sha_file: Path) -> str:
    """SHA-256 del archivo; si existe el archivo de referencia, debe coincidir con el."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if sha_file.exists():
        expected = sha_file.read_text(encoding="ascii").split()[0]
        if digest != expected:
            raise IngestionError(
                f"el SHA-256 de {path.name} no coincide con {sha_file.name}: el original cambio"
            )
    return digest


def parse_raw(content: bytes) -> RawDataset:
    try:
        return RawDataset.model_validate_json(content)
    except ValidationError as exc:
        # hide_input_in_errors: los mensajes no incluyen valores de entrada.
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"])
        raise IngestionError(
            f"estructura no valida ({exc.error_count()} errores): {first['msg']}", path=location
        ) from None


def _field[T](record_id: str, path: str, normalize: Callable[[], T]) -> T:
    try:
        return normalize()
    except norm.NormalizationError as exc:
        raise IngestionError(exc.reason, record_id=record_id, path=path, value=exc.value) from None


def _model[T](record_id: str, build: Callable[[], T]) -> T:
    try:
        return build()
    except ValidationError as exc:
        first = exc.errors()[0]
        location = ".".join(str(part) for part in first["loc"]) or None
        raise IngestionError(
            f"invariante del modelo {exc.title}: {first['msg']}", record_id=record_id, path=location
        ) from None


def _vehicle(record_id: str, index: int, raw: RawVehicle) -> Vehicle:
    path = "registros[].vehiculos[]"
    brand, model = _field(
        record_id,
        f"{path}.marca_modelo",
        lambda: norm.split_brand_model(raw.marca_modelo, raw.marca, raw.modelo),
    )
    return _model(
        record_id,
        lambda: Vehicle(
            vehicle_id=f"{record_id}-V{index}",
            vehicle_type=_field(
                record_id,
                f"{path}.tipo_vehiculo",
                lambda: norm.to_canonical(catalogs.VEHICLE_TYPES, raw.tipo_vehiculo),
            ),
            brand=brand,
            model=model,
            year=_field(record_id, f"{path}.anio", lambda: norm.parse_int(raw.anio)),
            service=_field(
                record_id,
                f"{path}.servicio",
                lambda: norm.to_canonical(catalogs.VEHICLE_SERVICES, raw.servicio),
            ),
        ),
    )


def _person(record_id: str, index: int, raw: RawPerson, plates: dict[str, str]) -> Person:
    path = "registros[].personas[]"
    vehicle_id = None
    if raw.placa_vehiculo is not None:
        vehicle_id = plates.get(raw.placa_vehiculo)
        if vehicle_id is None:
            # La placa no se muestra: es un dato personal (politica P4).
            raise IngestionError(
                f"la persona {index} apunta a una placa que no esta en el registro",
                record_id=record_id,
                path=f"{path}.placa_vehiculo",
            )
    return _model(
        record_id,
        lambda: Person(
            person_id=f"{record_id}-P{index}",
            role=_field(
                record_id, f"{path}.rol", lambda: norm.to_canonical(catalogs.PERSON_ROLES, raw.rol)
            ),
            age=_field(record_id, f"{path}.edad", lambda: norm.parse_int(raw.edad)),
            sex=_field(
                record_id, f"{path}.sexo", lambda: norm.to_canonical(catalogs.SEXES, raw.sexo)
            ),
            condition=_field(
                record_id,
                f"{path}.condicion",
                lambda: norm.to_canonical(catalogs.PERSON_CONDITIONS, raw.condicion),
            ),
            alcohol_gl=_field(
                record_id, f"{path}.alcohol_gl", lambda: norm.parse_alcohol(raw.alcohol_gl)
            ),
            protection=_field(
                record_id, f"{path}.proteccion", lambda: norm.normalize_protection(raw.proteccion)
            ),
            days_until_death=raw.dias_hasta_deceso,
            vehicle_id=vehicle_id,
        ),
    )


def _location(record_id: str, raw: RawRecord) -> Location:
    path = "registros[].ubicacion"
    loc = raw.ubicacion
    road = _field(record_id, f"{path}.via", lambda: norm.normalize_road(loc.via))
    latitude, longitude = _field(
        record_id,
        f"{path}.coordenadas",
        lambda: norm.parse_coordinates(to_json_value(loc.coordenadas)),
    )
    return _model(
        record_id,
        lambda: Location(
            province=_field(
                record_id,
                f"{path}.provincia",
                lambda: norm.to_canonical(catalogs.PROVINCES, loc.provincia),
            ),
            canton=_field(record_id, f"{path}.canton", lambda: norm.display_name(loc.canton)),
            parish=_field(record_id, f"{path}.parroquia", lambda: norm.display_name(loc.parroquia)),
            road=road.name,
            road_code=road.code,
            km=_field(record_id, f"{path}.km", lambda: norm.parse_km(loc.km)),
            latitude=latitude,
            longitude=longitude,
        ),
    )


def _accident(raw: RawRecord, versions_count: int, replaced_by: str | None) -> Accident:
    rid = raw.id_parte
    vehicles = [_vehicle(rid, i, v) for i, v in enumerate(raw.vehiculos, start=1)]
    plates = {v.placa: f"{rid}-V{i}" for i, v in enumerate(raw.vehiculos, start=1)}
    people = [_person(rid, i, p, plates) for i, p in enumerate(raw.personas, start=1)]

    # R03: conteos derivados de las personas; el resumen declarado solo marca la diferencia.
    def count(*conditions: PersonCondition) -> int:
        return sum(p.condition in conditions for p in people)

    derived = (
        count(PersonCondition.FALLECIDO),
        count(PersonCondition.HERIDO_GRAVE, PersonCondition.HERIDO_LEVE),
        count(PersonCondition.ILESO),
    )
    declared = (raw.resumen.fallecidos, raw.resumen.heridos, raw.resumen.ilesos)

    return _model(
        rid,
        lambda: Accident(
            accident_id=rid,
            version=raw.version,
            versions_count=versions_count,
            status=_field(
                rid,
                "registros[].estado",
                lambda: norm.to_canonical(catalogs.RECORD_STATUSES, raw.estado),
            ),
            updated_at=_field(
                rid,
                "registros[].fecha_actualizacion",
                lambda: norm.parse_update_date(raw.fecha_actualizacion),
            ),
            occurred_at=_field(
                rid,
                "registros[].fecha_hora",
                lambda: norm.parse_occurred_at(to_json_value(raw.fecha_hora)),
            ),
            accident_type=_field(
                rid,
                "registros[].tipo_siniestro",
                lambda: norm.to_canonical(catalogs.ACCIDENT_TYPES, raw.tipo_siniestro),
            ),
            cause=_field(
                rid,
                "registros[].causa_probable",
                lambda: norm.to_canonical(catalogs.CAUSES, raw.causa_probable),
            ),
            weather=_field(
                rid,
                "registros[].condiciones.clima",
                lambda: norm.to_canonical(catalogs.WEATHERS, raw.condiciones.clima),
            ),
            surface=_field(
                rid,
                "registros[].condiciones.superficie",
                lambda: norm.to_canonical(catalogs.SURFACES, raw.condiciones.superficie),
            ),
            lighting=_field(
                rid,
                "registros[].condiciones.iluminacion",
                lambda: norm.to_canonical(catalogs.LIGHTINGS, raw.condiciones.iluminacion),
            ),
            damages_usd=_field(
                rid, "registros[].danos_materiales", lambda: norm.parse_amount(raw.danos_materiales)
            ),
            location=_location(rid, raw),
            vehicles=vehicles,
            people=people,
            summary_mismatch=derived != declared,
            narrative=_field(rid, "registros[].narrativa", lambda: norm.clean_text(raw.narrativa)),
            annulment_reason=None
            if raw.motivo_anulacion is None
            else _field(
                rid, "registros[].motivo_anulacion", lambda: norm.clean_text(raw.motivo_anulacion)
            ),
            replaced_by=replaced_by,
        ),
    )


def _latest_versions(records: list[RawRecord]) -> dict[str, tuple[RawRecord, int]]:
    """R01: por id, el registro de mayor `version` (sin importar su posicion) y cuantos hay."""
    groups: dict[str, list[RawRecord]] = {}
    for record in records:
        groups.setdefault(record.id_parte, []).append(record)
    latest: dict[str, tuple[RawRecord, int]] = {}
    for record_id, versions in groups.items():
        numbers = [v.version for v in versions]
        if len(set(numbers)) != len(numbers):
            raise IngestionError(
                "registro repetido con la misma version",
                record_id=record_id,
                path="registros[].version",
            )
        latest[record_id] = (max(versions, key=lambda v: v.version), len(versions))
    return latest


def _replacements(latest: dict[str, tuple[RawRecord, int]]) -> dict[str, str]:
    """R02: anulado -> reemplazo, desde `reemplaza_a`. El anulado debe existir y estar anulado."""
    replaced_by: dict[str, str] = {}
    for record_id, (record, _) in latest.items():
        target = record.reemplaza_a
        if target is None:
            continue
        path = "registros[].reemplaza_a"
        if target not in latest:
            raise IngestionError(
                f"reemplaza a {target}, que no existe", record_id=record_id, path=path
            )
        status = _field(
            target,
            "registros[].estado",
            partial(norm.to_canonical, catalogs.RECORD_STATUSES, latest[target][0].estado),
        )
        if status is not RecordStatus.ANULADO:
            raise IngestionError(
                f"reemplaza a {target}, que no esta anulado", record_id=record_id, path=path
            )
        replaced_by[target] = record_id
    return replaced_by


def _section(report_id: str, order: int, raw: RawSection) -> ReportSection:
    path = "informes[].secciones[]"
    return _model(
        report_id,
        lambda: ReportSection(
            order=order,
            title=_field(report_id, f"{path}.titulo", lambda: norm.clean_text(raw.titulo)),
            text=_field(report_id, f"{path}.texto", lambda: norm.clean_text(raw.texto)),
        ),
    )


def _report(raw: RawReport) -> Report:
    rid = raw.id
    road = None
    if raw.via_analizada is not None:
        road = _field(
            rid, "informes[].via_analizada", lambda: norm.normalize_road(raw.via_analizada)
        )
    sections = [_section(rid, order, section) for order, section in enumerate(raw.secciones, 1)]
    classification = _field(
        rid,
        "informes[].clasificacion",
        lambda: norm.to_canonical(catalogs.CLASSIFICATIONS, raw.clasificacion),
    )
    # RawDataset ya descarta los no publicos; esta comprobacion cubre un uso directo.
    if classification is not Classification.PUBLICO:
        raise IngestionError("informe no publico", record_id=rid, path="informes[].clasificacion")
    return _model(
        rid,
        lambda: Report(
            report_id=rid,
            title=_field(rid, "informes[].titulo", lambda: norm.clean_text(raw.titulo)),
            date=_field(rid, "informes[].fecha", lambda: norm.parse_report_date(raw.fecha)),
            status=_field(
                rid,
                "informes[].estado",
                lambda: norm.to_canonical(catalogs.REPORT_STATUSES, raw.estado),
            ),
            classification=classification,
            road=road.name if road else None,
            road_code=road.code if road else None,
            supersedes=raw.reemplaza_a,
            sections=sections,
        ),
    )


def _accident_type_definitions(reports: list[Report]) -> dict[AccidentType, str]:
    """A24: definiciones "Tipo: texto." de la seccion "Tipos de siniestro" de un informe vigente."""
    definitions: dict[AccidentType, str] = {}
    for report in sorted(reports, key=lambda r: (r.status.value != "vigente", r.report_id)):
        for section in report.sections:
            if norm.normalize_key(section.title) != DEFINITIONS_SECTION_KEY:
                continue
            for sentence in _SENTENCE_END.split(section.text):
                label, sep, text = sentence.partition(":")
                member = catalogs.ACCIDENT_TYPES.get(norm.normalize_key(label))
                if sep and member is not None and member not in definitions:
                    definitions[member] = text.strip()
    if missing := sorted(t.value for t in set(AccidentType) - set(definitions)):
        raise IngestionError(
            f"falta la definicion de {missing} en la seccion '{DEFINITIONS_SECTION_KEY}'",
            path="informes[].secciones[]",
        )
    return definitions


def build_dataset(raw: RawDataset, *, sha256: str, source_file: str) -> CleanDataset:
    latest = _latest_versions(raw.registros)
    replaced_by = _replacements(latest)
    # R06: salida ordenada por id para que la misma entrada produzca la misma carga.
    accidents = [
        _accident(record, count, replaced_by.get(record_id))
        for record_id, (record, count) in sorted(latest.items())
    ]
    reports = sorted((_report(r) for r in raw.informes), key=lambda r: r.report_id)
    meta = raw.metadata
    info = _model(
        "metadata",
        lambda: DatasetInfo(
            sha256=sha256,
            source_file=source_file,
            source=norm.clean_text(meta.fuente),
            generated=_field(
                "metadata", "metadata.generado", lambda: norm.parse_update_date(meta.generado)
            ),
            schema_version=norm.clean_text(meta.version_esquema),
            timezone=norm.clean_text(meta.zona_horaria),
        ),
    )
    return _model(
        "dataset",
        lambda: CleanDataset(
            info=info,
            accidents=accidents,
            reports=reports,
            accident_type_definitions=_accident_type_definitions(reports),
        ),
    )


def run_pipeline(path: Path) -> CleanDataset:
    content = path.read_bytes()
    return build_dataset(
        parse_raw(content), sha256=hashlib.sha256(content).hexdigest(), source_file=path.name
    )
