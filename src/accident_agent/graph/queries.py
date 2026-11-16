"""Plantillas Cypher del repositorio (tarea 3.2).

Todas son constantes de solo lectura con parametros: los filtros opcionales se expresan como
`($p IS NULL OR ...)`, de modo que ningun valor se concatena en la consulta. Las variantes por
agrupacion (`STATS_QUERIES`) son consultas completas fijadas al importar el modulo.
"""

from typing import Final, LiteralString

from accident_agent.graph.repository import GroupBy

# Filtro comun: una fila por siniestro (cada uno tiene una parroquia, una via, un tipo y una causa).
# Los anulados solo entran si se piden (include_annulled) o se nombran por id.
_FILTERED: Final[LiteralString] = """
MATCH (a:Accident)-[:OCCURRED_IN]->(:Parish)-[:BELONGS_TO]->(can:Canton)
      -[:BELONGS_TO]->(pro:Province)
MATCH (a)-[:ON_ROAD]->(road:Road)
MATCH (a)-[:OF_TYPE]->(t:AccidentType)
MATCH (a)-[:HAS_CAUSE]->(c:Cause)
WHERE (a.is_active OR $include_annulled OR size($accident_ids) > 0)
  AND (size($accident_ids) = 0 OR a.accident_id IN $accident_ids)
  AND ($text_scores IS NULL OR a.accident_id IN keys($text_scores))
  AND ($province IS NULL OR pro.name = $province)
  AND ($canton IS NULL OR can.name = $canton)
  AND ($road_code IS NULL OR road.code = $road_code)
  AND ($road_text IS NULL OR toLower(road.name) CONTAINS $road_text)
  AND ($accident_type IS NULL OR t.code = $accident_type)
  AND ($cause IS NULL OR c.code = $cause)
  AND ($weather IS NULL OR a.weather = $weather)
  AND ($surface IS NULL OR a.surface = $surface)
  AND ($lighting IS NULL OR a.lighting = $lighting)
  AND ($date_from IS NULL OR a.date >= $date_from)
  AND ($date_to IS NULL OR a.date <= $date_to)
  AND (NOT $only_fatal OR a.deaths > 0)
  AND ($vehicle_type IS NULL OR EXISTS {
        (a)<-[:INVOLVED_IN]-(:Vehicle)-[:OF_TYPE]->(:VehicleType {code: $vehicle_type})
      })
"""

# Ids de la pagina y total; con texto se ordena por relevancia, si no por fecha descendente.
SEARCH_IDS: Final[LiteralString] = (
    _FILTERED
    + """
WITH a
ORDER BY coalesce($text_scores[a.accident_id], 0.0) DESC, a.occurred_at DESC, a.accident_id
WITH collect(a.accident_id) AS ids
RETURN size(ids) AS total, ids[0..$limit] AS page
"""
)

# Detalle completo por id, con vehiculos y personas en orden de id.
ACCIDENT_DETAILS: Final[LiteralString] = """
MATCH (a:Accident) WHERE a.accident_id IN $ids
MATCH (a)-[:OCCURRED_IN]->(par:Parish)-[:BELONGS_TO]->(can:Canton)-[:BELONGS_TO]->(pro:Province)
MATCH (a)-[on:ON_ROAD]->(road:Road)
MATCH (a)-[:OF_TYPE]->(t:AccidentType)
MATCH (a)-[:HAS_CAUSE]->(c:Cause)
OPTIONAL MATCH (a)-[:REPLACED_BY]->(rep:Accident)
OPTIONAL MATCH (prev:Accident)-[:REPLACED_BY]->(a)
CALL (a) {
  MATCH (v:Vehicle)-[:INVOLVED_IN]->(a)
  MATCH (v)-[:OF_TYPE]->(vt:VehicleType)
  WITH v, vt ORDER BY v.vehicle_id
  RETURN collect(v {.*, vehicle_type: vt.code}) AS vehicles
}
CALL (a) {
  MATCH (p:Person)-[:PARTICIPATED_IN]->(a)
  OPTIONAL MATCH (p)-[:RODE_IN]->(pv:Vehicle)
  WITH p, pv ORDER BY p.person_id
  RETURN collect(p {.*, vehicle_id: pv.vehicle_id}) AS people
}
RETURN a {.*,
  accident_type: t.code, cause: c.code,
  province: pro.name, canton: can.name, parish: par.name,
  road: road.name, road_code: road.code, km: on.km,
  replaced_by: rep.accident_id, replaces: prev.accident_id,
  vehicles: vehicles, people: people
} AS accident
"""

_STATS_TAIL: Final[LiteralString] = """
RETURN grp AS group, count(a) AS accidents, sum(a.deaths) AS deaths,
       sum(a.injured) AS injured, sum(a.damages_usd) AS damages_usd
ORDER BY accidents DESC, group
"""

STATS_QUERIES: Final[dict[GroupBy, LiteralString]] = {
    GroupBy.PROVINCE: _FILTERED + "WITH DISTINCT a, pro.name AS grp" + _STATS_TAIL,
    GroupBy.CAUSE: _FILTERED + "WITH DISTINCT a, c.code AS grp" + _STATS_TAIL,
    GroupBy.ACCIDENT_TYPE: _FILTERED + "WITH DISTINCT a, t.code AS grp" + _STATS_TAIL,
    GroupBy.MONTH: _FILTERED
    + "WITH DISTINCT a, substring(toString(a.date), 0, 7) AS grp"
    + _STATS_TAIL,
    GroupBy.YEAR: _FILTERED + "WITH DISTINCT a, toString(a.year) AS grp" + _STATS_TAIL,
    GroupBy.WEATHER: _FILTERED + "WITH DISTINCT a, a.weather AS grp" + _STATS_TAIL,
    # Un siniestro con dos tipos de vehiculo cuenta en ambos grupos.
    GroupBy.VEHICLE_TYPE: _FILTERED
    + "MATCH (a)<-[:INVOLVED_IN]-(:Vehicle)-[:OF_TYPE]->(vt:VehicleType)"
    + " WITH DISTINCT a, vt.code AS grp"
    + _STATS_TAIL,
}

FULLTEXT_ACCIDENTS: Final[LiteralString] = """
CALL db.index.fulltext.queryNodes('accident_narratives', $query) YIELD node, score
RETURN node.accident_id AS accident_id, score
"""

_REPORT_FIELDS: Final[LiteralString] = """
OPTIONAL MATCH (r)-[:SUPERSEDES]->(old:Report)
OPTIONAL MATCH (newer:Report)-[:SUPERSEDES]->(r)
OPTIONAL MATCH (r)-[:ANALYZES_ROAD]->(road:Road)
RETURN r.report_id AS report_id, r.title AS title, r.date AS date, r.status AS status,
       road.code AS road_code, s.order AS section_order, s.title AS section_title,
       s.text AS text, score, old.report_id AS supersedes, newer.report_id AS superseded_by
"""

# Los informes vigentes van primero (escenario 8); despues, relevancia o fecha.
REPORTS_BY_TEXT: Final[LiteralString] = (
    """
CALL db.index.fulltext.queryNodes('report_texts', $query) YIELD node AS s, score
MATCH (r:Report)-[:HAS_SECTION]->(s)
WHERE $road_code IS NULL OR EXISTS { (r)-[:ANALYZES_ROAD]->(:Road {code: $road_code}) }
"""
    + _REPORT_FIELDS
    + "ORDER BY status = 'vigente' DESC, score DESC, report_id, section_order LIMIT $limit"
)

REPORTS_ALL: Final[LiteralString] = (
    """
MATCH (r:Report)-[:HAS_SECTION]->(s:ReportSection)
WHERE $road_code IS NULL OR EXISTS { (r)-[:ANALYZES_ROAD]->(:Road {code: $road_code}) }
WITH r, s, null AS score
"""
    + _REPORT_FIELDS
    + "ORDER BY status = 'vigente' DESC, date DESC, report_id, section_order LIMIT $limit"
)

DATASET_INFO: Final[LiteralString] = """
MATCH (d:Dataset)
RETURN d.source AS source, d.source_file AS source_file, d.sha256 AS sha256,
       d.generated AS generated
"""
