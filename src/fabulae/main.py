"""Fabulae CLI application."""

from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from fabulae.models import load_project
from fabulae.version_cli import version_command

app = typer.Typer(
    help="Fabulae — your CLI application.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@app.callback(invoke_without_command=True)
def app_callback(ctx: typer.Context) -> None:
    """Root callback invoked when no subcommand is provided."""
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())


app.command(name="version", help="Display the current version.")(version_command)


DEFAULT_PROJECT_PATH = Path(".")


@app.command(name="validate", help="Validate a Fabulae project directory.")
def validate_command(
    path: Annotated[Path, typer.Argument(help="Project directory.")] = DEFAULT_PROJECT_PATH
) -> None:
    """Validate a Fabulae project and report errors."""
    try:
        load_project(path)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        typer.echo(f"Validation failed: {exc}")
        raise typer.Exit(code=1) from exc
    typer.echo("Validation OK.")


def main() -> None:
    """Entry point for the fabulae CLI."""
    app()


if __name__ == "__main__":
    main()
