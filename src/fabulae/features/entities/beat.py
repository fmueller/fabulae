"""Beat CRUD commands for Fabulae projects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
import yaml
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.prompts import build_beat_suggest_prompt
from fabulae.features.entities.schemas import BeatSuggestion
from fabulae.features.entities.service import suggest_entity_sync
from fabulae.features.entities.utils import (
    confirm,
    find_scene_by_id,
    get_all_entity_ids,
    resolve_idea_input,
    validate_entity_id,
)
from fabulae.llm import resolve_config
from fabulae.models import Beat, load_project, save_project

beat_app = typer.Typer(help="Manage beats in a Fabulae project.")
console = Console()


def _find_beat_in_project(project: object, beat_id: str) -> tuple[object, Beat] | None:
    """Find a beat by ID across all scenes. Returns (scene, beat) or None."""
    from fabulae.models import Project

    if not isinstance(project, Project):
        return None
    for scene in project.plot.scenes:
        for beat in scene.beats:
            if beat.id == beat_id:
                return (scene, beat)
    return None


@beat_app.command("add")
def add(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    scene: Annotated[str, typer.Option("--scene", "-s", help="Scene ID to add beat to.")],
    id: Annotated[str, typer.Option("--id", help="Beat ID (lowercase-with-hyphens).")],
    kind: Annotated[str, typer.Option("--kind", "-k", help="Beat type (action, dialogue, revelation, etc.).")],
    summary: Annotated[str | None, typer.Option("--summary", help="Beat summary.")] = None,
    goal: Annotated[str | None, typer.Option("--goal", help="What the POV character wants.")] = None,
    conflict: Annotated[str | None, typer.Option("--conflict", help="Obstacle or tension.")] = None,
    outcome: Annotated[str | None, typer.Option("--outcome", help="How the beat resolves.")] = None,
    pace: Annotated[str | None, typer.Option("--pace", help="Pacing note (fast, slow, tense).")] = None,
    target_words: Annotated[int | None, typer.Option("--target-words", help="Target word count.")] = None,
    constraints: Annotated[
        list[str] | None, typer.Option("--constraint", help="Prose generation constraints (repeatable).")
    ] = None,
) -> None:
    """Add a new beat to a scene.

    Example:
        fabulae beat add ./my-novel --scene scene-01 --id beat-discovery --kind revelation
    """
    # Validate ID format before loading project
    validate_entity_id(id)

    project = load_project(project_dir)

    scene_obj = find_scene_by_id(project, scene)
    if not scene_obj:
        typer.echo(f"Error: Scene '{scene}' not found.", err=True)
        raise typer.Exit(code=1)

    # Check for duplicate ID
    existing_ids = get_all_entity_ids(project)
    if id in existing_ids:
        typer.echo(f"Error: ID '{id}' already exists in project.", err=True)
        raise typer.Exit(code=1)

    beat = Beat(
        id=id,
        kind=kind,
        summary=summary,
        goal=goal,
        conflict=conflict,
        outcome=outcome,
        pace=pace,
        target_words=target_words,
        constraints=constraints or [],
    )
    scene_obj.beats.append(beat)
    save_project(project, project_dir)
    typer.echo(f"Added beat: {id} to scene {scene}")


@beat_app.command("suggest")
def suggest(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    scene: Annotated[str, typer.Option("--scene", "-s", help="Scene ID for context.")],
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path.")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    base_url: str | None = base_url_option(),
    api_key: str | None = api_key_option(),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Add without confirmation.")] = False,
) -> None:
    """Suggest a new beat for a scene.

    Example:
        fabulae beat suggest ./my-novel --scene scene-01 --idea "escalate tension"
    """
    project = load_project(project_dir)

    scene_obj = find_scene_by_id(project, scene)
    if not scene_obj:
        typer.echo(f"Error: Scene '{scene}' not found.", err=True)
        raise typer.Exit(code=1)

    # Resolve idea input
    guidance = resolve_idea_input(idea) if idea else None

    # Build prompt and get suggestion
    config = resolve_config(model, base_url, api_key, temperature, None)
    prompt = build_beat_suggest_prompt(scene_obj, project, guidance)

    typer.echo("Generating beat suggestion...")
    suggestion = suggest_entity_sync(BeatSuggestion, prompt, config)

    # Display suggestion
    console.print("\n[bold]Suggested beat:[/bold]")
    console.print(f"  ID: {suggestion.id}")
    console.print(f"  Kind: {suggestion.kind}")
    if suggestion.summary:
        console.print(f"  Summary: {suggestion.summary}")
    if suggestion.goal:
        console.print(f"  Goal: {suggestion.goal}")
    if suggestion.conflict:
        console.print(f"  Conflict: {suggestion.conflict}")
    if suggestion.outcome:
        console.print(f"  Outcome: {suggestion.outcome}")
    console.print()

    # Confirm and add
    if yes or confirm("Add this beat?"):
        # Check for duplicate ID
        existing_ids = get_all_entity_ids(project)
        if suggestion.id in existing_ids:
            typer.echo(f"Error: ID '{suggestion.id}' already exists. Try again or use 'beat add' manually.", err=True)
            raise typer.Exit(code=1)

        beat = Beat(
            id=suggestion.id,
            kind=suggestion.kind,
            summary=suggestion.summary,
            goal=suggestion.goal,
            conflict=suggestion.conflict,
            outcome=suggestion.outcome,
        )
        scene_obj.beats.append(beat)
        save_project(project, project_dir)
        typer.echo(f"Added beat: {suggestion.id} to scene {scene}")
    else:
        typer.echo("Beat not added.")


@beat_app.command("list")
def list_beats(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    scene: Annotated[str | None, typer.Option("--scene", "-s", help="Filter by scene ID.")] = None,
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, yaml.")] = "table",
) -> None:
    """List beats in the project.

    Example:
        fabulae beat list ./my-novel --scene scene-01
    """
    project = load_project(project_dir)

    # Collect beats with scene info
    beats_data: list[dict[str, object]] = []
    for s in project.plot.scenes:
        if scene and s.id != scene:
            continue
        for beat in s.beats:
            beats_data.append(
                {
                    "scene_id": s.id,
                    "id": beat.id,
                    "kind": beat.kind,
                    "summary": beat.summary,
                }
            )

    if not beats_data:
        if scene:
            typer.echo(f"No beats in scene '{scene}'.")
        else:
            typer.echo("No beats in project.")
        return

    if format == "table":
        table = Table(title="Beats")
        table.add_column("Scene", style="cyan")
        table.add_column("ID", style="green")
        table.add_column("Kind")
        table.add_column("Summary")

        for b in beats_data:
            summary = str(b["summary"] or "")[:40]
            if b["summary"] and len(str(b["summary"])) > 40:
                summary += "..."
            table.add_row(str(b["scene_id"]), str(b["id"]), str(b["kind"]), summary)

        console.print(table)

    elif format == "json":
        typer.echo(json.dumps(beats_data, indent=2))

    elif format == "yaml":
        typer.echo(yaml.dump(beats_data, default_flow_style=False, allow_unicode=True))

    else:
        typer.echo(f"Unknown format: {format}. Use table, json, or yaml.", err=True)
        raise typer.Exit(code=1)


@beat_app.command("move")
def move(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    beat_id: Annotated[str, typer.Argument(help="Beat ID to move.")],
    to_scene: Annotated[str, typer.Option("--to-scene", help="Target scene ID.")],
    position: Annotated[
        int | None, typer.Option("--position", "-p", help="Position in target scene (0-indexed).")
    ] = None,
) -> None:
    """Move a beat to a different scene.

    Example:
        fabulae beat move ./my-novel beat-discovery --to-scene scene-02 --position 0
    """
    project = load_project(project_dir)

    # Find the beat
    result = _find_beat_in_project(project, beat_id)
    if not result:
        typer.echo(f"Error: Beat '{beat_id}' not found.", err=True)
        raise typer.Exit(code=1)

    from fabulae.models import Scene

    source_scene, beat = result
    if not isinstance(source_scene, Scene):
        typer.echo("Error: Invalid scene object.", err=True)
        raise typer.Exit(code=1)

    # Find target scene
    target_scene = find_scene_by_id(project, to_scene)
    if not target_scene:
        typer.echo(f"Error: Target scene '{to_scene}' not found.", err=True)
        raise typer.Exit(code=1)

    # Remove from source
    source_scene.beats = [b for b in source_scene.beats if b.id != beat_id]

    # Add to target
    if position is not None:
        target_scene.beats.insert(position, beat)
    else:
        target_scene.beats.append(beat)

    save_project(project, project_dir)
    typer.echo(f"Moved beat '{beat_id}' from '{source_scene.id}' to '{to_scene}'")


@beat_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    beat_id: Annotated[str, typer.Argument(help="Beat ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
) -> None:
    """Remove a beat from the project.

    Example:
        fabulae beat remove ./my-novel beat-discovery
    """
    project = load_project(project_dir)

    # Find the beat
    result = _find_beat_in_project(project, beat_id)
    if not result:
        typer.echo(f"Error: Beat '{beat_id}' not found.", err=True)
        raise typer.Exit(code=1)

    from fabulae.models import Scene

    scene, beat = result
    if not isinstance(scene, Scene):
        typer.echo("Error: Invalid scene object.", err=True)
        raise typer.Exit(code=1)

    if not force and not confirm(f"Remove beat '{beat_id}' from scene '{scene.id}'?"):
        typer.echo("Beat not removed.")
        return

    scene.beats = [b for b in scene.beats if b.id != beat_id]
    save_project(project, project_dir)
    typer.echo(f"Removed beat: {beat_id}")


@beat_app.command("edit")
def edit(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    beat_id: Annotated[str, typer.Argument(help="Beat ID to edit.")],
    kind: Annotated[str | None, typer.Option("--kind", "-k", help="New beat type.")] = None,
    summary: Annotated[str | None, typer.Option("--summary", help="New summary.")] = None,
    goal: Annotated[str | None, typer.Option("--goal", help="New goal.")] = None,
    conflict: Annotated[str | None, typer.Option("--conflict", help="New conflict.")] = None,
    outcome: Annotated[str | None, typer.Option("--outcome", help="New outcome.")] = None,
    pace: Annotated[str | None, typer.Option("--pace", help="New pace.")] = None,
    target_words: Annotated[int | None, typer.Option("--target-words", help="New target word count.")] = None,
    add_constraint: Annotated[list[str] | None, typer.Option("--add-constraint", help="Add a constraint.")] = None,
    remove_constraint: Annotated[
        list[str] | None, typer.Option("--remove-constraint", help="Remove a constraint (by exact text).")
    ] = None,
) -> None:
    """Edit an existing beat.

    Example:
        fabulae beat edit ./my-novel beat-discovery --kind action --summary "Vera examines the evidence"
    """
    project = load_project(project_dir)

    # Find the beat
    result = _find_beat_in_project(project, beat_id)
    if not result:
        typer.echo(f"Error: Beat '{beat_id}' not found.", err=True)
        raise typer.Exit(code=1)

    _, beat = result

    # Update only provided fields
    if kind is not None:
        beat.kind = kind
    if summary is not None:
        beat.summary = summary
    if goal is not None:
        beat.goal = goal
    if conflict is not None:
        beat.conflict = conflict
    if outcome is not None:
        beat.outcome = outcome
    if pace is not None:
        beat.pace = pace
    if target_words is not None:
        beat.target_words = target_words

    # Handle constraint modifications
    if add_constraint:
        for constraint in add_constraint:
            if constraint not in beat.constraints:
                beat.constraints.append(constraint)
    if remove_constraint:
        beat.constraints = [c for c in beat.constraints if c not in remove_constraint]

    save_project(project, project_dir)
    typer.echo(f"Updated beat: {beat_id}")
