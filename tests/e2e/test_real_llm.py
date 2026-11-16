"""Prueba con el LLM real de OpenRouter y Neo4j (marca e2e, fuera de la suite por defecto).

Consume cuota del plan gratuito (unas 2 solicitudes). Ejecutar a mano:
    docker compose up -d neo4j && uv run pytest -m e2e
"""

import pytest
from neo4j.exceptions import ServiceUnavailable

from accident_agent.bootstrap import build_container
from accident_agent.config import get_settings
from tests.fakes import ListLogger

pytestmark = pytest.mark.e2e


def test_real_llm_answers_from_the_graph() -> None:
    settings = get_settings()
    if not settings.openrouter_api_key.get_secret_value():
        pytest.skip("falta OPENROUTER_API_KEY")
    container = build_container(settings, logger=ListLogger())
    try:
        try:
            container.repository.dataset_info()
        except Exception as exc:
            if isinstance(exc.__cause__, ServiceUnavailable) or "disponible" in str(exc):
                pytest.skip("Neo4j no esta disponible")
            raise
        response = container.orchestrator.handle("e2e", "Cuantos siniestros hubo en Pichincha?")
    finally:
        container.close()
    if response.stop_reason == "llm_error":
        pytest.skip(f"proveedor no disponible: {response.answer}")
    assert "search_accidents" in [t.name for t in response.tools_used]
    assert "5" in response.answer
