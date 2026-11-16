from typing import Any

import pytest
from neo4j import GraphDatabase
from neo4j.exceptions import ClientError, Neo4jError, ServiceUnavailable

from accident_agent.graph.neo4j_repository import Neo4jAccidentRepository, lucene_query
from accident_agent.graph.repository import AccidentFilters, RepositoryError


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("neblina", "neblina"),
        ("choque: (frontal)", "choque\\: \\(frontal\\)"),
        ('"bus"* AND moto~', '\\"bus\\"\\* and moto\\~'),
        ("a+b-c/d", "a\\+b\\-c\\/d"),
    ],
)
def test_lucene_query_escapes_operators(text: str, expected: str) -> None:
    assert lucene_query(text) == expected


class RaisingDriver:
    def __init__(self, error: Exception) -> None:
        self.error = error

    def execute_query(self, *args: Any, **kwargs: Any) -> Any:
        raise self.error


def _timeout_error() -> Neo4jError:
    return Neo4jError._hydrate_neo4j(
        code="Neo.ClientError.Transaction.TransactionTimedOut", message="timeout"
    )


@pytest.mark.parametrize(
    ("error", "kind"),
    [(_timeout_error(), "timeout"), (ServiceUnavailable("caida"), "unavailable")],
)
def test_driver_errors_are_translated(error: Exception, kind: str) -> None:
    repo = Neo4jAccidentRepository(RaisingDriver(error))  # type: ignore[arg-type]
    with pytest.raises(RepositoryError) as info:
        repo.search(AccidentFilters(), limit=5)
    assert info.value.kind == kind


def test_query_errors_are_not_hidden() -> None:
    syntax = Neo4jError._hydrate_neo4j(code="Neo.ClientError.Statement.SyntaxError", message="x")
    repo = Neo4jAccidentRepository(RaisingDriver(syntax))  # type: ignore[arg-type]
    with pytest.raises(ClientError):
        repo.search(AccidentFilters(), limit=5)


def test_unreachable_server_is_unavailable() -> None:
    with GraphDatabase.driver(
        "bolt://127.0.0.1:1", auth=("neo4j", "x"), max_transaction_retry_time=0
    ) as driver:
        repo = Neo4jAccidentRepository(driver)
        with pytest.raises(RepositoryError) as info:
            repo.dataset_info()
    assert info.value.kind == "unavailable"
