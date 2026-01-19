"""Fragment CRUD commands for Fabulae projects."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.prompts import build_fragment_suggest_prompt
from fabulae.features.entities.schemas import FragmentSuggestion
from fabulae.features.entities.service import suggest_entity_sync
from fabulae.features.entities.utils import (
    confirm,
    find_fragment_by_id,
    get_all_entity_ids,
    output_list_as_json,
    output_list_as_yaml,
    require_micro_prose_format,
    resolve_idea_input,
    validate_entity_id,
    validate_output_format,
)
from fabulae.llm import resolve_config
from fabulae.models import Fragment, load_project, save_project

fragment_app = typer.Typer(help="Manage fragments in a Fabulae project.")
console = Console()


@fragment_app.command("add")
def add(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    id: Annotated[str, typer.Option("--id", help="Fragment ID (lowercase-with-hyphens).")],
    content: Annotated[str, typer.Option("--content", "-c", help="Fragment content.")],
    target_words: Annotated[int | None, typer.Option("--target-words", help="Target word count.")] = None,
    notes: Annotated[str | None, typer.Option("--notes", help="Notes about this fragment.")] = None,
) -> None:
    """Add a new fragment to the project.

    Example:
        fabulae fragment add ./my-flash-fiction --id fragment-03 --content "A moment of clarity."
    """
    # Validate ID format before loading project
    validate_entity_id(id)

    project = load_project(project_dir)
    require_micro_prose_format(project, "fragment add")

    # Check for duplicate ID
    existing_ids = get_all_entity_ids(project)
    if id in existing_ids:
        typer.echo(f"Error: ID '{id}' already exists in project.", err=True)
        raise typer.Exit(code=1)

    fragment = Fragment(
        id=id,
        content=content,
        target_words=target_words,
        notes=notes,
    )
    project.plot.fragments.append(fragment)
    save_project(project, project_dir)
    typer.echo(f"Added fragment: {id}")


@fragment_app.command("suggest")
def suggest(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path.")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    base_url: str | None = base_url_option(),
    api_key: str | None = api_key_option(),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Add without confirmation.")] = False,
) -> None:
    """Suggest a new fragment based on project context.

    Example:
        fabulae fragment suggest ./my-flash-fiction --idea "a moment of reflection"
    """
    project = load_project(project_dir)
    require_micro_prose_format(project, "fragment suggest")

    # Resolve idea input
    guidance = resolve_idea_input(idea) if idea else None

    # Build prompt and get suggestion
    config = resolve_config(model, base_url, api_key, temperature, None)
    prompt = build_fragment_suggest_prompt(project, guidance)

    typer.echo("Generating fragment suggestion...")
    suggestion = suggest_entity_sync(FragmentSuggestion, prompt, config)

    # Display suggestion
    console.print("\n[bold]Suggested fragment:[/bold]")
    console.print(f"  ID: {suggestion.id}")
    content_preview = suggestion.content[:100] + "..." if len(suggestion.content) > 100 else suggestion.content
    console.print(f"  Content: {content_preview}")
    if suggestion.target_words:
        console.print(f"  Target words: {suggestion.target_words}")
    if suggestion.notes:
        console.print(f"  Notes: {suggestion.notes}")
    console.print()

    # Confirm and add
    if yes or confirm("Add this fragment?"):
        # Check for duplicate ID
        existing_ids = get_all_entity_ids(project)
        if suggestion.id in existing_ids:
            typer.echo(
                f"Error: ID '{suggestion.id}' already exists. Use 'fragment add' manually.",
                err=True,
            )
            raise typer.Exit(code=1)

        fragment = Fragment(
            id=suggestion.id,
            content=suggestion.content,
            target_words=suggestion.target_words,
            notes=suggestion.notes,
        )
        project.plot.fragments.append(fragment)
        save_project(project, project_dir)
        typer.echo(f"Added fragment: {suggestion.id}")
    else:
        typer.echo("Fragment not added.")


@fragment_app.command("list")
def list_fragments(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, yaml.")] = "table",
) -> None:
    """List all fragments in the project.

    Example:
        fabulae fragment list ./my-flash-fiction --format json
    """
    project = load_project(project_dir)
    require_micro_prose_format(project, "fragment list")

    if not project.plot.fragments:
        typer.echo("No fragments in project.")
        return

    validate_output_format(format)

    if format == "table":
        table = Table(title="Fragments")
        table.add_column("ID", style="cyan")
        table.add_column("Target Words")
        table.add_column("Content")

        for frag in project.plot.fragments:
            content_preview = (frag.content[:50] + "...") if len(frag.content) > 50 else frag.content
            table.add_row(
                frag.id,
                str(frag.target_words) if frag.target_words else "",
                content_preview,
            )

        console.print(table)
    elif format == "json":
        output_list_as_json(project.plot.fragments)
    elif format == "yaml":
        output_list_as_yaml(project.plot.fragments)


@fragment_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    fragment_id: Annotated[str, typer.Argument(help="Fragment ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
) -> None:
    """Remove a fragment from the project.

    Example:
        fabulae fragment remove ./my-flash-fiction fragment-03
    """
    project = load_project(project_dir)
    require_micro_prose_format(project, "fragment remove")

    fragment = find_fragment_by_id(project, fragment_id)
    if not fragment:
        typer.echo(f"Error: Fragment '{fragment_id}' not found.", err=True)
        raise typer.Exit(code=1)

    if not force and not confirm(f"Remove fragment '{fragment_id}'?"):
        typer.echo("Fragment not removed.")
        return

    project.plot.fragments = [f for f in project.plot.fragments if f.id != fragment_id]
    save_project(project, project_dir)
    typer.echo(f"Removed fragment: {fragment_id}")


@fragment_app.command("edit")
def edit(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    fragment_id: Annotated[str, typer.Argument(help="Fragment ID to edit.")],
    content: Annotated[str | None, typer.Option("--content", "-c", help="New content.")] = None,
    target_words: Annotated[int | None, typer.Option("--target-words", help="New target word count.")] = None,
    notes: Annotated[str | None, typer.Option("--notes", help="New notes.")] = None,
) -> None:
    """Edit an existing fragment.

    Example:
        fabulae fragment edit ./my-flash-fiction fragment-01 --content "Updated prose."
    """
    project = load_project(project_dir)
    require_micro_prose_format(project, "fragment edit")

    fragment = find_fragment_by_id(project, fragment_id)
    if not fragment:
        typer.echo(f"Error: Fragment '{fragment_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Update only provided fields
    if content is not None:
        fragment.content = content
    if target_words is not None:
        fragment.target_words = target_words
    if notes is not None:
        fragment.notes = notes if notes else None

    save_project(project, project_dir)
    typer.echo(f"Updated fragment: {fragment_id}")
