"""API REST con TestClient (tarea 4.9): contenedor con fakes, sin Neo4j ni LLM real."""

from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from accident_agent.bootstrap import Container, build_container
from accident_agent.config import Settings
from accident_agent.core.clock import FixedClock
from accident_agent.core.llm import Message
from accident_agent.graph.repository import RepositoryError
from accident_agent.interfaces.api import create_app
from tests.fakes import (
    FakeAccidentRepository,
    FakeLLMProvider,
    ListLogger,
    answer,
    call,
    context_ids,
)


def _container(tmp_path: Path, steps: list[Any], api_key: str = "") -> Container:
    settings = Settings(
        _env_file=None,
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        openrouter_api_key=SecretStr(api_key),
    )
    return build_container(
        settings,
        llm=FakeLLMProvider(steps),
        repository=FakeAccidentRepository(),
        clock=FixedClock(datetime(2026, 11, 15, 17, 30, tzinfo=UTC)),
        logger=ListLogger(),
    )


@pytest.fixture
def make_client(tmp_path: Path) -> Iterator[Any]:
    clients: list[TestClient] = []

    def make(steps: list[Any], api_key: str = "") -> tuple[TestClient, Container]:
        container = _container(tmp_path, steps, api_key)
        client = TestClient(create_app(lambda: container))
        client.__enter__()
        clients.append(client)
        return client, container

    yield make
    for client in clients:
        client.__exit__(None, None, None)


def test_health(make_client: Any) -> None:
    client, _ = make_client([], api_key="sk-or-v1-secreta")
    response = client.get("/health")
    assert response.json() == {"status": "ok", "neo4j": "ok", "llm_configured": True}
    assert "sk-or" not in response.text


def test_health_degraded_when_the_database_fails(make_client: Any) -> None:
    client, container = make_client([])
    container.repository.fail_with = RepositoryError("unavailable", "x")
    assert client.get("/health").json() == {
        "status": "degraded",
        "neo4j": "unavailable",
        "llm_configured": False,
    }


def test_chat_and_follow_up_in_the_same_session(make_client: Any) -> None:
    def from_context(messages: list[Message]) -> Any:
        return answer("Recuerdo: " + ", ".join(context_ids(messages)))

    client, _ = make_client(
        [
            call(("search_accidents", {"accident_ids": ["SIN-2025-0001"]})),
            answer("Listo."),
            from_context,
        ]
    )
    first = client.post("/chat", json={"message": "Busca SIN-2025-0001"})
    assert first.status_code == 200
    body = first.json()
    assert body["answer"] == "Listo."
    assert body["tools_used"][0]["name"] == "search_accidents"
    assert body["stop_reason"] == "final_answer"
    assert len(body["trace_id"]) == 32
    second = client.post("/chat", json={"session_id": body["session_id"], "message": "y ese?"})
    assert second.json()["answer"] == "Recuerdo: SIN-2025-0001"


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"message": ""}, "message"),
        ({"message": "   "}, "message"),
        ({"message": "x" * 2001}, "message"),
        ({"message": "hola", "session_id": "../etc"}, "session_id"),
        ({}, "message"),
    ],
)
def test_invalid_requests_are_422_without_echo(
    make_client: Any, payload: dict[str, Any], field: str
) -> None:
    client, _ = make_client([])
    response = client.post("/chat", json=payload)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["type"] == "validation"
    assert error["details"][0]["field"] == field
    assert "../etc" not in response.text


def test_report_endpoint(make_client: Any) -> None:
    client, container = make_client(
        [call(("generate_accident_report", {"accident_ids": ["SIN-2025-0001"]})), answer("ok")]
    )
    client.post("/chat", json={"message": "informe"})
    report_id = next(Path(container.settings.reports_dir).glob("RPT-*.md")).stem
    response = client.get(f"/reports/{report_id}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "SIN-2025-0001" in response.text
    assert client.get("/reports/RPT-20990101-000000-abcdef").status_code == 404
    assert client.get("/reports/..%2F..%2Fetc%2Fpasswd").status_code == 404


def test_delete_session(make_client: Any) -> None:
    client, _ = make_client([answer("hola")])
    session = client.post("/chat", json={"message": "hola"}).json()["session_id"]
    assert client.delete(f"/sessions/{session}").status_code == 204
    assert client.delete(f"/sessions/{session}").status_code == 404


def test_openapi_docs(make_client: Any) -> None:
    client, _ = make_client([])
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert {"/chat", "/health", "/reports/{report_id}", "/sessions/{session_id}"} <= set(paths)
