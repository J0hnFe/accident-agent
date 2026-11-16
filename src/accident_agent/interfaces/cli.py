"""CLI de accident-agent (tarea 4.8): chat interactivo, pregunta unica y carga de datos.

Los logs van solo a `logs/agent.jsonl` para no mezclarse con la conversacion.
"""

import json
import uuid
from collections.abc import Callable
from importlib.metadata import version

import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.table import Table

from accident_agent.bootstrap import Container, build_container
from accident_agent.core.orchestrator import MAX_MESSAGE_CHARS, OrchestratorResponse

app = typer.Typer(help="Consultas sobre siniestros de transito del Ecuador.", no_args_is_help=True)
console = Console()

# Las pruebas reemplazan la fabrica para usar dobles sin Neo4j ni LLM.
container_factory: Callable[[], Container] = lambda: build_container(log_to_stdout=False)  # noqa: E731

HELP_TEXT = (
    "Comandos: /historial (conversacion), /reiniciar (nueva sesion), /ayuda, /salir.\n"
    "Ejemplos: 'Cuantos siniestros hubo en Pichincha?', 'Que hora es?', "
    "'Genera el informe de esos accidentes'."
)

VerboseOption = typer.Option(False, "--verbose", "-v", help="Muestra las herramientas usadas.")


# Sin callback, Typer ejecuta un comando unico como si fuera la aplicacion completa.
@app.callback()
def main() -> None:
    """accident-agent."""


@app.command("version")
def show_version() -> None:
    """Muestra la version instalada."""
    typer.echo(version("accident-agent"))


def _print_details(response: OrchestratorResponse) -> None:
    table = Table(title="Herramientas usadas", show_lines=False)
    for column in ("Herramienta", "Parametros", "Estado", "ms"):
        table.add_column(column)
    for tool in response.tools_used:
        params = (
            tool.params
            if isinstance(tool.params, str)
            else json.dumps(tool.params, ensure_ascii=False)
        )
        status = tool.status if tool.error_type is None else f"{tool.status} ({tool.error_type})"
        table.add_row(tool.name, params, status, str(tool.duration_ms))
    if response.tools_used:
        console.print(table)
    console.print(
        f"[dim]trace_id={response.trace_id} iteraciones={response.iterations} "
        f"stop_reason={response.stop_reason}[/dim]"
    )


def _message_error(message: str) -> str | None:
    """Mismas reglas que POST /chat: un mensaje vacio no debe llegar al LLM."""
    if not message.strip():
        return "La pregunta esta vacia."
    if len(message) > MAX_MESSAGE_CHARS:
        return f"La pregunta supera {MAX_MESSAGE_CHARS} caracteres."
    return None


def _answer(
    container: Container, session_id: str, message: str, verbose: bool
) -> OrchestratorResponse:
    with console.status("Consultando..."):
        response = container.orchestrator.handle(session_id, message)
    console.print(Markdown(response.answer))
    if verbose:
        _print_details(response)
    return response


@app.command("ask")
def ask(
    question: str = typer.Argument(..., help="Pregunta en lenguaje natural."),
    verbose: bool = VerboseOption,
) -> None:
    """Responde una sola pregunta y termina."""
    error = _message_error(question)
    if error:
        console.print(error)
        raise typer.Exit(code=2)
    container = container_factory()
    try:
        response = _answer(container, uuid.uuid4().hex, question, verbose)
    finally:
        container.close()
    if response.stop_reason == "llm_error":
        raise typer.Exit(code=1)


@app.command("chat")
def chat(verbose: bool = VerboseOption) -> None:
    """Conversacion interactiva con memoria de la sesion."""
    container = container_factory()
    session_id = uuid.uuid4().hex
    console.print("[bold]accident-agent[/bold]: siniestros de transito del Ecuador.")
    console.print(HELP_TEXT)
    try:
        while True:
            try:
                message = console.input("[bold cyan]> [/bold cyan]").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not message:
                continue
            command = message.lower()
            if command in ("/salir", "/exit", "/quit"):
                break
            if command == "/ayuda":
                console.print(HELP_TEXT)
            elif command == "/reiniciar":
                container.memory.reset(session_id)
                session_id = uuid.uuid4().hex
                console.print("Sesion reiniciada.")
            elif command == "/historial":
                history = container.memory.history(session_id)
                if not history:
                    console.print("Sin mensajes en esta sesion.")
                for item in history:
                    who = "Tu" if item.role == "user" else "Agente"
                    console.print(f"[bold]{who}:[/bold] {item.content}")
            elif error := _message_error(message):
                console.print(error)
            else:
                _answer(container, session_id, message, verbose)
    finally:
        container.close()
    console.print("Hasta luego.")


@app.command("ingest")
def ingest() -> None:
    """Verifica el JSON original y carga Neo4j (lo mismo que el servicio loader)."""
    from accident_agent.config import get_settings
    from accident_agent.ingestion.__main__ import run_load

    raise typer.Exit(code=run_load(get_settings()))
