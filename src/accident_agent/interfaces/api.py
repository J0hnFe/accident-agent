"""API REST (seccion 7.7 del plan, tarea 4.9). Documentacion OpenAPI en /docs.

Un solo proceso de uvicorn: la memoria de sesiones vive en el proceso (limitacion documentada).
"""

import re
import uuid
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from importlib.metadata import version
from pathlib import Path
from typing import Any, Final, Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from accident_agent.bootstrap import Container, build_container
from accident_agent.core.orchestrator import StopReason, ToolUse
from accident_agent.graph.repository import RepositoryError

REPORT_ID: Final = re.compile(r"^RPT-\d{8}-\d{6}-[0-9a-f]{6}$")
SESSION_ID_PATTERN: Final = r"^[A-Za-z0-9_-]{1,64}$"


class ChatRequest(BaseModel):
    session_id: str | None = Field(
        default=None,
        pattern=SESSION_ID_PATTERN,
        description="Sesion para continuar una conversacion; si se omite se crea una nueva.",
    )
    message: str = Field(min_length=1, max_length=2000, description="Pregunta del usuario.")

    @field_validator("message")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("el mensaje esta vacio")
        return value


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    tools_used: list[ToolUse]
    trace_id: str
    stop_reason: StopReason


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    neo4j: Literal["ok", "unavailable"]
    llm_configured: bool


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorInfo(BaseModel):
    type: str
    message: str
    details: list[ErrorDetail] | None = None


class ErrorResponse(BaseModel):
    """Formato de todos los errores de la API (422, 404 y 500)."""

    error: ErrorInfo


# Se declaran en cada ruta para que el OpenAPI publique este formato y no el de FastAPI
# ({"detail": [...]}), que la API no devuelve.
Responses = dict[int | str, dict[str, Any]]

_INVALID: Final[Responses] = {422: {"model": ErrorResponse, "description": "Solicitud no valida"}}
_FAILED: Final[Responses] = {500: {"model": ErrorResponse, "description": "Error interno"}}
_NOT_FOUND: Final[Responses] = {404: {"model": ErrorResponse, "description": "No encontrado"}}


def _json_error(description: str) -> dict[str, Any]:
    # En rutas que responden texto, FastAPI publicaria el modelo bajo text/plain.
    schema = {"$ref": "#/components/schemas/ErrorResponse"}
    return {"description": description, "content": {"application/json": {"schema": schema}}}


def _error(status: int, error_type: str, message: str, **extra: object) -> JSONResponse:
    return JSONResponse(
        status_code=status, content={"error": {"type": error_type, "message": message, **extra}}
    )


def create_app(container_factory: Callable[[], Container] | None = None) -> FastAPI:
    """El contenedor se crea al arrancar (o lo inyectan las pruebas) y se cierra al apagar."""
    factory = container_factory or build_container

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = factory()
        try:
            yield
        finally:
            app.state.container.close()

    app = FastAPI(
        title="accident-agent",
        description=(
            "Consultas en lenguaje natural sobre siniestros de transito del Ecuador "
            "(RAG sobre Neo4j, hora actual e informes)."
        ),
        version=version("accident-agent"),
        lifespan=lifespan,
    )

    def container(request: Request) -> Container:
        current: Container = request.app.state.container
        return current

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Solo campo y motivo: no se devuelve lo que envio el cliente.
        details = [
            {"field": ".".join(str(p) for p in e["loc"] if p != "body"), "message": e["msg"]}
            for e in exc.errors()
        ]
        return _error(422, "validation", "solicitud no valida", details=details)

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        error_type = "not_found" if exc.status_code == 404 else "http"
        # "Not Found" es el detalle por defecto de Starlette para rutas inexistentes.
        message = "recurso no encontrado" if exc.detail == "Not Found" else str(exc.detail)
        return _error(exc.status_code, error_type, message)

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        container(request).logger.warning("api_error", error=type(exc).__name__)
        return _error(500, "internal", "error interno; intenta de nuevo")

    @app.post("/chat", responses={**_INVALID, **_FAILED})
    def chat(body: ChatRequest, request: Request) -> ChatResponse:
        session_id = body.session_id or uuid.uuid4().hex
        response = container(request).orchestrator.handle(session_id, body.message)
        return ChatResponse(
            session_id=response.session_id,
            answer=response.answer,
            tools_used=response.tools_used,
            trace_id=response.trace_id,
            stop_reason=response.stop_reason,
        )

    @app.get("/health", responses=_FAILED)
    def health(request: Request) -> HealthResponse:
        current = container(request)
        try:
            current.repository.dataset_info()
            neo4j: Literal["ok", "unavailable"] = "ok"
        except RepositoryError:
            neo4j = "unavailable"
        return HealthResponse(
            status="ok" if neo4j == "ok" else "degraded",
            neo4j=neo4j,
            llm_configured=bool(current.settings.openrouter_api_key.get_secret_value()),
        )

    @app.get(
        "/reports/{report_id}",
        response_class=PlainTextResponse,
        responses={404: _json_error("No encontrado"), 422: _json_error("Solicitud no valida")},
    )
    def report(report_id: str, request: Request) -> PlainTextResponse:
        if not REPORT_ID.match(report_id):
            raise HTTPException(status_code=404, detail="informe no encontrado")
        path = Path(container(request).settings.reports_dir) / f"{report_id}.md"
        if not path.is_file():
            raise HTTPException(status_code=404, detail="informe no encontrado")
        return PlainTextResponse(path.read_text(encoding="utf-8"), media_type="text/markdown")

    @app.delete("/sessions/{session_id}", status_code=204, responses={**_NOT_FOUND, **_INVALID})
    def delete_session(session_id: str, request: Request) -> Response:
        if not re.match(SESSION_ID_PATTERN, session_id) or not container(request).memory.reset(
            session_id
        ):
            raise HTTPException(status_code=404, detail="sesion no encontrada")
        return Response(status_code=204)

    return app


app = create_app()
