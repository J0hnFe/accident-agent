"""Consultas de ejemplo de `docs/modelo_grafo.md` (seccion 9) con sus parametros.

Las usan las pruebas de integracion y la evidencia de la tarea 2.8. Solo lectura y parametrizadas.
"""

from datetime import date
from typing import Any, Final, LiteralString, NamedTuple


class ExampleQuery(NamedTuple):
    title: str
    cypher: LiteralString
    params: dict[str, Any]


EXAMPLES: Final[dict[str, ExampleQuery]] = {
    "by_province": ExampleQuery(
        "Siniestros vigentes por provincia",
        "MATCH (a:Accident {is_active: true})-[:OCCURRED_IN]->(:Parish)-[:BELONGS_TO]->(:Canton)"
        "-[:BELONGS_TO]->(p:Province)"
        " RETURN p.name AS province, count(a) AS accidents ORDER BY accidents DESC, province",
        {},
    ),
    "fatal_on_road": ExampleQuery(
        "Siniestros con fallecidos en una via",
        "MATCH (a:Accident {is_active: true})-[r:ON_ROAD]->(road:Road {code: $road_code})"
        " WHERE a.deaths > 0"
        " RETURN a.accident_id AS accident_id, a.date AS date, a.deaths AS deaths, r.km AS km"
        " ORDER BY a.date",
        {"road_code": "E35"},
    ),
    "by_vehicle_type": ExampleQuery(
        "Siniestros con un tipo de vehiculo",
        "MATCH (a:Accident {is_active: true})<-[:INVOLVED_IN]-(:Vehicle)"
        "-[:OF_TYPE]->(:VehicleType {code: $vehicle_type})"
        " RETURN count(DISTINCT a) AS accidents",
        {"vehicle_type": "motocicleta"},
    ),
    "date_range": ExampleQuery(
        "Siniestros en un rango de fechas (ultimos 6 meses desde 2026-11-15)",
        "MATCH (a:Accident {is_active: true})"
        " WHERE a.date >= $date_from AND a.date <= $date_to"
        " RETURN a.accident_id AS accident_id, a.date AS date ORDER BY a.date",
        {"date_from": date(2026, 5, 15), "date_to": date(2026, 11, 15)},
    ),
    "annulled_trace": ExampleQuery(
        "Trazabilidad de un anulado",
        "MATCH (a:Accident {accident_id: $accident_id})"
        " OPTIONAL MATCH (a)-[:REPLACED_BY]->(r:Accident)"
        " RETURN a.accident_id AS accident_id, a.status AS status,"
        " a.annulment_reason AS annulment_reason, r.accident_id AS replaced_by",
        {"accident_id": "SIN-2026-0010"},
    ),
    "narrative_search": ExampleQuery(
        "Busqueda en narrativas",
        "CALL db.index.fulltext.queryNodes('accident_narratives', $text) YIELD node, score"
        " WHERE node.is_active"
        " RETURN node.accident_id AS accident_id, round(score, 3) AS score"
        " ORDER BY score DESC, accident_id LIMIT 10",
        {"text": "neblina"},
    ),
    "road_reports": ExampleQuery(
        "Informes de una via, vigentes primero",
        "MATCH (rep:Report)-[:ANALYZES_ROAD]->(:Road {code: $road_code})"
        " OPTIONAL MATCH (rep)-[:SUPERSEDES]->(old:Report)"
        " RETURN rep.report_id AS report_id, rep.status AS status, old.report_id AS supersedes"
        " ORDER BY rep.status = 'vigente' DESC, rep.date DESC",
        {"road_code": "E35"},
    ),
    "accident_subgraph": ExampleQuery(
        "Subgrafo de un siniestro (caminos devueltos)",
        "MATCH (a:Accident {accident_id: $accident_id})"
        " CALL (a) {"
        "   MATCH p = (a)-[:OCCURRED_IN]->()-[:BELONGS_TO]->()-[:BELONGS_TO]->() RETURN p"
        "   UNION"
        "   MATCH p = (a)-[:ON_ROAD|OF_TYPE|HAS_CAUSE|REPLACED_BY]-() RETURN p"
        "   UNION"
        "   MATCH p = (a)<-[:INVOLVED_IN]-()-[:OF_TYPE]->() RETURN p"
        "   UNION"
        "   MATCH p = (a)<-[:PARTICIPATED_IN]-()-[:RODE_IN*0..1]->() RETURN p"
        " }"
        " RETURN count(p) AS paths",
        {"accident_id": "SIN-2025-0001"},
    ),
}
