"""Chapter CRUD commands for Fabulae projects."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from fabulae.cli_options import api_key_option, base_url_option, model_option, temperature_option
from fabulae.features.entities.generation.chapter import suggest_chapter_sync
from fabulae.features.entities.utils import (
    confirm,
    find_chapter_by_id,
    get_all_entity_ids,
    output_list_as_json,
    output_list_as_yaml,
    require_prose_format,
    resolve_idea_input,
    validate_entity_id,
    validate_output_format,
)
from fabulae.llm import resolve_config
from fabulae.models import Chapter, load_project, save_project

chapter_app = typer.Typer(help="Manage chapters in a Fabulae project.")
console = Console()


@chapter_app.command("add")
def add(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    id: Annotated[str, typer.Option("--id", help="Chapter ID (lowercase-with-hyphens).")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="Chapter title.")] = None,
    summary: Annotated[str | None, typer.Option("--summary", help="Chapter summary.")] = None,
) -> None:
    """Add a new chapter to the project.

    Example:
        fabulae chapter add ./my-novel --id chapter-03 --title "The Revelation"
    """
    validate_entity_id(id)
    project = load_project(project_dir)
    require_prose_format(project, "chapter add")

    if id in get_all_entity_ids(project):
        typer.echo(f"Error: ID '{id}' already exists in project.", err=True)
        raise typer.Exit(code=1)

    chapter = Chapter(
        id=id,
        title=title,
        summary=summary,
        scene_ids=[],
    )
    project.plot.chapters.append(chapter)
    save_project(project, project_dir)
    typer.echo(f"Added chapter: {title or id} ({id})")


@chapter_app.command("suggest")
def suggest(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path.")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    base_url: str | None = base_url_option(),
    api_key: str | None = api_key_option(),
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Add without confirmation.")] = False,
) -> None:
    """Suggest a new chapter based on project context.

    Example:
        fabulae chapter suggest ./my-novel --idea "a climactic confrontation"
    """
    project = load_project(project_dir)
    require_prose_format(project, "chapter suggest")
    guidance = resolve_idea_input(idea) if idea else None
    config = resolve_config(model, base_url, api_key, temperature, None)

    typer.echo("Generating chapter suggestion...")
    chapter = suggest_chapter_sync(project=project, guidance=guidance, config=config)

    console.print("\n[bold]Suggested chapter:[/bold]")
    console.print(f"  ID: {chapter.id}")
    if chapter.title:
        console.print(f"  Title: {chapter.title}")
    if chapter.summary:
        console.print(f"  Summary: {chapter.summary}")
    console.print()

    if yes or confirm("Add this chapter?"):
        if chapter.id in get_all_entity_ids(project):
            typer.echo(
                f"Error: ID '{chapter.id}' already exists. Try again or use 'chapter add' manually.",
                err=True,
            )
            raise typer.Exit(code=1)

        project.plot.chapters.append(chapter)
        save_project(project, project_dir)
        typer.echo(f"Added chapter: {chapter.title or chapter.id} ({chapter.id})")
    else:
        typer.echo("Chapter not added.")


@chapter_app.command("list")
def list_chapters(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    format: Annotated[str, typer.Option("--format", "-f", help="Output format: table, json, yaml.")] = "table",
) -> None:
    """List chapters in the project.

    Example:
        fabulae chapter list ./my-novel
    """
    project = load_project(project_dir)
    require_prose_format(project, "chapter list")

    if not project.plot.chapters:
        typer.echo("No chapters in project.")
        return

    validate_output_format(format)

    if format == "table":
        table = Table(title="Chapters")
        table.add_column("ID", style="cyan")
        table.add_column("Title", style="green")
        table.add_column("Scenes")
        table.add_column("Summary")

        for chapter in project.plot.chapters:
            scene_count = len(chapter.scene_ids) if chapter.scene_ids else 0
            if chapter.summary and len(chapter.summary) > 40:
                summary = chapter.summary[:40] + "..."
            else:
                summary = chapter.summary or ""
            table.add_row(chapter.id, chapter.title or "", str(scene_count), summary)

        console.print(table)
    elif format == "json":
        output_list_as_json(project.plot.chapters)
    elif format == "yaml":
        output_list_as_yaml(project.plot.chapters)


@chapter_app.command("remove")
def remove(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    chapter_id: Annotated[str, typer.Argument(help="Chapter ID to remove.")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation.")] = False,
    move_scenes_to: Annotated[
        str | None, typer.Option("--move-scenes-to", help="Move scenes to this chapter before removal.")
    ] = None,
    cascade: Annotated[bool, typer.Option("--cascade", help="Delete the chapter AND all its scenes.")] = False,
) -> None:
    """Remove a chapter from the project.

    If the chapter contains scenes, you must specify how to handle them:
      --move-scenes-to <chapter-id>  Move scenes to another chapter first
      --cascade                      Delete the chapter AND its scenes

    Example:
        fabulae chapter remove ./my-novel chapter-03 --move-scenes-to chapter-02
        fabulae chapter remove ./my-novel chapter-03 --cascade
    """
    project = load_project(project_dir)
    require_prose_format(project, "chapter remove")

    chapter = find_chapter_by_id(project, chapter_id)
    if not chapter:
        typer.echo(f"Error: Chapter '{chapter_id}' not found.", err=True)
        raise typer.Exit(code=1)

    if chapter.scene_ids:
        scene_count = len(chapter.scene_ids)

        if not move_scenes_to and not cascade:
            typer.echo(f"Error: Chapter '{chapter_id}' contains {scene_count} scene(s).", err=True)
            typer.echo("Use one of the following options:", err=True)
            typer.echo("  --move-scenes-to <chapter-id>  Move scenes to another chapter first", err=True)
            typer.echo("  --cascade                      Delete the chapter AND its scenes", err=True)
            raise typer.Exit(code=1)

        if move_scenes_to:
            target_chapter = find_chapter_by_id(project, move_scenes_to)
            if not target_chapter:
                typer.echo(f"Error: Target chapter '{move_scenes_to}' not found.", err=True)
                raise typer.Exit(code=1)
            if target_chapter.scene_ids is None:
                target_chapter.scene_ids = []
            target_chapter.scene_ids.extend(chapter.scene_ids)
            typer.echo(f"Moved {scene_count} scene(s) to '{move_scenes_to}'")

        elif cascade:
            beat_count = sum(len(scene.beats) for scene in project.plot.scenes if scene.id in chapter.scene_ids)
            if beat_count > 0:
                typer.echo(f"Warning: This will delete {scene_count} scene(s) and {beat_count} beat(s).")
            else:
                typer.echo(f"Warning: This will delete {scene_count} scene(s).")
            if not force and not confirm("Continue?"):
                typer.echo("Chapter not removed.")
                return
            scene_ids_to_delete = set(chapter.scene_ids)
            project.plot.scenes = [s for s in project.plot.scenes if s.id not in scene_ids_to_delete]

    elif not force and not confirm(f"Remove chapter '{chapter.title or chapter_id}' ({chapter_id})?"):
        typer.echo("Chapter not removed.")
        return

    project.plot.chapters = [c for c in project.plot.chapters if c.id != chapter_id]
    save_project(project, project_dir)
    typer.echo(f"Removed chapter: {chapter_id}")


@chapter_app.command("edit")
def edit(
    project_dir: Annotated[Path, typer.Argument(help="Project directory.")],
    chapter_id: Annotated[str, typer.Argument(help="Chapter ID to edit.")],
    title: Annotated[str | None, typer.Option("--title", "-t", help="New title.")] = None,
    summary: Annotated[str | None, typer.Option("--summary", help="New summary.")] = None,
) -> None:
    """Edit an existing chapter.

    Example:
        fabulae chapter edit ./my-novel chapter-03 --title "The Big Reveal"
    """
    project = load_project(project_dir)
    require_prose_format(project, "chapter edit")

    chapter = find_chapter_by_id(project, chapter_id)
    if not chapter:
        typer.echo(f"Error: Chapter '{chapter_id}' not found.", err=True)
        raise typer.Exit(code=1)

    if title is not None:
        chapter.title = title if title else None
    if summary is not None:
        chapter.summary = summary if summary else None

    save_project(project, project_dir)
    typer.echo(f"Updated chapter: {chapter_id}")
