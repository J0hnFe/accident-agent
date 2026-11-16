from pathlib import Path

from pydantic import SecretStr

from accident_agent.bootstrap import build_container, build_tracer
from accident_agent.config import Settings
from accident_agent.core.tracer import NoopTracer, SafeTracer
from accident_agent.providers.openrouter import DEFAULT_MODELS, OpenRouterProvider
from tests.fakes import FakeAccidentRepository, ListLogger


def _settings(tmp_path: Path, **overrides: object) -> Settings:
    return Settings(
        _env_file=None,
        reports_dir=tmp_path / "reports",
        logs_dir=tmp_path / "logs",
        **overrides,  # type: ignore[arg-type]
    )


def test_container_wires_the_three_tools(tmp_path: Path) -> None:
    container = build_container(
        _settings(tmp_path), repository=FakeAccidentRepository(), logger=ListLogger()
    )
    assert container.registry.names == [
        "get_current_time",
        "search_accidents",
        "generate_accident_report",
    ]
    assert container.driver is None
    assert isinstance(container.tracer, NoopTracer)
    container.close()


def test_default_models_when_not_configured(tmp_path: Path) -> None:
    container = build_container(
        _settings(tmp_path), repository=FakeAccidentRepository(), logger=ListLogger()
    )
    provider = container.orchestrator._llm
    assert isinstance(provider, OpenRouterProvider)
    assert provider.models == list(DEFAULT_MODELS)
    container.close()


def test_tracer_without_keys_is_noop(tmp_path: Path) -> None:
    settings = _settings(tmp_path, langfuse_base_url="https://us.cloud.langfuse.com")
    assert isinstance(build_tracer(settings, ListLogger()), NoopTracer)


def test_tracer_with_keys_is_langfuse_behind_safe_tracer(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        langfuse_public_key=SecretStr("pk-lf-bootstrap-test"),
        langfuse_secret_key=SecretStr("sk-lf-bootstrap-test"),
        langfuse_base_url="http://127.0.0.1:1",
    )
    tracer = build_tracer(settings, ListLogger())
    assert isinstance(tracer, SafeTracer)
    tracer.flush()
