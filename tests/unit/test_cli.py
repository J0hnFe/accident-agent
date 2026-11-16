"""CLI con CliRunner (tarea 4.8): contenedor con fakes, sin Neo4j ni LLM real."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from accident_agent.bootstrap import Container, build_container
from accident_agent.config import Settings
from accident_agent.core.clock import FixedClock
from accident_agent.core.llm import RateLimitError
from accident_agent.interfaces import cli
from tests.fakes import FakeAccidentRepository, FakeLLMProvider, ListLogger, answer, call

runner = CliRunner()


@pytest.fixture
def use_steps(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    def configure(steps: list[Any]) -> None:
        def factory() -> Container:
            settings = Settings(
                _env_file=None, reports_dir=tmp_path / "reports", logs_dir=tmp_path / "logs"
            )
            return build_container(
                settings,
                llm=FakeLLMProvider(steps),
                repository=FakeAccidentRepository(),
                clock=FixedClock(datetime(2026, 11, 15, 17, 30, tzinfo=UTC)),
                logger=ListLogger(),
            )

        monkeypatch.setattr(cli, "container_factory", factory)

    return configure


def test_version() -> None:
    result = runner.invoke(cli.app, ["version"])
    assert result.exit_code == 0
    assert result.output.strip() == "0.1.0"


def test_ask_with_verbose_table(use_steps: Any) -> None:
    use_steps(
        [call(("search_accidents", {"province": "Guayas"})), answer("Hubo **5** siniestros.")]
    )
    result = runner.invoke(cli.app, ["ask", "Siniestros en Guayas?", "--verbose"])
    assert result.exit_code == 0
    assert "Hubo 5 siniestros." in result.output
    assert "search_accidents" in result.output
    assert '"province": "Guayas"' in result.output
    assert "stop_reason=final_answer" in result.output


def test_ask_exits_with_error_when_the_provider_fails(use_steps: Any) -> None:
    use_steps([RateLimitError("429")])
    result = runner.invoke(cli.app, ["ask", "hola"])
    assert result.exit_code == 1
    assert "limite de uso" in result.output


def test_chat_session_commands(use_steps: Any) -> None:
    use_steps([answer("Hola, soy el agente."), answer("Nueva sesion.")])
    commands = "hola\n/historial\n/reiniciar\n/historial\notra\n/ayuda\n/salir\n"
    result = runner.invoke(cli.app, ["chat"], input=commands)
    assert result.exit_code == 0
    output = result.output
    assert "Hola, soy el agente." in output
    assert "Tu: hola" in output
    assert "Sesion reiniciada." in output
    assert "Sin mensajes en esta sesion." in output
    assert "Nueva sesion." in output
    assert "/historial" in output
    assert output.rstrip().endswith("Hasta luego.")


def test_chat_ends_on_end_of_input(use_steps: Any) -> None:
    use_steps([])
    result = runner.invoke(cli.app, ["chat"], input="")
    assert result.exit_code == 0
    assert "Hasta luego." in result.output
