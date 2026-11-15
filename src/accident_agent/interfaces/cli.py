"""CLI de accident-agent. Los comandos chat, ask e ingest se agregan en la tarea 4.8."""

from importlib.metadata import version

import typer

app = typer.Typer(help="Consultas sobre siniestros de transito del Ecuador.", no_args_is_help=True)


# Sin callback, Typer ejecuta un comando unico como si fuera la aplicacion completa.
@app.callback()
def main() -> None:
    """accident-agent."""


@app.command("version")
def show_version() -> None:
    """Muestra la version instalada."""
    typer.echo(version("accident-agent"))
