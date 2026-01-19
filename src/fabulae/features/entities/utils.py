"""Shared utilities for entity commands."""

import re
from pathlib import Path

import typer

from fabulae.models import Character, Project, Scene, WorldFact

# Pattern for valid entity IDs: lowercase alphanumeric with hyphens
ENTITY_ID_PATTERN = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


def validate_entity_id(id: str) -> None:
    """Validate entity ID format before model creation.

    Raises typer.Exit with code 1 if the ID is invalid.
    """
    if not ENTITY_ID_PATTERN.match(id):
        typer.echo(
            f"Error: Invalid ID '{id}'. IDs must be lowercase alphanumeric with hyphens "
            "(e.g., 'my-character-01', 'scene-intro').",
            err=True,
        )
        raise typer.Exit(code=1)


def resolve_idea_input(idea: str) -> str:
    """Resolve --idea parameter: if it's a file path that exists, read its contents.
    Otherwise, return the string as-is.
    """
    path = Path(idea)
    if path.exists() and path.is_file():
        return path.read_text().strip()
    return idea


def confirm(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation."""
    return typer.confirm(message, default=default)


def format_existing_characters(characters: list[Character]) -> str:
    """Format existing characters for prompt context."""
    if not characters:
        return "No existing characters."
    lines = []
    for c in characters:
        line = f"- {c.name} ({c.id}): {c.role or 'unspecified role'}"
        if c.desire:
            line += f" - wants: {c.desire}"
        lines.append(line)
    return "\n".join(lines)


def format_existing_scenes(scenes: list[Scene]) -> str:
    """Format existing scenes for prompt context."""
    if not scenes:
        return "No existing scenes."
    return "\n".join([f"- {s.id}: {s.summary[:50] if s.summary else 'No summary'}" for s in scenes])


def format_existing_world_facts(facts: list[WorldFact]) -> str:
    """Format existing world facts for prompt context."""
    if not facts:
        return "No world facts defined."
    lines = []
    for f in facts:
        fact_preview = ", ".join(f.facts[:2]) if f.facts else "No details"
        lines.append(f"- {f.id} [{f.type}]: {f.name} - {fact_preview}")
    return "\n".join(lines)


def find_character_by_id(project: Project, character_id: str) -> Character | None:
    """Find a character by ID in the project."""
    for char in project.characters:
        if char.id == character_id:
            return char
    return None


def find_scene_by_id(project: Project, scene_id: str) -> Scene | None:
    """Find a scene by ID in the project."""
    for scene in project.plot.scenes:
        if scene.id == scene_id:
            return scene
    return None


def find_world_fact_by_id(project: Project, fact_id: str) -> WorldFact | None:
    """Find a world fact by ID in the project."""
    if not project.world:
        return None
    for fact in project.world.facts:
        if fact.id == fact_id:
            return fact
    return None


def get_character_references(project: Project, character_id: str) -> list[str]:
    """Get list of scene IDs that reference a character."""
    references = []
    for scene in project.plot.scenes:
        if character_id in scene.characters:
            references.append(scene.id)
    return references


def get_world_fact_references(project: Project, fact_id: str) -> list[str]:
    """Get list of scene IDs that reference a world fact."""
    references = []
    for scene in project.plot.scenes:
        if scene.location == fact_id:
            references.append(f"{scene.id} (location)")
        if fact_id in scene.world_fact_ids:
            references.append(f"{scene.id} (world_fact)")
    return references


def generate_next_id(prefix: str, existing_ids: set[str]) -> str:
    """Generate the next sequential ID with the given prefix."""
    n = 1
    while True:
        new_id = f"{prefix}-{n:02d}"
        if new_id not in existing_ids:
            return new_id
        n += 1


def get_all_entity_ids(project: Project) -> set[str]:
    """Get all entity IDs in the project."""
    ids: set[str] = set()
    for char in project.characters:
        ids.add(char.id)
    if project.world:
        for fact in project.world.facts:
            ids.add(fact.id)
    for chapter in project.plot.chapters:
        ids.add(chapter.id)
    for scene in project.plot.scenes:
        ids.add(scene.id)
        for beat in scene.beats:
            ids.add(beat.id)
    for fragment in project.plot.fragments:
        ids.add(fragment.id)
    for stanza in project.plot.stanzas:
        ids.add(stanza.id)
    return ids
