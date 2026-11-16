"""Escritura del `CleanDataset` en Neo4j (tarea 2.3). Modelo: `docs/modelo_grafo.md`.

- El esquema (restricciones e indices) se crea con `IF NOT EXISTS` en transacciones propias:
  Neo4j no mezcla esquema y datos en una transaccion.
- Los datos se recargan en una sola transaccion de escritura: se borra todo y se crea de nuevo
  con `UNWIND`. Es idempotente y atomica: si algo falla, queda la carga anterior.
- Cada sentencia comprueba cuantos nodos y relaciones creo. Un `MATCH` que no encuentra su nodo
  no falla en Cypher, solo deja de crear; aqui eso aborta la transaccion.
- Todo Cypher es constante y parametrizado: los datos nunca se concatenan en la consulta.
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Final, LiteralString

from neo4j import Driver, ManagedTransaction
from pydantic import BaseModel, ConfigDict

from accident_agent.domain.catalogs import AccidentType, Cause, VehicleType, display_label
from accident_agent.domain.models import Accident, CleanDataset
from accident_agent.ingestion.normalizers import normalize_key

Row = dict[str, Any]

SCHEMA_STATEMENTS: Final[tuple[LiteralString, ...]] = (
    "CREATE CONSTRAINT accident_id IF NOT EXISTS FOR (n:Accident) REQUIRE n.accident_id IS UNIQUE",
    "CREATE CONSTRAINT province_name IF NOT EXISTS FOR (n:Province) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT canton_id IF NOT EXISTS FOR (n:Canton) REQUIRE n.canton_id IS UNIQUE",
    "CREATE CONSTRAINT parish_id IF NOT EXISTS FOR (n:Parish) REQUIRE n.parish_id IS UNIQUE",
    "CREATE CONSTRAINT road_name IF NOT EXISTS FOR (n:Road) REQUIRE n.name IS UNIQUE",
    "CREATE CONSTRAINT accident_type_code IF NOT EXISTS"
    " FOR (n:AccidentType) REQUIRE n.code IS UNIQUE",
    "CREATE CONSTRAINT cause_code IF NOT EXISTS FOR (n:Cause) REQUIRE n.code IS UNIQUE",
    "CREATE CONSTRAINT vehicle_type_code IF NOT EXISTS"
    " FOR (n:VehicleType) REQUIRE n.code IS UNIQUE",
    "CREATE CONSTRAINT vehicle_id IF NOT EXISTS FOR (n:Vehicle) REQUIRE n.vehicle_id IS UNIQUE",
    "CREATE CONSTRAINT person_id IF NOT EXISTS FOR (n:Person) REQUIRE n.person_id IS UNIQUE",
    "CREATE CONSTRAINT report_id IF NOT EXISTS FOR (n:Report) REQUIRE n.report_id IS UNIQUE",
    "CREATE CONSTRAINT section_id IF NOT EXISTS"
    " FOR (n:ReportSection) REQUIRE n.section_id IS UNIQUE",
    "CREATE CONSTRAINT dataset_sha256 IF NOT EXISTS FOR (n:Dataset) REQUIRE n.sha256 IS UNIQUE",
    "CREATE INDEX accident_occurred_at IF NOT EXISTS FOR (n:Accident) ON (n.occurred_at)",
    "CREATE INDEX accident_date IF NOT EXISTS FOR (n:Accident) ON (n.date)",
    "CREATE INDEX accident_is_active IF NOT EXISTS FOR (n:Accident) ON (n.is_active)",
    "CREATE INDEX accident_weather IF NOT EXISTS FOR (n:Accident) ON (n.weather)",
    "CREATE INDEX accident_surface IF NOT EXISTS FOR (n:Accident) ON (n.surface)",
    "CREATE INDEX accident_lighting IF NOT EXISTS FOR (n:Accident) ON (n.lighting)",
    "CREATE FULLTEXT INDEX accident_narratives IF NOT EXISTS FOR (n:Accident) ON EACH"
    " [n.narrative_search] OPTIONS {indexConfig: {`fulltext.analyzer`: 'spanish'}}",
    "CREATE FULLTEXT INDEX report_texts IF NOT EXISTS FOR (n:ReportSection) ON EACH"
    " [n.title_search, n.text_search] OPTIONS {indexConfig: {`fulltext.analyzer`: 'spanish'}}",
)
# Propiedades que debe indexar cada indice full-text. Si un indice existente indexa otras,
# se borra y se crea de nuevo: CREATE ... IF NOT EXISTS no cambia un indice que ya existe.
FULLTEXT_PROPERTIES: Final[dict[str, list[str]]] = {
    "accident_narratives": ["narrative_search"],
    "report_texts": ["title_search", "text_search"],
}


class GraphRows(BaseModel):
    """Filas listas para `UNWIND`: solo tipos que el driver entiende (sin enums ni modelos)."""

    model_config = ConfigDict(frozen=True)

    dataset: Row
    provinces: list[Row]
    cantons: list[Row]
    parishes: list[Row]
    roads: list[Row]
    accident_types: list[Row]
    causes: list[Row]
    vehicle_types: list[Row]
    accidents: list[Row]
    replacements: list[Row]
    vehicles: list[Row]
    people: list[Row]
    reports: list[Row]
    sections: list[Row]
    supersedes: list[Row]
    report_roads: list[Row]


def _plain(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime) and value.tzinfo is not None:
        # Desfase fijo en lugar de ZoneInfo: el driver pasa su propio tipo de fecha a
        # ZoneInfo.utcoffset, y en Python 3.12.15 eso provoca un fallo de segmentacion.
        # America/Guayaquil no tiene horario de verano, asi que no se pierde informacion.
        return value.astimezone(timezone(value.utcoffset() or timedelta(0)))
    return value


def _props(model: BaseModel, *, exclude: set[str]) -> Row:
    return {k: _plain(v) for k, v in model.model_dump(exclude=exclude).items()}


def _canton_id(accident: Accident) -> str:
    return f"{accident.location.province.value}|{accident.location.canton}"


def graph_rows(dataset: CleanDataset) -> GraphRows:
    accidents = dataset.accidents
    roads: dict[str, str | None] = {a.location.road: a.location.road_code for a in accidents}
    roads |= {r.road: r.road_code for r in dataset.reports if r.road is not None}
    cantons = {
        _canton_id(a): {"name": a.location.canton, "province": a.location.province.value}
        for a in accidents
    }
    parishes = {
        f"{_canton_id(a)}|{a.location.parish}": {
            "name": a.location.parish,
            "canton_id": _canton_id(a),
        }
        for a in accidents
    }
    accident_exclude = {"location", "vehicles", "people", "replaced_by", "accident_type", "cause"}
    return GraphRows(
        dataset=_props(dataset.info, exclude=set()),
        provinces=[{"name": p} for p in sorted({a.location.province.value for a in accidents})],
        cantons=[{"canton_id": k, **v} for k, v in sorted(cantons.items())],
        parishes=[{"parish_id": k, **v} for k, v in sorted(parishes.items())],
        roads=[{"name": name, "code": code} for name, code in sorted(roads.items())],
        accident_types=[
            {
                "code": t.value,
                "name": display_label(t.value),
                "definition": dataset.accident_type_definitions[t],
            }
            for t in AccidentType
        ],
        causes=[{"code": c.value, "name": display_label(c.value)} for c in Cause],
        vehicle_types=[{"code": t.value, "name": display_label(t.value)} for t in VehicleType],
        accidents=[
            {
                "props": _props(a, exclude=accident_exclude)
                | {
                    "latitude": a.location.latitude,
                    "longitude": a.location.longitude,
                    # Copia sin tildes para el full-text: el stemmer espanol de Lucene no quita
                    # las tildes de palabras cortas ("via" no encontraria "via" con tilde).
                    "narrative_search": normalize_key(a.narrative),
                },
                "parish_id": f"{_canton_id(a)}|{a.location.parish}",
                "road": a.location.road,
                "km": a.location.km,
                "accident_type": a.accident_type.value,
                "cause": a.cause.value,
            }
            for a in accidents
        ],
        replacements=[
            {"annulled": a.accident_id, "replacement": a.replaced_by}
            for a in accidents
            if a.replaced_by is not None
        ],
        vehicles=[
            {
                "props": _props(v, exclude={"vehicle_type"}),
                "accident_id": a.accident_id,
                "vehicle_type": v.vehicle_type.value,
            }
            for a in accidents
            for v in a.vehicles
        ],
        people=[
            {
                "props": _props(p, exclude={"vehicle_id"}),
                "accident_id": a.accident_id,
                "vehicle_id": p.vehicle_id,
            }
            for a in accidents
            for p in a.people
        ],
        reports=[
            {"props": _props(r, exclude={"road", "road_code", "supersedes", "sections"})}
            for r in dataset.reports
        ],
        sections=[
            {
                "props": {
                    "section_id": f"{r.report_id}-S{s.order}",
                    **_props(s, exclude=set()),
                    "title_search": normalize_key(s.title),
                    "text_search": normalize_key(s.text),
                },
                "report_id": r.report_id,
            }
            for r in dataset.reports
            for s in r.sections
        ],
        supersedes=[
            {"report_id": r.report_id, "previous": r.supersedes}
            for r in dataset.reports
            if r.supersedes is not None
        ],
        report_roads=[
            {"report_id": r.report_id, "road": r.road}
            for r in dataset.reports
            if r.road is not None
        ],
    )


class LoadMismatchError(RuntimeError):
    """Una sentencia creo menos nodos o relaciones de los esperados."""


# (sentencia, filas, nodos esperados por fila, relaciones esperadas)
_DELETE_ALL: Final = "MATCH (n) DETACH DELETE n"
_CREATE_DATASET: Final = "CREATE (d:Dataset) SET d = $row"
_LOAD: Final[tuple[tuple[str, LiteralString], ...]] = (
    ("provinces", "UNWIND $rows AS row CREATE (:Province {name: row.name})"),
    (
        "cantons",
        "UNWIND $rows AS row MATCH (p:Province {name: row.province})"
        " CREATE (:Canton {canton_id: row.canton_id, name: row.name})-[:BELONGS_TO]->(p)",
    ),
    (
        "parishes",
        "UNWIND $rows AS row MATCH (c:Canton {canton_id: row.canton_id})"
        " CREATE (:Parish {parish_id: row.parish_id, name: row.name})-[:BELONGS_TO]->(c)",
    ),
    ("roads", "UNWIND $rows AS row CREATE (:Road {name: row.name, code: row.code})"),
    (
        "accident_types",
        "UNWIND $rows AS row"
        " CREATE (:AccidentType {code: row.code, name: row.name, definition: row.definition})",
    ),
    ("causes", "UNWIND $rows AS row CREATE (:Cause {code: row.code, name: row.name})"),
    ("vehicle_types", "UNWIND $rows AS row CREATE (:VehicleType {code: row.code, name: row.name})"),
    (
        "accidents",
        "UNWIND $rows AS row"
        " MATCH (p:Parish {parish_id: row.parish_id}), (r:Road {name: row.road}),"
        " (t:AccidentType {code: row.accident_type}), (c:Cause {code: row.cause})"
        " CREATE (a:Accident) SET a = row.props"
        " CREATE (a)-[:OCCURRED_IN]->(p), (a)-[:ON_ROAD {km: row.km}]->(r),"
        " (a)-[:OF_TYPE]->(t), (a)-[:HAS_CAUSE]->(c)",
    ),
    (
        "replacements",
        "UNWIND $rows AS row"
        " MATCH (old:Accident {accident_id: row.annulled}),"
        " (new:Accident {accident_id: row.replacement})"
        " CREATE (old)-[:REPLACED_BY]->(new)",
    ),
    (
        "vehicles",
        "UNWIND $rows AS row"
        " MATCH (a:Accident {accident_id: row.accident_id}),"
        " (t:VehicleType {code: row.vehicle_type})"
        " CREATE (v:Vehicle) SET v = row.props"
        " CREATE (v)-[:INVOLVED_IN]->(a), (v)-[:OF_TYPE]->(t)",
    ),
    (
        "people",
        "UNWIND $rows AS row"
        " MATCH (a:Accident {accident_id: row.accident_id})"
        " CREATE (p:Person) SET p = row.props"
        " CREATE (p)-[:PARTICIPATED_IN]->(a)"
        " WITH p, row WHERE row.vehicle_id IS NOT NULL"
        " MATCH (v:Vehicle {vehicle_id: row.vehicle_id})"
        " CREATE (p)-[:RODE_IN]->(v)",
    ),
    ("reports", "UNWIND $rows AS row CREATE (r:Report) SET r = row.props"),
    (
        "sections",
        "UNWIND $rows AS row MATCH (r:Report {report_id: row.report_id})"
        " CREATE (s:ReportSection) SET s = row.props CREATE (r)-[:HAS_SECTION]->(s)",
    ),
    (
        "supersedes",
        "UNWIND $rows AS row"
        " MATCH (new:Report {report_id: row.report_id}), (old:Report {report_id: row.previous})"
        " CREATE (new)-[:SUPERSEDES]->(old)",
    ),
    (
        "report_roads",
        "UNWIND $rows AS row"
        " MATCH (r:Report {report_id: row.report_id}), (road:Road {name: row.road})"
        " CREATE (r)-[:ANALYZES_ROAD]->(road)",
    ),
)
# Nodos y relaciones que crea cada fila de cada sentencia.
_PER_ROW: Final[dict[str, tuple[int, int]]] = {
    "provinces": (1, 0),
    "cantons": (1, 1),
    "parishes": (1, 1),
    "roads": (1, 0),
    "accident_types": (1, 0),
    "causes": (1, 0),
    "vehicle_types": (1, 0),
    "accidents": (1, 4),
    "replacements": (0, 1),
    "vehicles": (1, 2),
    "people": (1, 1),
    "reports": (1, 0),
    "sections": (1, 1),
    "supersedes": (0, 1),
    "report_roads": (0, 1),
}


def _expected(name: str, rows: GraphRows) -> tuple[int, int]:
    batch: list[Row] = getattr(rows, name)
    nodes, rels = _PER_ROW[name]
    extra = sum(r["vehicle_id"] is not None for r in batch) if name == "people" else 0
    return nodes * len(batch), rels * len(batch) + extra


def _load(tx: ManagedTransaction, rows: GraphRows) -> dict[str, tuple[int, int]]:
    tx.run(_DELETE_ALL).consume()
    tx.run(_CREATE_DATASET, row=rows.dataset).consume()
    created: dict[str, tuple[int, int]] = {}
    for name, statement in _LOAD:
        counters = tx.run(statement, rows=getattr(rows, name)).consume().counters
        result = (counters.nodes_created, counters.relationships_created)
        if result != _expected(name, rows):
            expected = _expected(name, rows)
            raise LoadMismatchError(
                f"{name}: se crearon {result} (nodos, relaciones); se esperaban {expected}"
            )
        created[name] = result
    return created


class Neo4jWriter:
    def __init__(self, driver: Driver) -> None:
        self._driver = driver

    def apply_schema(self) -> None:
        records, _, _ = self._driver.execute_query(
            "SHOW FULLTEXT INDEXES YIELD name, properties RETURN name, properties"
        )
        for record in records:
            expected = FULLTEXT_PROPERTIES.get(record["name"])
            if expected is not None and record["properties"] != expected:
                self._driver.execute_query(
                    f"DROP INDEX {record['name']}"
                )  # nombre de la lista fija
        for statement in SCHEMA_STATEMENTS:
            self._driver.execute_query(statement)

    def write(self, dataset: CleanDataset) -> dict[str, tuple[int, int]]:
        """Recarga completa; devuelve (nodos, relaciones) creados por sentencia."""
        self.apply_schema()
        rows = graph_rows(dataset)
        with self._driver.session() as session:
            created = session.execute_write(_load, rows)
        # Los indices full-text se pueblan en segundo plano; se espera a que esten en linea.
        self._driver.execute_query("CALL db.awaitIndexes(120)")
        return created
