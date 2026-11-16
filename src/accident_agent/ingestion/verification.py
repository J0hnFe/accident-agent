"""Verificacion posterior a la carga (tarea 2.6).

Consulta el grafo y compara con los valores de control de la seccion 8 del plan, mas los conteos
de nodos y relaciones del modelo (`docs/modelo_grafo.md`). Los valores de control solo valen
para el archivo conocido: si el SHA-256 cambia, se informan los conteos pero no se exigen.

Tambien comprueba que no haya datos personales: ninguna propiedad con nombre de campo personal
y ningun texto que coincida con los patrones de la regla P6. Nunca imprime valores.
"""

from collections.abc import Mapping
from typing import Any, Final, LiteralString

from neo4j import Driver, RoutingControl
from pydantic import BaseModel, ConfigDict

from accident_agent.domain.privacy import find_personal_data

KNOWN_SHA256: Final = "77e2ca6e3f29c838035009cad0f720ef70bbda8138369b23616800cbd1fd8280"

CONTROL_VALUES: Final[dict[str, Any]] = {
    # Seccion 8 del plan.
    "accidents": 30,
    "active_accidents": 29,
    "annulled": ["SIN-2026-0010 -> SIN-2026-0011"],
    "sin_2025_0007_version_damages": [2, 4100.0],
    "active_with_motorcycle": 7,
    "deaths_active": 18,
    "injured_active": 44,
    "active_with_deaths": 15,
    "active_pichincha": 5,
    "active_guayas": 5,
    "active_e35": 6,
    "active_e35_with_deaths": ["SIN-2025-0001", "SIN-2025-0013", "SIN-2026-0004", "SIN-2026-0007"],
    "reports": 4,
    "personal_data_properties": 0,
    # Modelo de grafo: nodos por etiqueta y relaciones por tipo.
    "nodes": {
        "AccidentType": 5,
        "Accident": 30,
        "Canton": 22,
        "Cause": 10,
        "Dataset": 1,
        "Parish": 30,
        "Person": 80,
        "Province": 17,
        "Report": 4,
        "ReportSection": 9,
        "Road": 20,
        "Vehicle": 49,
        "VehicleType": 10,
    },
    "relationships": {
        "ANALYZES_ROAD": 2,
        "BELONGS_TO": 52,
        "HAS_CAUSE": 30,
        "HAS_SECTION": 9,
        "INVOLVED_IN": 49,
        "OCCURRED_IN": 30,
        "OF_TYPE": 79,
        "ON_ROAD": 30,
        "PARTICIPATED_IN": 80,
        "REPLACED_BY": 1,
        "RODE_IN": 75,
        "SUPERSEDES": 1,
    },
    "fulltext_indexes": ["accident_narratives: ONLINE", "report_texts: ONLINE"],
}

_PERSONAL_KEYS: Final = ["nombre", "cedula", "placa", "placa_vehiculo"]

# Cada consulta devuelve una sola columna "value". Solo lectura y sin datos concatenados.
_QUERIES: Final[dict[str, LiteralString]] = {
    "accidents": "MATCH (a:Accident) RETURN count(a) AS value",
    "active_accidents": "MATCH (a:Accident {is_active: true}) RETURN count(a) AS value",
    "annulled": (
        "MATCH (a:Accident {is_active: false}) OPTIONAL MATCH (a)-[:REPLACED_BY]->(r:Accident)"
        " WITH a, r ORDER BY a.accident_id"
        " RETURN collect(a.accident_id + ' -> ' + coalesce(r.accident_id, 'sin reemplazo'))"
        " AS value"
    ),
    "sin_2025_0007_version_damages": (
        "MATCH (a:Accident {accident_id: 'SIN-2025-0007'})"
        " RETURN [a.version, a.damages_usd] AS value"
    ),
    "active_with_motorcycle": (
        "MATCH (a:Accident {is_active: true})<-[:INVOLVED_IN]-(:Vehicle)"
        "-[:OF_TYPE]->(:VehicleType {code: 'motocicleta'}) RETURN count(DISTINCT a) AS value"
    ),
    "deaths_active": "MATCH (a:Accident {is_active: true}) RETURN sum(a.deaths) AS value",
    "injured_active": "MATCH (a:Accident {is_active: true}) RETURN sum(a.injured) AS value",
    "active_with_deaths": (
        "MATCH (a:Accident {is_active: true}) WHERE a.deaths > 0 RETURN count(a) AS value"
    ),
    "active_pichincha": (
        "MATCH (a:Accident {is_active: true})-[:OCCURRED_IN]->()-[:BELONGS_TO]->()"
        "-[:BELONGS_TO]->(:Province {name: 'Pichincha'}) RETURN count(a) AS value"
    ),
    "active_guayas": (
        "MATCH (a:Accident {is_active: true})-[:OCCURRED_IN]->()-[:BELONGS_TO]->()"
        "-[:BELONGS_TO]->(:Province {name: 'Guayas'}) RETURN count(a) AS value"
    ),
    "active_e35": (
        "MATCH (a:Accident {is_active: true})-[:ON_ROAD]->(:Road {code: 'E35'})"
        " RETURN count(a) AS value"
    ),
    "active_e35_with_deaths": (
        "MATCH (a:Accident {is_active: true})-[:ON_ROAD]->(:Road {code: 'E35'})"
        " WHERE a.deaths > 0 WITH a ORDER BY a.accident_id RETURN collect(a.accident_id) AS value"
    ),
    "reports": "MATCH (r:Report) RETURN count(r) AS value",
    "personal_data_properties": (
        "MATCH (n) UNWIND keys(n) AS key WITH key WHERE key IN $personal_keys"
        " RETURN count(*) AS value"
    ),
}
# Conteos por etiqueta y por tipo de relacion; el mapa se arma en Python.
_NODE_COUNTS: Final = "MATCH (n) RETURN labels(n)[0] AS label, count(*) AS total"
_REL_COUNTS: Final = "MATCH ()-[r]->() RETURN type(r) AS label, count(*) AS total"
_FULLTEXT: Final = (
    "SHOW INDEXES YIELD name, type, state WHERE type = 'FULLTEXT' RETURN name, state ORDER BY name"
)
_STRING_PROPERTIES: Final = (
    "MATCH (n) UNWIND keys(n) AS key WITH n, key, n[key] AS value WHERE value IS :: STRING"
    " RETURN labels(n)[0] AS label, key, value"
)


class VerificationReport(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed: dict[str, Any]
    mismatches: list[str]
    enforced: bool
    personal_data_findings: list[str]

    @property
    def ok(self) -> bool:
        return not self.personal_data_findings and (not self.enforced or not self.mismatches)


def collect(driver: Driver) -> dict[str, Any]:
    observed: dict[str, Any] = {}
    for name, query in _QUERIES.items():
        records, _, _ = driver.execute_query(
            query, personal_keys=_PERSONAL_KEYS, routing_=RoutingControl.READ
        )
        observed[name] = records[0]["value"]
    for name, query in (("nodes", _NODE_COUNTS), ("relationships", _REL_COUNTS)):
        records, _, _ = driver.execute_query(query, routing_=RoutingControl.READ)
        observed[name] = {r["label"]: r["total"] for r in sorted(records, key=lambda r: r["label"])}
    records, _, _ = driver.execute_query(_FULLTEXT, routing_=RoutingControl.READ)
    observed["fulltext_indexes"] = [f"{r['name']}: {r['state']}" for r in records]
    return observed


def personal_data_findings(driver: Driver) -> list[str]:
    """`Etiqueta.propiedad: tipos` de cada texto con un patron P6; nunca el valor."""
    records, _, _ = driver.execute_query(_STRING_PROPERTIES, routing_=RoutingControl.READ)
    findings = {
        f"{r['label']}.{r['key']}: {', '.join(kinds)}"
        for r in records
        if (kinds := find_personal_data(r["value"]))
    }
    return sorted(findings)


def compare(observed: Mapping[str, Any], expected: Mapping[str, Any]) -> list[str]:
    return [
        f"{name}: se obtuvo {observed.get(name)!r}, se esperaba {value!r}"
        for name, value in expected.items()
        if observed.get(name) != value
    ]


def verify(driver: Driver, sha256: str) -> VerificationReport:
    observed = collect(driver)
    return VerificationReport(
        observed=observed,
        mismatches=compare(observed, CONTROL_VALUES),
        enforced=sha256 == KNOWN_SHA256,
        personal_data_findings=personal_data_findings(driver),
    )
