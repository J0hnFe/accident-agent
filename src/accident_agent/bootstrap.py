"""Raiz de composicion (tarea 4.7): unico lugar donde se crean y conectan los adaptadores.

El nucleo depende de puertos (LLMProvider, AccidentRepository, Clock, Tracer, ConversationMemory).
Aqui se eligen las implementaciones; las pruebas pasan dobles por parametro.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neo4j import Driver

from accident_agent.config import Settings, get_settings
from accident_agent.core.clock import Clock, SystemClock
from accident_agent.core.llm import LLMProvider
from accident_agent.core.memory import InMemoryConversationMemory
from accident_agent.core.orchestrator import Orchestrator, OrchestratorLimits
from accident_agent.core.registry import ToolRegistry
from accident_agent.core.tracer import NoopTracer, SafeTracer, Tracer
from accident_agent.graph.connection import create_driver
from accident_agent.graph.neo4j_repository import Neo4jAccidentRepository
from accident_agent.graph.repository import AccidentRepository
from accident_agent.observability.events import EventLogger
from accident_agent.observability.logging import configure_logging, get_logger
from accident_agent.providers.openrouter import DEFAULT_MODELS, OpenRouterProvider
from accident_agent.tools.accident_report import GenerateReportTool
from accident_agent.tools.accident_search import SearchAccidentsTool
from accident_agent.tools.current_time import CurrentTimeTool


@dataclass
class Container:
    settings: Settings
    orchestrator: Orchestrator
    registry: ToolRegistry
    repository: AccidentRepository
    memory: InMemoryConversationMemory
    tracer: Tracer
    logger: EventLogger
    driver: Driver | None = None

    def close(self) -> None:
        self.orchestrator.close()
        self.tracer.flush()
        if self.driver is not None:
            self.driver.close()


def build_tracer(settings: Settings, logger: EventLogger) -> Tracer:
    """Langfuse solo si estan las tres variables; sin ellas no se intenta ninguna conexion."""
    public_key = settings.langfuse_public_key.get_secret_value()
    secret_key = settings.langfuse_secret_key.get_secret_value()
    if not (public_key and secret_key and settings.langfuse_base_url):
        return NoopTracer()
    from accident_agent.observability.langfuse_tracer import LangfuseTracer

    try:
        tracer = LangfuseTracer(
            public_key=public_key, secret_key=secret_key, base_url=settings.langfuse_base_url
        )
    except Exception as exc:
        logger.warning("tracer_error", operation="init", error=type(exc).__name__)
        return NoopTracer()
    return SafeTracer(tracer, logger)


def build_registry(
    settings: Settings, repository: AccidentRepository, clock: Clock
) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        CurrentTimeTool(
            clock,
            default_timezone=settings.default_timezone,
            timeout_seconds=settings.tool_timeout_time_seconds,
        )
    )
    registry.register(
        SearchAccidentsTool(repository, timeout_seconds=settings.tool_timeout_search_seconds)
    )
    registry.register(
        GenerateReportTool(
            repository,
            clock,
            reports_dir=Path(settings.reports_dir),
            timezone=settings.default_timezone,
            timeout_seconds=settings.tool_timeout_report_seconds,
        )
    )
    return registry


def build_container(
    settings: Settings | None = None,
    *,
    llm: LLMProvider | None = None,
    repository: AccidentRepository | None = None,
    clock: Clock | None = None,
    tracer: Tracer | None = None,
    logger: EventLogger | None = None,
    log_to_stdout: bool = True,
) -> Container:
    config = settings or get_settings()
    if logger is None:
        configure_logging(config.log_level, Path(config.logs_dir), stdout=log_to_stdout)
        logger = get_logger()

    driver: Driver | None = None
    if repository is None:
        driver = create_driver(config)
        repository = Neo4jAccidentRepository(
            driver, timeout_seconds=config.tool_timeout_search_seconds
        )

    registry = build_registry(config, repository, clock or SystemClock())
    provider: Any = llm or OpenRouterProvider(
        api_key=config.openrouter_api_key.get_secret_value(),
        models=config.openrouter_models or list(DEFAULT_MODELS),
        timeout_seconds=config.llm_timeout_seconds,
    )
    chosen_tracer = tracer or build_tracer(config, logger)
    memory = InMemoryConversationMemory(max_turns=config.memory_max_turns)
    orchestrator = Orchestrator(
        llm=provider,
        registry=registry,
        memory=memory,
        logger=logger,
        tracer=chosen_tracer,
        limits=OrchestratorLimits(
            max_iterations=config.orch_max_iterations,
            max_tool_calls_per_iteration=config.orch_max_tool_calls_per_iteration,
        ),
    )
    return Container(
        settings=config,
        orchestrator=orchestrator,
        registry=registry,
        repository=repository,
        memory=memory,
        tracer=chosen_tracer,
        logger=logger,
        driver=driver,
    )
