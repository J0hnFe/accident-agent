"""Modelos permisivos del JSON original (tarea 1.8).

Aceptan exactamente los tipos observados en cada campo (`docs/datos/analisis_datos.md`) y los
conservan sin convertir: la conversion es trabajo de los normalizadores. Una clave nueva o
faltante es error, para detectar cambios de estructura.

Datos personales:
- `nombre` y `cedula` se descartan antes de validar; nunca existen en estos modelos.
- Las placas se conservan solo para enlazar persona y vehiculo (regla R04); no salen en `repr`
  ni al serializar.
- Los informes no publicos (INF-RES-01) se descartan al leer, texto incluido (regla P3).
- Los errores de validacion no muestran los valores de entrada.

Uso: `RawDataset.model_validate_json(bytes_del_archivo)`.
"""

from typing import Any, Final

from pydantic import BaseModel, ConfigDict, Field, model_validator

from accident_agent.ingestion.normalizers import normalize_key

_DROPPED_PERSON_KEYS: Final = frozenset({"nombre", "cedula"})


class _RawModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", hide_input_in_errors=True)


class RawMetadata(_RawModel):
    fuente: str
    generado: str
    version_esquema: str
    zona_horaria: str
    formato_fechas_texto: str
    total_registros: int
    aviso: str


class RawDateParts(_RawModel):
    fecha: str
    hora: str


class RawCoordinates(_RawModel):
    latitud: float
    longitud: float


class RawLocation(_RawModel):
    provincia: str
    canton: str
    parroquia: str
    via: str
    km: int | float | str | None
    coordenadas: str | RawCoordinates | None


class RawConditions(_RawModel):
    clima: str
    superficie: str
    iluminacion: str


class RawSummary(_RawModel):
    fallecidos: int
    heridos: int
    ilesos: int


class RawVehicle(_RawModel):
    tipo_vehiculo: str
    marca_modelo: str | None = None
    marca: str | None = None
    modelo: str | None = None
    anio: int | str
    servicio: str
    placa: str = Field(repr=False, exclude=True)


class RawPerson(_RawModel):
    rol: str
    edad: int | str
    sexo: str
    condicion: str
    alcohol_gl: float | str | None
    proteccion: str | None
    placa_vehiculo: str | None = Field(repr=False, exclude=True)
    dias_hasta_deceso: int | None = None

    @model_validator(mode="before")
    @classmethod
    def _drop_personal_data(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k not in _DROPPED_PERSON_KEYS}
        return data


class RawRecord(_RawModel):
    id_parte: str
    version: int
    fecha_actualizacion: str
    estado: str
    fecha_hora: str | RawDateParts
    ubicacion: RawLocation
    tipo_siniestro: str
    causa_probable: str
    condiciones: RawConditions
    danos_materiales: int | float | str
    resumen: RawSummary
    vehiculos: list[RawVehicle]
    personas: list[RawPerson]
    narrativa: str = Field(repr=False)
    fuente: str
    motivo_anulacion: str | None = None
    reemplaza_a: str | None = None


class RawSection(_RawModel):
    titulo: str
    texto: str = Field(repr=False)


class RawReport(_RawModel):
    id: str
    titulo: str
    fecha: str
    estado: str
    clasificacion: str
    via_analizada: str | None
    reemplaza_a: str | None = None
    secciones: list[RawSection]


class RawDataset(_RawModel):
    metadata: RawMetadata
    registros: list[RawRecord]
    informes: list[RawReport]
    # Ids de los informes descartados al leer; se conservan para el log de la carga.
    excluded_report_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _drop_restricted_reports(cls, data: Any) -> Any:
        if not isinstance(data, dict) or not isinstance(data.get("informes"), list):
            return data
        public, excluded = [], []
        for report in data["informes"]:
            classification = report.get("clasificacion") if isinstance(report, dict) else None
            if isinstance(classification, str) and normalize_key(classification) != "publico":
                excluded.append(str(report.get("id")))
            else:
                public.append(report)
        return {**data, "informes": public, "excluded_report_ids": excluded}


def to_json_value(value: Any) -> Any:
    """Valor JSON original de un campo: los objetos anidados (fecha, coordenadas) vuelven a ser
    diccionarios, que es lo que reciben los normalizadores."""
    return value.model_dump() if isinstance(value, BaseModel) else value
