"""Fabulae CLI application."""

import shutil
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
TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"


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


@app.command(name="narrative-patterns", help="List narrative patterns in a project.")
def narrative_patterns_command(
    path: Annotated[Path, typer.Argument(help="Project directory.")] = DEFAULT_PROJECT_PATH
) -> None:
    """List narrative patterns for a project."""
    try:
        project = load_project(path)
    except (FileNotFoundError, ValidationError, ValueError) as exc:
        typer.echo(f"Load failed: {exc}")
        raise typer.Exit(code=1) from exc

    if not project.narrative_patterns:
        typer.echo("No narrative patterns found.")
        return

    for pattern in project.narrative_patterns:
        typer.echo(f"{pattern.id}: {pattern.name}")


AVAILABLE_FORMATS = ["novel", "novella", "short-story", "micro-prose", "poem"]


@app.command(name="init", help="Initialize a new Fabulae project from a template.")
def init_command(
    path: Annotated[Path, typer.Argument(help="Target project directory.")] = DEFAULT_PROJECT_PATH,
    format_: Annotated[
        str,
        typer.Option(
            "--format",
            "-f",
            help="Literature format (novel, novella, short-story, micro-prose, poem).",
        ),
    ] = "novel",
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite existing files if present."),
    ] = False,
) -> None:
    """Initialize a Fabulae project with starter files."""
    template_map = {
        "novel": "novel",
        "novella": "novella",
        "short-story": "short-story",
        "micro-prose": "micro-prose",
        "poem": "poem",
    }

    if format_ not in template_map:
        available = ", ".join(AVAILABLE_FORMATS)
        raise typer.BadParameter(f"Unknown format: {format_}. Available: {available}")

    template_name = template_map[format_]
    template_path = TEMPLATES_DIR / template_name
    if not template_path.is_dir():
        raise typer.BadParameter(f"Template not found: {template_name}")

    template_files = sorted(template_path.glob("*.yml"))
    if not template_files:
        typer.echo(f"No template files found in {template_path}")
        raise typer.Exit(code=1)

    path.mkdir(parents=True, exist_ok=True)

    conflicts: list[Path] = []
    for template_file in template_files:
        destination = path / template_file.name
        if destination.exists() and not force:
            conflicts.append(destination)

    if conflicts:
        conflict_list = ", ".join(str(conflict) for conflict in conflicts)
        typer.echo(f"Init failed. Files already exist: {conflict_list}")
        raise typer.Exit(code=1)

    created: list[Path] = []
    for template_file in template_files:
        destination = path / template_file.name
        if destination.exists() and destination.is_dir():
            typer.echo(f"Init failed. Destination is a directory: {destination}")
            raise typer.Exit(code=1)
        shutil.copy2(template_file, destination)
        created.append(destination)

    typer.echo(f"Initialized Fabulae project in {path} (format: {format_})")
    for created_file in created:
        typer.echo(f"  {created_file.name}")


def main() -> None:
    """Entry point for the fabulae CLI."""
    app()


if __name__ == "__main__":
    main()
