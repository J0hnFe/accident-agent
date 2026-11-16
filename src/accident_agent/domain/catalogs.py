"""Catalogos canonicos de los valores categoricos (tarea 1.6).

Especificacion: `docs/datos/reglas_normalizacion.md`, seccion 3. Cada catalogo cerrado es un
`StrEnum` con los valores canonicos en espanol y una tabla de busqueda de clave normalizada
(`normalize_key`) a valor canonico. Aplicar la clave y fallar ante un valor desconocido es
responsabilidad de los normalizadores (tarea 1.7).

Los miembros repiten el valor canonico en mayusculas (`CHOQUE = "choque"`) en lugar de
traducirlo, para que el codigo y los datos usen el mismo termino.

Canton, parroquia y via no tienen catalogo cerrado: su nombre se deriva de la clave (reglas N02
y N03). Aqui solo vive el alias de via.
"""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Final


def build_lookup[E: StrEnum](
    enum_cls: type[E], synonyms: Mapping[str, E] | None = None
) -> Mapping[str, E]:
    """Tabla de solo lectura de clave a valor canonico.

    Incluye la forma propia de cada valor (`perdida_de_pista`) y su version con espacios
    (`perdida de pista`), mas los sinonimos explicitos. Un sinonimo que apunta a otro valor
    falla al importar en lugar de pisar la entrada en silencio.
    """
    table: dict[str, E] = {}

    def add(key: str, member: E) -> None:
        current = table.get(key)
        if current is not None and current is not member:
            raise ValueError(f"La clave {key!r} apunta a {current.value!r} y a {member.value!r}")
        table[key] = member

    for member in enum_cls:
        add(member.value.casefold(), member)
        add(member.value.replace("_", " ").casefold(), member)
    for key, member in (synonyms or {}).items():
        add(key, member)
    return MappingProxyType(table)


class AccidentType(StrEnum):
    """Tipos de siniestro de INF-2026-02; sus definiciones se toman del informe en la carga."""

    CHOQUE = "choque"
    ESTRELLAMIENTO = "estrellamiento"
    ATROPELLO = "atropello"
    VOLCAMIENTO = "volcamiento"
    PERDIDA_DE_PISTA = "perdida_de_pista"


class Cause(StrEnum):
    EXCESO_DE_VELOCIDAD = "exceso_de_velocidad"
    CONDUCIR_BAJO_EFECTOS_DEL_ALCOHOL = "conducir_bajo_efectos_del_alcohol"
    INVADIR_CARRIL = "invadir_carril"
    DISTRACCION_DEL_CONDUCTOR = "distraccion_del_conductor"
    PEATON_EN_LA_VIA = "peaton_en_la_via"
    MAL_ESTADO_DE_LA_VIA = "mal_estado_de_la_via"
    NO_RESPETAR_SEMAFORO = "no_respetar_semaforo"
    SOMNOLENCIA = "somnolencia"
    ADELANTAMIENTO_INDEBIDO = "adelantamiento_indebido"
    FALLO_MECANICO = "fallo_mecanico"


class Weather(StrEnum):
    DESPEJADO = "despejado"
    LLUVIA = "lluvia"
    NEBLINA = "neblina"


class Surface(StrEnum):
    SECA = "seca"
    MOJADA = "mojada"
    HUMEDA = "humeda"


class Lighting(StrEnum):
    DIURNA = "diurna"
    NOCTURNA_CON_ILUMINACION = "nocturna_con_iluminacion"
    NOCTURNA_SIN_ILUMINACION = "nocturna_sin_iluminacion"
    AMANECER_ATARDECER = "amanecer_atardecer"


class VehicleType(StrEnum):
    """`camion` queda separado de liviano y pesado: el dato no dice cual de los dos es."""

    AUTOMOVIL = "automovil"
    CAMIONETA = "camioneta"
    MOTOCICLETA = "motocicleta"
    BUS = "bus"
    CAMION = "camion"
    CAMION_LIVIANO = "camion_liviano"
    CAMION_PESADO = "camion_pesado"
    SUV = "suv"
    TAXI = "taxi"
    TRAILER = "trailer"


class VehicleService(StrEnum):
    PARTICULAR = "particular"
    CARGA = "carga"
    PUBLICO = "publico"


class PersonRole(StrEnum):
    CONDUCTOR = "conductor"
    PASAJERO = "pasajero"
    PEATON = "peaton"


class PersonCondition(StrEnum):
    """Gravedad de INF-2026-02; fallecido incluye las muertes hasta 30 dias despues."""

    FALLECIDO = "fallecido"
    HERIDO_GRAVE = "herido_grave"
    HERIDO_LEVE = "herido_leve"
    ILESO = "ileso"


class Sex(StrEnum):
    M = "M"
    F = "F"


class Protection(StrEnum):
    """Valores de `uso_proteccion` en INF-2026-02."""

    CINTURON = "cinturon"
    CASCO = "casco"
    NINGUNA = "ninguna"
    NO_APLICA = "no_aplica"
    NO_REGISTRADO = "no_registrado"


class RecordStatus(StrEnum):
    """`estado_registro` de INF-2026-02; el JSON lo llama `estado` y usa ACTIVO/ANULADO."""

    VIGENTE = "vigente"
    ANULADO = "anulado"


class ReportStatus(StrEnum):
    VIGENTE = "vigente"
    REEMPLAZADO = "reemplazado"


class Classification(StrEnum):
    PUBLICO = "publico"
    RESERVADO = "reservado"


class Province(StrEnum):
    """Las 24 provincias, no solo las observadas: una consulta por una provincia valida sin
    siniestros (Galapagos) debe dar cero resultados y no un error de validacion."""

    AZUAY = "Azuay"
    BOLIVAR = "Bolivar"
    CANAR = "Canar"
    CARCHI = "Carchi"
    CHIMBORAZO = "Chimborazo"
    COTOPAXI = "Cotopaxi"
    EL_ORO = "El Oro"
    ESMERALDAS = "Esmeraldas"
    GALAPAGOS = "Galapagos"
    GUAYAS = "Guayas"
    IMBABURA = "Imbabura"
    LOJA = "Loja"
    LOS_RIOS = "Los Rios"
    MANABI = "Manabi"
    MORONA_SANTIAGO = "Morona Santiago"
    NAPO = "Napo"
    ORELLANA = "Orellana"
    PASTAZA = "Pastaza"
    PICHINCHA = "Pichincha"
    SANTA_ELENA = "Santa Elena"
    SANTO_DOMINGO_DE_LOS_TSACHILAS = "Santo Domingo de los Tsachilas"
    SUCUMBIOS = "Sucumbios"
    TUNGURAHUA = "Tungurahua"
    ZAMORA_CHINCHIPE = "Zamora Chinchipe"


ACCIDENT_TYPES: Final = build_lookup(AccidentType)
CAUSES: Final = build_lookup(
    Cause,
    {
        "velocidad excesiva": Cause.EXCESO_DE_VELOCIDAD,
        "conducir en estado de ebriedad": Cause.CONDUCIR_BAJO_EFECTOS_DEL_ALCOHOL,
    },
)
WEATHERS: Final = build_lookup(Weather)
SURFACES: Final = build_lookup(Surface)
LIGHTINGS: Final = build_lookup(Lighting)
VEHICLE_TYPES: Final = build_lookup(VehicleType)
VEHICLE_SERVICES: Final = build_lookup(VehicleService)
PERSON_ROLES: Final = build_lookup(PersonRole)
PERSON_CONDITIONS: Final = build_lookup(PersonCondition)
SEXES: Final = build_lookup(
    Sex,
    {
        "masculino": Sex.M,
        "hombre": Sex.M,
        "femenino": Sex.F,
        "mujer": Sex.F,
    },
)
PROTECTIONS: Final = build_lookup(
    Protection,
    {
        "si - cinturon": Protection.CINTURON,
        "cinturon de seguridad": Protection.CINTURON,
        "si - casco": Protection.CASCO,
        "ninguno": Protection.NINGUNA,
        "no": Protection.NINGUNA,
        "n/a": Protection.NO_APLICA,
        "sin dato": Protection.NO_REGISTRADO,
        "": Protection.NO_REGISTRADO,
    },
)
RECORD_STATUSES: Final = build_lookup(RecordStatus, {"activo": RecordStatus.VIGENTE})
REPORT_STATUSES: Final = build_lookup(ReportStatus)
CLASSIFICATIONS: Final = build_lookup(Classification)
PROVINCES: Final = build_lookup(Province)

# Clave de via -> clave canonica. El codigo de via (E35, E45, E15) se extrae del texto (N03).
ROAD_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {"e35": "panamericana e35 (troncal de la sierra)"}
)
