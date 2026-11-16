"""API REST. Por ahora solo `GET /health` (servicio `api` de compose, tarea 2.5).

`POST /chat` y el resto del contrato 7.7 del plan se agregan en la tarea 4.9.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version
from typing import Literal

from fastapi import FastAPI, Request
from neo4j import Driver
from neo4j.exceptions import DriverError, Neo4jError
from pydantic import BaseModel

from accident_agent.config import Settings, get_settings
from accident_agent.graph.connection import create_driver


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    neo4j: Literal["ok", "unavailable"]
    llm_configured: bool


def create_app(settings: Settings | None = None, driver: Driver | None = None) -> FastAPI:
    """El driver se puede inyectar (pruebas); si no, se crea y se cierra con la aplicacion."""
    config = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.driver = driver or create_driver(config)
        try:
            yield
        finally:
            if driver is None:
                app.state.driver.close()

    app = FastAPI(
        title="accident-agent",
        description="Consultas sobre siniestros de transito del Ecuador.",
        version=version("accident-agent"),
        lifespan=lifespan,
    )

    @app.get("/health")
    def health(request: Request) -> HealthResponse:
        try:
            request.app.state.driver.verify_connectivity()
            neo4j: Literal["ok", "unavailable"] = "ok"
        except (DriverError, Neo4jError):
            neo4j = "unavailable"
        return HealthResponse(
            status="ok" if neo4j == "ok" else "degraded",
            neo4j=neo4j,
            llm_configured=bool(config.openrouter_api_key.get_secret_value()),
        )

    return app


app = create_app()
