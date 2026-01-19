"""Stanza CRUD commands for Fabulae projects."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.prompts import build_stanza_suggest_prompt
from fabulae.features.entities.schemas import StanzaSuggestion
from fabulae.features.entities.service import suggest_entity_sync
from fabulae.features.entities.utils import (
    confirm,
    find_stanza_by_id,
    get_all_entity_ids,
    output_list_as_json,
    output_list_as_yaml,
    require_poem_format,
    resolve_idea_input,
    validate_entity_id,
    validate_output_format,
)
from fabulae.llm import resolve_config
from fabulae.models import Stanza, load_project, save_project

stanza_app = typer.Typer(help="Manage stanzas in a Fabulae project.")
console = Console()


@stanza_app.command("add")
def add(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    id: Annotated[str, typer.Option("--id", help="Stanza ID (lowercase-with-hyphens).")],
    line: Annotated[list[str] | None, typer.Option("--line", "-l", help="Line of poetry (repeatable).")] = None,
    meter: Annotated[str | None, typer.Option("--meter", help="Meter pattern (e.g., 'iambic pentameter').")] = None,
    rhyme_scheme: Annotated[str | None, typer.Option("--rhyme-scheme", help="Rhyme scheme (e.g., 'ABAB').")] = None,
) -> None:
    """Add a new stanza to the project.

    Example:
        fabulae stanza add ./my-poem --id stanza-03 --line "A verse of gold." --line "In autumn's hold."
    """
    # Validate ID format before loading project
    validate_entity_id(id)

    project = load_project(project_dir)
    require_poem_format(project, "stanza add")

    # Check for duplicate ID
    existing_ids = get_all_entity_ids(project)
    if id in existing_ids:
        typer.echo(f"Error: ID '{id}' already exists in project.", err=True)
        raise typer.Exit(code=1)

    stanza = Stanza(
        id=id,
        lines=line or [],
        meter=meter,
        rhyme_scheme=rhyme_scheme,
    )
    project.plot.stanzas.append(stanza)
    save_project(project, project_dir)
    typer.echo(f"Added stanza: {id}")


@stanza_app.command("suggest")
def suggest(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path.")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    base_url: str | None = base_url_option(),
    api_key: str | None = api_key_option(),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Add without confirmation.")] = False,
) -> None:
    """Suggest a new stanza based on project context.

    Example:
        fabulae stanza suggest ./my-poem --idea "a verse about the sea"
    """
    project = load_project(project_dir)
    require_poem_format(project, "stanza suggest")

    # Resolve idea input
    guidance = resolve_idea_input(idea) if idea else None

    # Build prompt and get suggestion
    config = resolve_config(model, base_url, api_key, temperature, None)
    prompt = build_stanza_suggest_prompt(project, guidance)

    typer.echo("Generating stanza suggestion...")
    suggestion = suggest_entity_sync(StanzaSuggestion, prompt, config)

    # Display suggestion
    console.print("\n[bold]Suggested stanza:[/bold]")
    console.print(f"  ID: {suggestion.id}")
    if suggestion.lines:
        console.print("  Lines:")
        for ln in suggestion.lines[:4]:
            console.print(f'    "{ln}"')
        if len(suggestion.lines) > 4:
            console.print(f"    ... and {len(suggestion.lines) - 4} more lines")
    if suggestion.meter:
        console.print(f"  Meter: {suggestion.meter}")
    if suggestion.rhyme_scheme:
        console.print(f"  Rhyme scheme: {suggestion.rhyme_scheme}")
    console.print()

    # Confirm and add
    if yes or confirm("Add this stanza?"):
        # Check for duplicate ID
        existing_ids = get_all_entity_ids(project)
        if suggestion.id in existing_ids:
            typer.echo(
                f"Error: ID '{suggestion.id}' already exists. Use 'stanza add' manually.",
                err=True,
            )
            raise typer.Exit(code=1)

        stanza = Stanza(
            id=suggestion.id,
            lines=suggestion.lines,
            meter=suggestion.meter,
            rhyme_scheme=suggestion.rhyme_scheme,
        )
        project.plot.stanzas.append(stanza)
        save_project(project, project_dir)
        typer.echo(f"Added stanza: {suggestion.id}")
    else:
        typer.echo("Stanza not added.")


@stanza_app.command("list")
def list_stanzas(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, yaml.")] = "table",
) -> None:
    """List all stanzas in the project.

    Example:
        fabulae stanza list ./my-poem --format json
    """
    project = load_project(project_dir)
    require_poem_format(project, "stanza list")

    if not project.plot.stanzas:
        typer.echo("No stanzas in project.")
        return

    validate_output_format(format)

    if format == "table":
        table = Table(title="Stanzas")
        table.add_column("ID", style="cyan")
        table.add_column("Lines")
        table.add_column("Meter")
        table.add_column("Rhyme")

        for s in project.plot.stanzas:
            first_line = s.lines[0] if s.lines else "(empty)"
            line_preview = (first_line[:30] + "...") if len(first_line) > 30 else first_line
            if len(s.lines) > 1:
                line_preview += f" (+{len(s.lines) - 1} more)"
            table.add_row(s.id, line_preview, s.meter or "", s.rhyme_scheme or "")

        console.print(table)
    elif format == "json":
        output_list_as_json(project.plot.stanzas)
    elif format == "yaml":
        output_list_as_yaml(project.plot.stanzas)


@stanza_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    stanza_id: Annotated[str, typer.Argument(help="Stanza ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
) -> None:
    """Remove a stanza from the project.

    Example:
        fabulae stanza remove ./my-poem stanza-03
    """
    project = load_project(project_dir)
    require_poem_format(project, "stanza remove")

    stanza = find_stanza_by_id(project, stanza_id)
    if not stanza:
        typer.echo(f"Error: Stanza '{stanza_id}' not found.", err=True)
        raise typer.Exit(code=1)

    if not force and not confirm(f"Remove stanza '{stanza_id}'?"):
        typer.echo("Stanza not removed.")
        return

    project.plot.stanzas = [s for s in project.plot.stanzas if s.id != stanza_id]
    save_project(project, project_dir)
    typer.echo(f"Removed stanza: {stanza_id}")


@stanza_app.command("edit")
def edit(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    stanza_id: Annotated[str, typer.Argument(help="Stanza ID to edit.")],
    add_line: Annotated[list[str] | None, typer.Option("--add-line", help="Add a line to the stanza.")] = None,
    remove_line: Annotated[
        list[int] | None, typer.Option("--remove-line", help="Remove line by index (0-based).")
    ] = None,
    meter: Annotated[str | None, typer.Option("--meter", help="New meter.")] = None,
    rhyme_scheme: Annotated[str | None, typer.Option("--rhyme-scheme", help="New rhyme scheme.")] = None,
) -> None:
    """Edit an existing stanza.

    Example:
        fabulae stanza edit ./my-poem stanza-01 --add-line "A new line of verse."
    """
    project = load_project(project_dir)
    require_poem_format(project, "stanza edit")

    stanza = find_stanza_by_id(project, stanza_id)
    if not stanza:
        typer.echo(f"Error: Stanza '{stanza_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Handle line removals first (by index, in reverse order to preserve indices)
    if remove_line:
        indices_to_remove = sorted(remove_line, reverse=True)
        for idx in indices_to_remove:
            if 0 <= idx < len(stanza.lines):
                stanza.lines.pop(idx)
            else:
                typer.echo(f"Warning: Line index {idx} out of range, skipping.", err=True)

    # Handle line additions
    if add_line:
        for ln in add_line:
            stanza.lines.append(ln)

    # Update optional fields
    if meter is not None:
        stanza.meter = meter if meter else None
    if rhyme_scheme is not None:
        stanza.rhyme_scheme = rhyme_scheme if rhyme_scheme else None

    save_project(project, project_dir)
    typer.echo(f"Updated stanza: {stanza_id}")
