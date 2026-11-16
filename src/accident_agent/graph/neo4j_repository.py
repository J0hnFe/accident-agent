"""Adaptador Neo4j del puerto `AccidentRepository` (tarea 3.2).

- Solo transacciones de lectura (`RoutingControl.READ`), con timeout por transaccion.
- Solo plantillas de `queries.py`; el texto libre se escapa para la sintaxis de Lucene.
- Los errores del driver se traducen a `RepositoryError` para que la herramienta los informe.
"""

import re
from collections.abc import Mapping, Sequence
from typing import Any, Final, LiteralString

from neo4j import Driver, Query, RoutingControl
from neo4j.exceptions import (
    ClientError,
    DriverError,
    Neo4jError,
    ServiceUnavailable,
    SessionExpired,
)

from accident_agent.graph import queries
from accident_agent.graph.repository import (
    AccidentFilters,
    AccidentView,
    DatasetSummary,
    GroupBy,
    ReportHit,
    RepositoryError,
    SearchPage,
    StatsRow,
)

# Caracteres con significado en la sintaxis de consultas de Lucene.
_LUCENE_SPECIAL: Final = re.compile(r'([+\-!(){}\[\]^"~*?:\\/&|])')


def lucene_query(text: str) -> str:
    """Texto ya plegado como consulta literal: sin operadores ni comodines del usuario."""
    return _LUCENE_SPECIAL.sub(r"\\\1", text.lower())


def _native(value: Any) -> Any:
    if hasattr(value, "to_native"):
        return value.to_native()
    if isinstance(value, Mapping):
        return {k: _native(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_native(v) for v in value]
    return value


class Neo4jAccidentRepository:
    def __init__(self, driver: Driver, *, timeout_seconds: float = 10.0) -> None:
        self._driver = driver
        self._timeout = timeout_seconds

    def _read(self, cypher: LiteralString, **params: Any) -> list[dict[str, Any]]:
        try:
            records, _, _ = self._driver.execute_query(
                Query(cypher, timeout=self._timeout), params, routing_=RoutingControl.READ
            )
        except ClientError as exc:
            if exc.code and "TransactionTimedOut" in exc.code:
                raise RepositoryError("timeout", "la consulta supero el tiempo limite") from exc
            raise
        except (ServiceUnavailable, SessionExpired) as exc:
            raise RepositoryError("unavailable", "la base de datos no esta disponible") from exc
        except (DriverError, Neo4jError) as exc:
            raise RepositoryError("unavailable", "la base de datos no respondio") from exc
        return [_native(record.data()) for record in records]

    def _filter_params(self, filters: AccidentFilters) -> dict[str, Any]:
        params = filters.model_dump(mode="json", exclude={"text"})
        params["date_from"] = filters.date_from
        params["date_to"] = filters.date_to
        params["text_scores"] = self._text_scores(filters.text) if filters.text else None
        return params

    def _text_scores(self, text: str) -> dict[str, float]:
        rows = self._read(queries.FULLTEXT_ACCIDENTS, query=lucene_query(text))
        return {row["accident_id"]: row["score"] for row in rows}

    def search(self, filters: AccidentFilters, limit: int) -> SearchPage:
        rows = self._read(queries.SEARCH_IDS, limit=limit, **self._filter_params(filters))
        row = rows[0]
        return SearchPage(total_found=row["total"], accidents=self.get_by_ids(row["page"]))

    def get_by_ids(self, accident_ids: Sequence[str]) -> list[AccidentView]:
        if not accident_ids:
            return []
        rows = self._read(queries.ACCIDENT_DETAILS, ids=list(accident_ids))
        found = {r["accident"]["accident_id"]: AccidentView(**r["accident"]) for r in rows}
        return [found[i] for i in accident_ids if i in found]

    def stats(self, filters: AccidentFilters, group_by: GroupBy) -> list[StatsRow]:
        rows = self._read(queries.STATS_QUERIES[group_by], **self._filter_params(filters))
        return [StatsRow(**row) for row in rows]

    def search_reports(
        self, text: str | None, road_code: str | None, limit: int
    ) -> list[ReportHit]:
        if text:
            rows = self._read(
                queries.REPORTS_BY_TEXT, query=lucene_query(text), road_code=road_code, limit=limit
            )
        else:
            rows = self._read(queries.REPORTS_ALL, road_code=road_code, limit=limit)
        return [ReportHit(**row) for row in rows]

    def dataset_info(self) -> DatasetSummary:
        rows = self._read(queries.DATASET_INFO)
        if not rows:
            raise RepositoryError("unavailable", "la base no tiene datos cargados")
        return DatasetSummary(**rows[0])
