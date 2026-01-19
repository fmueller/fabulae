"""Character CRUD commands for Fabulae projects."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.generation.character import suggest_character_sync
from fabulae.features.entities.utils import (
    confirm,
    find_character_by_id,
    get_all_entity_ids,
    get_character_references,
    output_list_as_json,
    output_list_as_yaml,
    resolve_idea_input,
    validate_entity_id,
    validate_output_format,
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
    validate_entity_id(id)
    project = load_project(project_dir)

    if id in get_all_entity_ids(project):
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
    guidance = resolve_idea_input(idea) if idea else None
    config = resolve_config(model, base_url, api_key, temperature, None)

    typer.echo("Generating character suggestion...")
    character = suggest_character_sync(project=project, guidance=guidance, config=config)

    console.print("\n[bold]Suggested character:[/bold]")
    console.print(f"  ID: {character.id}")
    console.print(f"  Name: {character.name}")
    if character.role:
        console.print(f"  Role: {character.role}")
    if character.desire:
        console.print(f"  Desire: {character.desire}")
    if character.need:
        console.print(f"  Need: {character.need}")
    if character.flaw:
        console.print(f"  Flaw: {character.flaw}")
    if character.secret:
        console.print(f"  Secret: {character.secret}")
    if character.traits:
        console.print(f"  Traits: {', '.join(character.traits)}")
    console.print()

    if yes or confirm("Add this character?"):
        if character.id in get_all_entity_ids(project):
            typer.echo(
                f"Error: ID '{character.id}' already exists. Use 'character add' manually.",
                err=True,
            )
            raise typer.Exit(code=1)

        project.characters.append(character)
        save_project(project, project_dir)
        typer.echo(f"Added character: {character.name} ({character.id})")
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

    validate_output_format(format)

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
        output_list_as_json(project.characters)
    elif format == "yaml":
        output_list_as_yaml(project.characters)


@character_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    character_id: Annotated[str, typer.Argument(help="Character ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
) -> None:
    """Remove a character from the project.

    If the character is referenced in scenes, those references will be cleaned up
    when using --force.

    Example:
        fabulae character remove ./my-novel detective-jane
    """
    project = load_project(project_dir)

    character = find_character_by_id(project, character_id)
    if not character:
        typer.echo(f"Error: Character '{character_id}' not found.", err=True)
        raise typer.Exit(code=1)

    references = get_character_references(project, character_id)
    if references:
        typer.echo(f"Warning: Character is referenced in scenes: {', '.join(references)}")

    if not force and not confirm(f"Remove character '{character.name}' ({character_id})?"):
        typer.echo("Character not removed.")
        return

    if references:
        typer.echo("Cleaning up references...")
        for scene in project.plot.scenes:
            if character_id in scene.characters:
                scene.characters = [c for c in scene.characters if c != character_id]
                typer.echo(f"  - Removed from scene '{scene.id}' characters list")

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

    if add_trait:
        for trait in add_trait:
            if trait not in character.traits:
                character.traits.append(trait)
    if remove_trait:
        character.traits = [t for t in character.traits if t not in remove_trait]

    save_project(project, project_dir)
    typer.echo(f"Updated character: {character.name} ({character_id})")
