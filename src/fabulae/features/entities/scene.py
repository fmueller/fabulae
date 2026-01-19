"""Scene CRUD commands for Fabulae projects."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.prompts import build_scene_suggest_prompt
from fabulae.features.entities.schemas import SceneSuggestion
from fabulae.features.entities.service import suggest_entity_sync
from fabulae.features.entities.utils import (
    confirm,
    find_chapter_by_id,
    find_chapter_containing_scene,
    find_scene_by_id,
    get_all_entity_ids,
    output_list_as_json,
    output_list_as_yaml,
    require_prose_format,
    resolve_idea_input,
    validate_entity_id,
    validate_output_format,
)
from fabulae.llm import resolve_config
from fabulae.models import Scene, load_project, save_project

scene_app = typer.Typer(help="Manage scenes in a Fabulae project.")
console = Console()


@scene_app.command("add")
def add(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    id: Annotated[str, typer.Option("--id", help="Scene ID (lowercase-with-hyphens).")],
    chapter: Annotated[str | None, typer.Option("--chapter", "-c", help="Chapter ID to add scene to.")] = None,
    location: Annotated[str | None, typer.Option("--location", "-l", help="Location ID (world fact).")] = None,
    time: Annotated[str | None, typer.Option("--time", "-t", help="Time of day.")] = None,
    summary: Annotated[str | None, typer.Option("--summary", help="Scene summary.")] = None,
    goal: Annotated[str | None, typer.Option("--goal", help="Scene goal.")] = None,
    conflict: Annotated[str | None, typer.Option("--conflict", help="Scene conflict.")] = None,
    outcome: Annotated[str | None, typer.Option("--outcome", help="Scene outcome.")] = None,
    characters: Annotated[list[str] | None, typer.Option("--character", help="Character IDs (repeatable).")] = None,
    world_facts: Annotated[list[str] | None, typer.Option("--world-fact", help="World fact IDs (repeatable).")] = None,
) -> None:
    """Add a new scene to the project.

    Example:
        fabulae scene add ./my-novel --id scene-discovery --chapter chapter-01 --summary "Vera finds a clue"
    """
    # Validate ID format before loading project
    validate_entity_id(id)

    project = load_project(project_dir)
    require_prose_format(project, "scene add")

    # Check for duplicate ID
    existing_ids = get_all_entity_ids(project)
    if id in existing_ids:
        typer.echo(f"Error: ID '{id}' already exists in project.", err=True)
        raise typer.Exit(code=1)

    # Validate location if provided
    if location:
        if not project.world:
            typer.echo(f"Error: No world facts defined. Cannot use location '{location}'.", err=True)
            raise typer.Exit(code=1)
        location_fact = next((f for f in project.world.facts if f.id == location and f.type == "location"), None)
        if not location_fact:
            typer.echo(f"Error: Location '{location}' not found or not a location type.", err=True)
            raise typer.Exit(code=1)

    # Validate characters if provided
    if characters:
        valid_char_ids = {c.id for c in project.characters}
        invalid = set(characters) - valid_char_ids
        if invalid:
            typer.echo(f"Error: Unknown character IDs: {', '.join(sorted(invalid))}", err=True)
            raise typer.Exit(code=1)

    # Validate world facts if provided
    if world_facts:
        valid_fact_ids = {f.id for f in project.world.facts} if project.world else set()
        invalid = set(world_facts) - valid_fact_ids
        if invalid:
            typer.echo(f"Error: World fact(s) not found: {', '.join(sorted(invalid))}", err=True)
            raise typer.Exit(code=1)

    scene = Scene(
        id=id,
        location=location,
        time=time,
        summary=summary,
        goal=goal,
        conflict=conflict,
        outcome=outcome,
        characters=characters or [],
        world_fact_ids=world_facts or [],
    )
    project.plot.scenes.append(scene)

    # Add to chapter if specified
    if chapter:
        chapter_obj = find_chapter_by_id(project, chapter)
        if not chapter_obj:
            typer.echo(f"Error: Chapter '{chapter}' not found.", err=True)
            raise typer.Exit(code=1)
        if chapter_obj.scene_ids is None:
            chapter_obj.scene_ids = []
        chapter_obj.scene_ids.append(id)

    save_project(project, project_dir)
    if chapter:
        typer.echo(f"Added scene: {id} to chapter {chapter}")
    else:
        typer.echo(f"Added scene: {id}")


@scene_app.command("suggest")
def suggest(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    chapter: Annotated[str | None, typer.Option("--chapter", "-c", help="Chapter ID for context.")] = None,
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path.")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    base_url: str | None = base_url_option(),
    api_key: str | None = api_key_option(),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Add without confirmation.")] = False,
) -> None:
    """Suggest a new scene based on project context.

    Example:
        fabulae scene suggest ./my-novel --chapter chapter-02 --idea "confrontation"
    """
    project = load_project(project_dir)
    require_prose_format(project, "scene suggest")

    # Validate chapter if provided
    if chapter:
        chapter_obj = find_chapter_by_id(project, chapter)
        if not chapter_obj:
            typer.echo(f"Error: Chapter '{chapter}' not found.", err=True)
            raise typer.Exit(code=1)

    # Resolve idea input
    guidance = resolve_idea_input(idea) if idea else None

    # Build prompt and get suggestion
    config = resolve_config(model, base_url, api_key, temperature, None)
    prompt = build_scene_suggest_prompt(project, chapter, guidance)

    typer.echo("Generating scene suggestion...")
    suggestion = suggest_entity_sync(SceneSuggestion, prompt, config)

    # Display suggestion
    console.print("\n[bold]Suggested scene:[/bold]")
    console.print(f"  ID: {suggestion.id}")
    if suggestion.summary:
        console.print(f"  Summary: {suggestion.summary}")
    if suggestion.goal:
        console.print(f"  Goal: {suggestion.goal}")
    if suggestion.conflict:
        console.print(f"  Conflict: {suggestion.conflict}")
    if suggestion.outcome:
        console.print(f"  Outcome: {suggestion.outcome}")
    if suggestion.characters:
        console.print(f"  Characters: {', '.join(suggestion.characters)}")
    if suggestion.location:
        console.print(f"  Location: {suggestion.location}")
    if suggestion.time:
        console.print(f"  Time: {suggestion.time}")
    console.print()

    # Confirm and add
    if yes or confirm("Add this scene?"):
        # Check for duplicate ID
        existing_ids = get_all_entity_ids(project)
        if suggestion.id in existing_ids:
            typer.echo(f"Error: ID '{suggestion.id}' already exists. Try again or use 'scene add' manually.", err=True)
            raise typer.Exit(code=1)

        # Validate references
        valid_char_ids = {c.id for c in project.characters}
        valid_characters = [c for c in suggestion.characters if c in valid_char_ids]

        valid_location = None
        if suggestion.location and project.world:
            loc_fact = next(
                (f for f in project.world.facts if f.id == suggestion.location and f.type == "location"),
                None,
            )
            if loc_fact:
                valid_location = suggestion.location

        scene = Scene(
            id=suggestion.id,
            summary=suggestion.summary,
            goal=suggestion.goal,
            conflict=suggestion.conflict,
            outcome=suggestion.outcome,
            characters=valid_characters,
            location=valid_location,
            time=suggestion.time,
        )
        project.plot.scenes.append(scene)

        # Add to chapter if specified
        if chapter:
            chapter_obj = find_chapter_by_id(project, chapter)
            if chapter_obj:
                if chapter_obj.scene_ids is None:
                    chapter_obj.scene_ids = []
                chapter_obj.scene_ids.append(suggestion.id)

        save_project(project, project_dir)
        if chapter:
            typer.echo(f"Added scene: {suggestion.id} to chapter {chapter}")
        else:
            typer.echo(f"Added scene: {suggestion.id}")
    else:
        typer.echo("Scene not added.")


@scene_app.command("list")
def list_scenes(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    chapter: Annotated[str | None, typer.Option("--chapter", "-c", help="Filter by chapter ID.")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, yaml.")] = "table",
) -> None:
    """List scenes in the project.

    Example:
        fabulae scene list ./my-novel --chapter chapter-01
    """
    project = load_project(project_dir)
    require_prose_format(project, "scene list")

    scenes = project.plot.scenes
    if chapter:
        chapter_obj = find_chapter_by_id(project, chapter)
        if not chapter_obj:
            typer.echo(f"Error: Chapter '{chapter}' not found.", err=True)
            raise typer.Exit(code=1)
        scenes = [s for s in scenes if s.id in chapter_obj.scene_ids] if chapter_obj.scene_ids else []

    if not scenes:
        if chapter:
            typer.echo(f"No scenes in chapter '{chapter}'.")
        else:
            typer.echo("No scenes in project.")
        return

    validate_output_format(format)

    if format == "table":
        table = Table(title="Scenes")
        table.add_column("ID", style="cyan")
        table.add_column("Location", style="yellow")
        table.add_column("Characters")
        table.add_column("Summary")

        for s in scenes:
            chars_str = ", ".join(s.characters[:2]) if s.characters else ""
            if s.characters and len(s.characters) > 2:
                chars_str += "..."
            summary = (s.summary[:35] + "...") if s.summary and len(s.summary) > 35 else (s.summary or "")
            table.add_row(s.id, s.location or "", chars_str, summary)

        console.print(table)
    elif format == "json":
        output_list_as_json(scenes)
    elif format == "yaml":
        output_list_as_yaml(scenes)


@scene_app.command("move")
def move(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    scene_id: Annotated[str, typer.Argument(help="Scene ID to move.")],
    to_chapter: Annotated[str, typer.Option("--to-chapter", help="Target chapter ID.")],
    position: Annotated[int | None, typer.Option("--position", "-p", help="Position in target chapter.")] = None,
) -> None:
    """Move a scene to a different chapter.

    Example:
        fabulae scene move ./my-novel scene-discovery --to-chapter chapter-02
    """
    project = load_project(project_dir)
    require_prose_format(project, "scene move")

    # Find the scene
    scene = find_scene_by_id(project, scene_id)
    if not scene:
        typer.echo(f"Error: Scene '{scene_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Find target chapter
    target_chapter = find_chapter_by_id(project, to_chapter)
    if not target_chapter:
        typer.echo(f"Error: Target chapter '{to_chapter}' not found.", err=True)
        raise typer.Exit(code=1)

    # Find source chapter and remove
    source_chapter = find_chapter_containing_scene(project, scene_id)
    if source_chapter and source_chapter.scene_ids:
        source_chapter.scene_ids = [sid for sid in source_chapter.scene_ids if sid != scene_id]

    # Add to target chapter
    if target_chapter.scene_ids is None:
        target_chapter.scene_ids = []

    if position is not None:
        target_chapter.scene_ids.insert(position, scene_id)
    else:
        target_chapter.scene_ids.append(scene_id)

    save_project(project, project_dir)
    source_name = source_chapter.id if source_chapter else "unassigned"
    typer.echo(f"Moved scene '{scene_id}' from '{source_name}' to '{to_chapter}'")


@scene_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    scene_id: Annotated[str, typer.Argument(help="Scene ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
) -> None:
    """Remove a scene from the project.

    Example:
        fabulae scene remove ./my-novel scene-discovery
    """
    project = load_project(project_dir)
    require_prose_format(project, "scene remove")

    scene = find_scene_by_id(project, scene_id)
    if not scene:
        typer.echo(f"Error: Scene '{scene_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Warn about beats
    if scene.beats:
        typer.echo(f"Warning: Scene contains {len(scene.beats)} beat(s) that will be deleted.")

    if not force and not confirm(f"Remove scene '{scene_id}'?"):
        typer.echo("Scene not removed.")
        return

    # Remove from chapter
    chapter = find_chapter_containing_scene(project, scene_id)
    if chapter and chapter.scene_ids:
        chapter.scene_ids = [sid for sid in chapter.scene_ids if sid != scene_id]

    # Remove scene
    project.plot.scenes = [s for s in project.plot.scenes if s.id != scene_id]

    save_project(project, project_dir)
    typer.echo(f"Removed scene: {scene_id}")


@scene_app.command("edit")
def edit(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    scene_id: Annotated[str, typer.Argument(help="Scene ID to edit.")],
    location: Annotated[str | None, typer.Option("--location", "-l", help="New location ID.")] = None,
    time: Annotated[str | None, typer.Option("--time", "-t", help="New time.")] = None,
    summary: Annotated[str | None, typer.Option("--summary", help="New summary.")] = None,
    goal: Annotated[str | None, typer.Option("--goal", help="New goal.")] = None,
    conflict: Annotated[str | None, typer.Option("--conflict", help="New conflict.")] = None,
    outcome: Annotated[str | None, typer.Option("--outcome", help="New outcome.")] = None,
    add_character: Annotated[list[str] | None, typer.Option("--add-character", help="Add character ID.")] = None,
    remove_character: Annotated[
        list[str] | None, typer.Option("--remove-character", help="Remove character ID.")
    ] = None,
    add_world_fact: Annotated[list[str] | None, typer.Option("--add-world-fact", help="Add world fact ID.")] = None,
    remove_world_fact: Annotated[
        list[str] | None, typer.Option("--remove-world-fact", help="Remove world fact ID.")
    ] = None,
) -> None:
    """Edit an existing scene.

    Example:
        fabulae scene edit ./my-novel scene-discovery --location tavern --summary "Updated scene"
    """
    project = load_project(project_dir)
    require_prose_format(project, "scene edit")

    scene = find_scene_by_id(project, scene_id)
    if not scene:
        typer.echo(f"Error: Scene '{scene_id}' not found.", err=True)
        raise typer.Exit(code=1)

    # Validate location if provided
    if location is not None:
        if location:  # Non-empty string
            if not project.world:
                typer.echo(f"Error: No world facts defined. Cannot use location '{location}'.", err=True)
                raise typer.Exit(code=1)
            location_fact = next((f for f in project.world.facts if f.id == location and f.type == "location"), None)
            if not location_fact:
                typer.echo(f"Error: Location '{location}' not found or not a location type.", err=True)
                raise typer.Exit(code=1)
        scene.location = location if location else None

    # Update simple fields
    if time is not None:
        scene.time = time if time else None
    if summary is not None:
        scene.summary = summary if summary else None
    if goal is not None:
        scene.goal = goal if goal else None
    if conflict is not None:
        scene.conflict = conflict if conflict else None
    if outcome is not None:
        scene.outcome = outcome if outcome else None

    # Handle character modifications
    if add_character:
        valid_char_ids = {c.id for c in project.characters}
        for char_id in add_character:
            if char_id not in valid_char_ids:
                typer.echo(f"Warning: Character '{char_id}' not found, skipping.", err=True)
            elif char_id not in scene.characters:
                scene.characters.append(char_id)
    if remove_character:
        scene.characters = [c for c in scene.characters if c not in remove_character]

    # Handle world fact modifications
    if add_world_fact:
        valid_fact_ids = {f.id for f in project.world.facts} if project.world else set()
        for fact_id in add_world_fact:
            if fact_id not in valid_fact_ids:
                typer.echo(f"Warning: World fact '{fact_id}' not found, skipping.", err=True)
            elif fact_id not in scene.world_fact_ids:
                scene.world_fact_ids.append(fact_id)
    if remove_world_fact:
        scene.world_fact_ids = [f for f in scene.world_fact_ids if f not in remove_world_fact]

    save_project(project, project_dir)
    typer.echo(f"Updated scene: {scene_id}")
