"""World fact CRUD commands for Fabulae projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Literal

import typer
import yaml
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.prompts import build_world_suggest_prompt
from fabulae.features.entities.schemas import WorldFactSuggestion
from fabulae.features.entities.service import suggest_entity_sync
from fabulae.features.entities.utils import (
    confirm,
    find_world_fact_by_id,
    get_all_entity_ids,
    get_world_fact_references,
    resolve_idea_input,
)
from fabulae.llm import resolve_config
from fabulae.models import World, WorldFact, load_project, save_project

world_app = typer.Typer(help="Manage world facts in a Fabulae project.")
console = Console()

WorldFactType = Literal["location", "culture", "history", "rule", "object"]


@world_app.command("add")
def add(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    id: Annotated[str, typer.Option("--id", help="World fact ID (lowercase-with-hyphens).")],
    type: Annotated[str, typer.Option("--type", "-t", help="Fact type: location, culture, history, rule, object.")],
    name: Annotated[str, typer.Option("--name", "-n", help="Name of the world element.")],
    facts: Annotated[list[str] | None, typer.Option("--fact", "-f", help="Specific details (repeatable).")] = None,
) -> None:
    """Add a new world fact to the project.

    Example:
        fabulae world add ./my-novel --id tavern-golden --type location --name "The Tankard"
    """
    project = load_project(project_dir)

    # Validate type
    valid_types = ["location", "culture", "history", "rule", "object"]
    if type not in valid_types:
        typer.echo(f"Error: Invalid type '{type}'. Must be one of: {', '.join(valid_types)}", err=True)
        raise typer.Exit(code=1)

    # Check for duplicate ID
    existing_ids = get_all_entity_ids(project)
    if id in existing_ids:
        typer.echo(f"Error: ID '{id}' already exists in project.", err=True)
        raise typer.Exit(code=1)

    world_fact = WorldFact(
        id=id,
        type=type,  # type: ignore[arg-type]
        name=name,
        facts=facts or [],
    )

    # Ensure world exists
    if not project.world:
        project.world = World()
    project.world.facts.append(world_fact)
    save_project(project, project_dir)
    typer.echo(f"Added world fact: {name} ({id})")


@world_app.command("suggest")
def suggest(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    type: Annotated[str | None, typer.Option("--type", help="Constrain to type: location, culture, etc.")] = None,
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path.")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    base_url: str | None = base_url_option(),
    api_key: str | None = api_key_option(),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Add without confirmation.")] = False,
) -> None:
    """Suggest a new world fact based on project context.

    Example:
        fabulae world suggest ./my-novel --type location --idea "a mysterious forest"
    """
    project = load_project(project_dir)

    # Validate type if provided
    if type:
        valid_types = ["location", "culture", "history", "rule", "object"]
        if type not in valid_types:
            typer.echo(f"Error: Invalid type '{type}'. Must be one of: {', '.join(valid_types)}", err=True)
            raise typer.Exit(code=1)

    # Resolve idea input
    guidance = resolve_idea_input(idea) if idea else None

    # Build prompt and get suggestion
    config = resolve_config(model, base_url, api_key, temperature, None)
    prompt = build_world_suggest_prompt(project, type, guidance)

    typer.echo("Generating world fact suggestion...")
    suggestion = suggest_entity_sync(WorldFactSuggestion, prompt, config)

    # Display suggestion
    console.print("\n[bold]Suggested world fact:[/bold]")
    console.print(f"  ID: {suggestion.id}")
    console.print(f"  Type: {suggestion.type}")
    console.print(f"  Name: {suggestion.name}")
    if suggestion.facts:
        console.print("  Facts:")
        for fact in suggestion.facts:
            console.print(f"    - {fact}")
    console.print()

    # Confirm and add
    if yes or confirm("Add this world fact?"):
        # Check for duplicate ID
        existing_ids = get_all_entity_ids(project)
        if suggestion.id in existing_ids:
            typer.echo(f"Error: ID '{suggestion.id}' already exists. Try again or use 'world add' manually.", err=True)
            raise typer.Exit(code=1)

        world_fact = WorldFact(
            id=suggestion.id,
            type=suggestion.type,
            name=suggestion.name,
            facts=suggestion.facts,
        )

        # Ensure world exists
        if not project.world:
            project.world = World()
        project.world.facts.append(world_fact)
        save_project(project, project_dir)
        typer.echo(f"Added world fact: {suggestion.name} ({suggestion.id})")
    else:
        typer.echo("World fact not added.")


@world_app.command("list")
def list_world_facts(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    type: Annotated[str | None, typer.Option("--type", "-t", help="Filter by type.")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, yaml.")] = "table",
) -> None:
    """List world facts in the project.

    Example:
        fabulae world list ./my-novel --type location
    """
    project = load_project(project_dir)

    if not project.world or not project.world.facts:
        typer.echo("No world facts in project.")
        return

    facts = project.world.facts
    if type:
        valid_types = ["location", "culture", "history", "rule", "object"]
        if type not in valid_types:
            typer.echo(f"Error: Invalid type '{type}'. Must be one of: {', '.join(valid_types)}", err=True)
            raise typer.Exit(code=1)
        facts = [f for f in facts if f.type == type]

    if not facts:
        typer.echo(f"No world facts of type '{type}'.")
        return

    if format == "table":
        table = Table(title="World Facts")
        table.add_column("ID", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Name", style="green")
        table.add_column("Facts")

        for fact in facts:
            facts_preview = "; ".join(fact.facts[:2]) if fact.facts else ""
            if fact.facts and len(fact.facts) > 2:
                facts_preview += "..."
            if len(facts_preview) > 40:
                facts_preview = facts_preview[:37] + "..."
            table.add_row(fact.id, fact.type, fact.name, facts_preview)

        console.print(table)

    elif format == "json":
        data = [f.model_dump(exclude_none=True) for f in facts]
        typer.echo(json.dumps(data, indent=2))

    elif format == "yaml":
        data = [f.model_dump(exclude_none=True) for f in facts]
        typer.echo(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    else:
        typer.echo(f"Unknown format: {format}. Use table, json, or yaml.", err=True)
        raise typer.Exit(code=1)


@world_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    fact_id: Annotated[str, typer.Argument(help="World fact ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
) -> None:
    """Remove a world fact from the project.

    Example:
        fabulae world remove ./my-novel tavern-golden
    """
    project = load_project(project_dir)

    fact = find_world_fact_by_id(project, fact_id)
    if not fact:
        typer.echo(f"Error: World fact '{fact_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Check for references
    references = get_world_fact_references(project, fact_id)
    if references:
        typer.echo(f"Warning: World fact is referenced in scenes: {', '.join(references)}")

    if not force and not confirm(f"Remove world fact '{fact.name}' ({fact_id})?"):
        typer.echo("World fact not removed.")
        return

    if project.world:
        project.world.facts = [f for f in project.world.facts if f.id != fact_id]
    save_project(project, project_dir)
    typer.echo(f"Removed world fact: {fact.name} ({fact_id})")


@world_app.command("edit")
def edit(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    fact_id: Annotated[str, typer.Argument(help="World fact ID to edit.")],
    name: Annotated[str | None, typer.Option("--name", "-n", help="New name.")] = None,
    type: Annotated[str | None, typer.Option("--type", "-t", help="New type.")] = None,
    add_fact: Annotated[
        list[str] | None, typer.Option("--add-fact", help="Add a fact.")
    ] = None,
    remove_fact: Annotated[
        list[str] | None, typer.Option("--remove-fact", help="Remove a fact (by exact text).")
    ] = None,
) -> None:
    """Edit an existing world fact.

    Example:
        fabulae world edit ./my-novel tavern-golden --name "The Silver Tankard" --add-fact "Recently renovated"
    """
    project = load_project(project_dir)

    fact = find_world_fact_by_id(project, fact_id)
    if not fact:
        typer.echo(f"Error: World fact '{fact_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Validate type if provided
    if type is not None:
        valid_types = ["location", "culture", "history", "rule", "object"]
        if type not in valid_types:
            typer.echo(f"Error: Invalid type '{type}'. Must be one of: {', '.join(valid_types)}", err=True)
            raise typer.Exit(code=1)
        fact.type = type  # type: ignore[assignment]

    # Update fields
    if name is not None:
        fact.name = name

    # Handle fact modifications
    if add_fact:
        for f in add_fact:
            if f not in fact.facts:
                fact.facts.append(f)
    if remove_fact:
        fact.facts = [f for f in fact.facts if f not in remove_fact]

    save_project(project, project_dir)
    typer.echo(f"Updated world fact: {fact_id}")
