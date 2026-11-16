from typing import Any

import pytest
from fastapi.testclient import TestClient
from neo4j.exceptions import ServiceUnavailable
from pydantic import SecretStr

from accident_agent.config import Settings
from accident_agent.interfaces.api import create_app


class FakeDriver:
    def __init__(self, available: bool) -> None:
        self.available = available
        self.closed = False

    def verify_connectivity(self) -> None:
        if not self.available:
            raise ServiceUnavailable("sin conexion")

    def close(self) -> None:
        self.closed = True


def _client(available: bool, api_key: str = "") -> tuple[TestClient, FakeDriver]:
    driver = FakeDriver(available)
    settings = Settings(_env_file=None, openrouter_api_key=SecretStr(api_key))
    app = create_app(settings, driver)  # type: ignore[arg-type]
    return TestClient(app), driver


@pytest.mark.parametrize(
    ("available", "api_key", "expected"),
    [
        (True, "sk-or-v1-secreta", {"status": "ok", "neo4j": "ok", "llm_configured": True}),
        (False, "", {"status": "degraded", "neo4j": "unavailable", "llm_configured": False}),
    ],
)
def test_health(available: bool, api_key: str, expected: dict[str, Any]) -> None:
    client, _ = _client(available, api_key)
    with client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == expected
    assert "sk-or" not in response.text


def test_injected_driver_is_not_closed_by_the_app() -> None:
    client, driver = _client(True)
    with client:
        client.get("/health")
    assert driver.closed is False
