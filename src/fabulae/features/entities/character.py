"""Character CRUD commands for Fabulae projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.prompts import build_character_suggest_prompt
from fabulae.features.entities.schemas import CharacterSuggestion
from fabulae.features.entities.service import suggest_entity_sync
from fabulae.features.entities.utils import (
    confirm,
    find_character_by_id,
    get_all_entity_ids,
    get_character_references,
    resolve_idea_input,
)
from fabulae.llm import resolve_config
from fabulae.models import Character, load_project, save_project

character_app = typer.Typer(help="Manage characters in a Fabulae project.")
console = Console()


@character_app.command("add")
def add(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    id: Annotated[str, typer.Option("--id", help="Character ID (lowercase-with-hyphens).")],
    name: Annotated[str, typer.Option("--name", help="Character name.")],
    role: Annotated[str | None, typer.Option("--role", help="Role: protagonist, antagonist, or supporting.")] = None,
    desire: Annotated[str | None, typer.Option("--desire", help="What the character wants.")] = None,
    need: Annotated[str | None, typer.Option("--need", help="What the character needs.")] = None,
    flaw: Annotated[str | None, typer.Option("--flaw", help="Character's key weakness.")] = None,
    secret: Annotated[str | None, typer.Option("--secret", help="Hidden information.")] = None,
    traits: Annotated[list[str] | None, typer.Option("--trait", help="Personality traits (repeatable).")] = None,
) -> None:
    """Add a new character to the project.

    Example:
        fabulae character add ./my-novel --id "detective-jane" --name "Jane Doe" --role protagonist
    """
    project = load_project(project_dir)

    # Check for duplicate ID
    existing_ids = get_all_entity_ids(project)
    if id in existing_ids:
        typer.echo(f"Error: ID '{id}' already exists in project.", err=True)
        raise typer.Exit(code=1)

    character = Character(
        id=id,
        name=name,
        role=role,
        desire=desire,
        need=need,
        flaw=flaw,
        secret=secret,
        traits=traits or [],
    )
    project.characters.append(character)
    save_project(project, project_dir)
    typer.echo(f"Added character: {name} ({id})")


@character_app.command("suggest")
def suggest(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path.")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    base_url: str | None = base_url_option(),
    api_key: str | None = api_key_option(),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Add without confirmation.")] = False,
) -> None:
    """Suggest a new character based on project context.

    Example:
        fabulae character suggest ./my-novel --idea "a mysterious mentor figure"
    """
    project = load_project(project_dir)

    # Resolve idea input
    guidance = resolve_idea_input(idea) if idea else None

    # Build prompt and get suggestion
    config = resolve_config(model, base_url, api_key, temperature, None)
    prompt = build_character_suggest_prompt(project, guidance)

    typer.echo("Generating character suggestion...")
    suggestion = suggest_entity_sync(CharacterSuggestion, prompt, config)

    # Display suggestion
    console.print("\n[bold]Suggested character:[/bold]")
    console.print(f"  ID: {suggestion.id}")
    console.print(f"  Name: {suggestion.name}")
    if suggestion.role:
        console.print(f"  Role: {suggestion.role}")
    if suggestion.desire:
        console.print(f"  Desire: {suggestion.desire}")
    if suggestion.need:
        console.print(f"  Need: {suggestion.need}")
    if suggestion.flaw:
        console.print(f"  Flaw: {suggestion.flaw}")
    if suggestion.secret:
        console.print(f"  Secret: {suggestion.secret}")
    if suggestion.traits:
        console.print(f"  Traits: {', '.join(suggestion.traits)}")
    console.print()

    # Confirm and add
    if yes or confirm("Add this character?"):
        # Check for duplicate ID
        existing_ids = get_all_entity_ids(project)
        if suggestion.id in existing_ids:
            typer.echo(
                f"Error: ID '{suggestion.id}' already exists. Use 'character add' manually.",
                err=True,
            )
            raise typer.Exit(code=1)

        character = Character(
            id=suggestion.id,
            name=suggestion.name,
            role=suggestion.role,
            desire=suggestion.desire,
            need=suggestion.need,
            flaw=suggestion.flaw,
            secret=suggestion.secret,
            traits=suggestion.traits,
        )
        project.characters.append(character)
        save_project(project, project_dir)
        typer.echo(f"Added character: {suggestion.name} ({suggestion.id})")
    else:
        typer.echo("Character not added.")


@character_app.command("list")
def list_characters(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, yaml.")] = "table",
) -> None:
    """List all characters in the project.

    Example:
        fabulae character list ./my-novel --format json
    """
    project = load_project(project_dir)

    if not project.characters:
        typer.echo("No characters in project.")
        return

    if format == "table":
        table = Table(title="Characters")
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="green")
        table.add_column("Role")
        table.add_column("Traits")

        for char in project.characters:
            traits_str = ", ".join(char.traits[:3]) if char.traits else ""
            if char.traits and len(char.traits) > 3:
                traits_str += "..."
            table.add_row(char.id, char.name, char.role or "", traits_str)

        console.print(table)

    elif format == "json":
        data = [char.model_dump(exclude_none=True) for char in project.characters]
        typer.echo(json.dumps(data, indent=2))

    elif format == "yaml":
        data = [char.model_dump(exclude_none=True) for char in project.characters]
        typer.echo(yaml.dump(data, default_flow_style=False, allow_unicode=True))

    else:
        typer.echo(f"Unknown format: {format}. Use table, json, or yaml.", err=True)
        raise typer.Exit(code=1)


@character_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    character_id: Annotated[str, typer.Argument(help="Character ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
) -> None:
    """Remove a character from the project.

    Example:
        fabulae character remove ./my-novel detective-jane
    """
    project = load_project(project_dir)

    character = find_character_by_id(project, character_id)
    if not character:
        typer.echo(f"Error: Character '{character_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Check for references
    references = get_character_references(project, character_id)
    if references:
        typer.echo(f"Warning: Character is referenced in scenes: {', '.join(references)}")

    if not force and not confirm(f"Remove character '{character.name}' ({character_id})?"):
        typer.echo("Character not removed.")
        return

    project.characters = [c for c in project.characters if c.id != character_id]
    save_project(project, project_dir)
    typer.echo(f"Removed character: {character.name} ({character_id})")


@character_app.command("edit")
def edit(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    character_id: Annotated[str, typer.Argument(help="Character ID to edit.")],
    name: Annotated[str | None, typer.Option("--name", help="New character name.")] = None,
    role: Annotated[str | None, typer.Option("--role", help="New role.")] = None,
    desire: Annotated[str | None, typer.Option("--desire", help="New desire.")] = None,
    need: Annotated[str | None, typer.Option("--need", help="New need.")] = None,
    flaw: Annotated[str | None, typer.Option("--flaw", help="New flaw.")] = None,
    secret: Annotated[str | None, typer.Option("--secret", help="New secret.")] = None,
    add_trait: Annotated[list[str] | None, typer.Option("--add-trait", help="Add a trait.")] = None,
    remove_trait: Annotated[list[str] | None, typer.Option("--remove-trait", help="Remove a trait.")] = None,
) -> None:
    """Edit an existing character.

    Example:
        fabulae character edit ./my-novel detective-jane --name "Jane Smith" --role antagonist
    """
    project = load_project(project_dir)

    character = find_character_by_id(project, character_id)
    if not character:
        typer.echo(f"Error: Character '{character_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Update only provided fields
    if name is not None:
        character.name = name
    if role is not None:
        character.role = role
    if desire is not None:
        character.desire = desire
    if need is not None:
        character.need = need
    if flaw is not None:
        character.flaw = flaw
    if secret is not None:
        character.secret = secret

    # Handle trait modifications
    if add_trait:
        for trait in add_trait:
            if trait not in character.traits:
                character.traits.append(trait)
    if remove_trait:
        character.traits = [t for t in character.traits if t not in remove_trait]

    save_project(project, project_dir)
    typer.echo(f"Updated character: {character.name} ({character_id})")
