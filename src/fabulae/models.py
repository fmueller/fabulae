"""Pydantic models for Fabulae narrative data structures."""

from __future__ import annotations

import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _validate_id(value: str) -> str:
    """Validate that an ID is lowercase with hyphens, no spaces."""
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", value):
        raise ValueError(f"ID must be lowercase alphanumeric with hyphens, no spaces: {value!r}")
    return value


EntityId = Annotated[str, Field(min_length=1), AfterValidator(_validate_id)]


LiteratureFormat = Literal["novel", "novella", "short-story", "micro-prose", "poem"]

AVAILABLE_FORMATS: list[LiteratureFormat] = [
    "novel",
    "novella",
    "short-story",
    "micro-prose",
    "poem",
]


class SemanticTag(BaseModel):
    """A labeled semantic tag with optional notes."""

    id: EntityId
    label: str
    notes: str | None = None


SemanticValue = str | SemanticTag


class Hook(BaseModel):
    """The story hook (line, question, promise)."""

    line: str | None = None
    question: str | None = None
    promise: str | None = None


class Stakes(BaseModel):
    """Stakes for the plot."""

    external: str | None = None
    internal: str | None = None


class Character(BaseModel):
    """A character in the story."""

    id: EntityId
    name: str
    role: str | None = None
    desire: str | None = None
    need: str | None = None
    flaw: str | None = None
    secret: str | None = None
    traits: list[str] = Field(default_factory=list)


class WorldFact(BaseModel):
    """A world-building element (location, culture, history, rule, or object)."""

    id: EntityId
    type: Literal["location", "culture", "history", "rule", "object"]
    name: str
    facts: list[str] = Field(default_factory=list)


class World(BaseModel):
    """World metadata and facts."""

    setting: str | None = None
    time_period: str | None = None
    tone: str | None = None
    motifs: list[SemanticValue] = Field(default_factory=list)
    facts: list[WorldFact] = Field(default_factory=list)


class Beat(BaseModel):
    """A dramatic beat inside a scene."""

    id: EntityId
    kind: str = Field(min_length=1)
    summary: str | None = None
    target_words: int | None = Field(default=None, ge=1)
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    pace: str | None = None
    constraints: list[str] = Field(default_factory=list)


class Scene(BaseModel):
    """A scene in the narrative."""

    id: EntityId
    location: EntityId | None = None
    time: str | None = None
    characters: list[EntityId] = Field(default_factory=list)
    world_fact_ids: list[EntityId] = Field(default_factory=list)
    summary: str | None = None
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    beats: list[Beat] = Field(default_factory=list)


class Chapter(BaseModel):
    """A chapter that groups scenes."""

    id: EntityId
    title: str | None = None
    summary: str | None = None
    scene_ids: list[EntityId] | None = None


class Stanza(BaseModel):
    """A stanza in a poem."""

    id: EntityId
    lines: list[str] = Field(default_factory=list)
    meter: str | None = None
    rhyme_scheme: str | None = None


class Fragment(BaseModel):
    """A micro-prose fragment or paragraph."""

    id: EntityId
    content: str
    target_words: int | None = Field(default=None, ge=1)
    notes: str | None = None


class Plot(BaseModel):
    """Plot metadata and narrative structure.

    Supports multiple narrative formats:
    - novel/novella/short-story: use chapters, scenes, beats
    - micro-prose: use fragments
    - poem: use stanzas or lines
    """

    # Format specification
    format: LiteratureFormat | None = "novel"

    # Common metadata (all formats)
    title: str | None = None
    premise: str
    themes: list[SemanticValue] = Field(default_factory=list)
    hook: Hook | None = None
    stakes: Stakes | None = None

    # Prose formats (novel, novella, short-story)
    chapters: list[Chapter] = Field(default_factory=list)
    scenes: list[Scene] = Field(default_factory=list)
    scene_ids: list[EntityId] | None = None

    # Micro-prose format
    fragments: list[Fragment] = Field(default_factory=list)

    # Poetry format
    stanzas: list[Stanza] = Field(default_factory=list)
    lines: list[str] = Field(default_factory=list)  # for non-stanza poetry (e.g., haiku)
    poem_form: str | None = None  # sonnet, haiku, villanelle, free verse, etc.
    poem_meter: str | None = None
    poem_rhyme_scheme: str | None = None


class Style(BaseModel):
    """Narrative style guidance."""

    model_config = ConfigDict(populate_by_name=True)

    language: str | None = None
    pov: str | None = None
    tense: str | None = None
    voice: str | None = None
    register_: str | None = Field(default=None, alias="register")
    constraints: list[str] = Field(default_factory=list)


class CharacterSlot(BaseModel):
    """A character slot in a story shape that must be filled."""

    slot: str = Field(min_length=1)
    needs: str = Field(min_length=1)
    can_merge_with: list[str] = Field(default_factory=list)
    optional: bool = False


class SettingSlot(BaseModel):
    """A setting/location slot in a story shape."""

    slot: str = Field(min_length=1)
    needs: str = Field(min_length=1)
    used_in: list[str] = Field(default_factory=list)
    optional: bool = False


class RequiredBeat(BaseModel):
    """A required beat in a story shape."""

    type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    position: Literal["early", "middle", "late", "climax", "anywhere"] = "anywhere"
    flexibility: Literal["fixed", "flexible", "very-flexible"] = "flexible"


class VariationPoint(BaseModel):
    """A point of variation in a story shape."""

    type: str = Field(min_length=1)
    description: str = Field(min_length=1)
    probability: float = Field(ge=0.0, le=1.0)
    position: Literal["early", "middle", "late", "climax", "anywhere"] = "anywhere"


class StoryShape(BaseModel):
    """A reusable story structure pattern defining slots, beats, and variation points."""

    id: EntityId
    name: str = Field(min_length=1)
    description: str = Field(min_length=1)
    character_slots: list[CharacterSlot] = Field(default_factory=list)
    setting_slots: list[SettingSlot] = Field(default_factory=list)
    required_beats: list[RequiredBeat] = Field(default_factory=list)
    variation_points: list[VariationPoint] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    motifs: list[str] = Field(default_factory=list)
    tone: str | None = None


class ProjectPaths(BaseModel):
    """Configurable file paths for project data."""

    plot: str = "plot.yml"
    characters: str = "characters.yml"
    world: str = "world.yml"
    style: str = "style.yml"


class ProjectDefaults(BaseModel):
    """Default values used when content omits them."""

    language: str | None = None


class GenerationMetadata(BaseModel):
    """Metadata about how the project was generated."""

    generated_at: datetime
    generator_version: str
    original_idea: str
    model: str
    temperature: float
    shape: str | None = None
    shape_file: str | None = None
    no_shape: bool | None = None  # True if user explicitly used --no-shape
    variation: float
    seed: int | None = None
    enrichment_enabled: bool
    format: str
    language: str | None = None


class ProjectConfig(BaseModel):
    """Project configuration loaded from fabulae.yml."""

    version: str | None = None
    title: str | None = None
    paths: ProjectPaths | None = None
    defaults: ProjectDefaults | None = None
    metadata: GenerationMetadata | None = None


class CharactersFile(BaseModel):
    """Wrapper for characters.yml."""

    characters: list[Character] = Field(default_factory=list)


class Project(BaseModel):
    """Fully loaded Fabulae project."""

    config: ProjectConfig
    plot: Plot
    characters: list[Character] = Field(default_factory=list)
    world: World | None = None
    style: Style | None = None


def load_yaml_file(path: Path) -> dict[str, object]:
    """Load a YAML file and return its contents as a dictionary."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml_file(path: Path, data: dict[str, object]) -> None:
    """Save a dictionary to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(
            data,
            f,
            Dumper=yaml.SafeDumper,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )


def _dump_plot(plot: Plot) -> dict[str, object]:
    data = plot.model_dump(exclude_none=True, exclude_defaults=True)
    if plot.format is not None:
        data["format"] = plot.format
    return data


def _validate_unique_ids(project: Project) -> None:
    id_sources: dict[str, list[str]] = defaultdict(list)

    for character in project.characters:
        id_sources[character.id].append("character")

    if project.world:
        for fact in project.world.facts:
            id_sources[fact.id].append("world_fact")

    for chapter in project.plot.chapters:
        id_sources[chapter.id].append("chapter")

    for scene in project.plot.scenes:
        id_sources[scene.id].append("scene")
        for beat in scene.beats:
            id_sources[beat.id].append("beat")

    for fragment in project.plot.fragments:
        id_sources[fragment.id].append("fragment")

    for stanza in project.plot.stanzas:
        id_sources[stanza.id].append("stanza")

    duplicates = {id_value: sources for id_value, sources in id_sources.items() if len(sources) > 1}
    if duplicates:
        details = ", ".join(
            f"{id_value} ({', '.join(sorted(sources))})" for id_value, sources in sorted(duplicates.items())
        )
        raise ValueError(f"Duplicate IDs detected: {details}")


def _validate_scene_order(plot: Plot) -> None:
    scene_ids = {scene.id for scene in plot.scenes}

    if plot.chapters:
        if plot.scene_ids:
            raise ValueError("plot.scene_ids is only allowed when no chapters are defined.")

        # Validate each chapter's scene_ids
        all_referenced_scenes: set[EntityId] = set()
        for chapter in plot.chapters:
            if chapter.scene_ids is None:
                continue

            if len(set(chapter.scene_ids)) != len(chapter.scene_ids):
                raise ValueError(f"Chapter {chapter.id!r} has duplicate scene IDs.")

            # Check for unknown scenes
            unknown = set(chapter.scene_ids) - scene_ids
            if unknown:
                raise ValueError(f"Chapter {chapter.id!r} references unknown scenes: {sorted(unknown)!r}.")

            # Check for scenes referenced by multiple chapters
            duplicates = all_referenced_scenes & set(chapter.scene_ids)
            if duplicates:
                raise ValueError(
                    f"Chapter {chapter.id!r} references scenes already in another chapter: {sorted(duplicates)!r}."
                )
            all_referenced_scenes.update(chapter.scene_ids)

        # Check for orphan scenes (scenes not in any chapter)
        orphan_scenes = scene_ids - all_referenced_scenes
        if orphan_scenes:
            raise ValueError(f"Scenes not assigned to any chapter: {sorted(orphan_scenes)!r}.")
    else:
        if plot.scene_ids is None:
            return
        if len(set(plot.scene_ids)) != len(plot.scene_ids):
            raise ValueError("plot.scene_ids contains duplicate IDs.")
        missing = scene_ids - set(plot.scene_ids)
        extra = set(plot.scene_ids) - scene_ids
        if extra:
            raise ValueError(f"plot.scene_ids references unknown scenes: {sorted(extra)!r}.")
        if missing:
            raise ValueError(f"plot.scene_ids does not list all scenes: {sorted(missing)!r}.")


def _validate_references(project: Project) -> None:
    characters = {character.id for character in project.characters}
    world_facts = {fact.id: fact for fact in project.world.facts} if project.world else {}

    for scene in project.plot.scenes:
        if scene.characters:
            missing_chars = set(scene.characters) - characters
            if missing_chars:
                raise ValueError(f"Scene {scene.id!r} references unknown characters: {sorted(missing_chars)!r}.")

        if scene.location:
            if not world_facts:
                raise ValueError(
                    f"Scene {scene.id!r} references location {scene.location!r} but world facts are missing."
                )
            if scene.location not in world_facts:
                raise ValueError(f"Scene {scene.id!r} references unknown location {scene.location!r}.")
            if world_facts[scene.location].type != "location":
                raise ValueError(
                    f"Scene {scene.id!r} location {scene.location!r} is not a world fact of type 'location'."
                )

        if scene.world_fact_ids:
            missing_facts = set(scene.world_fact_ids) - set(world_facts)
            if missing_facts:
                raise ValueError(f"Scene {scene.id!r} references unknown world facts: {sorted(missing_facts)!r}.")


def _validate_format(plot: Plot) -> None:
    """Validate that format-appropriate fields are populated."""
    fmt = plot.format or "novel"

    prose_formats = {"novel", "novella", "short-story"}
    has_prose = bool(plot.chapters or plot.scenes)
    has_micro_prose = bool(plot.fragments)
    has_poetry = bool(plot.stanzas or plot.lines)

    if fmt in prose_formats:
        if has_micro_prose:
            raise ValueError(f"Format {fmt!r} should not have fragments (use scenes/chapters instead).")
        if has_poetry:
            raise ValueError(f"Format {fmt!r} should not have stanzas/lines (use scenes/chapters instead).")
        if not plot.scenes:
            raise ValueError(f"Format {fmt!r} requires at least one scene.")

    elif fmt == "micro-prose":
        if has_prose or plot.scene_ids:
            raise ValueError("Format 'micro-prose' should use fragments, not scenes/chapters.")
        if has_poetry:
            raise ValueError("Format 'micro-prose' should not have stanzas/lines.")
        if not has_micro_prose:
            raise ValueError("Format 'micro-prose' requires at least one fragment.")

    elif fmt == "poem":
        if has_prose or plot.scene_ids:
            raise ValueError("Format 'poem' should not have scenes/chapters.")
        if has_micro_prose:
            raise ValueError("Format 'poem' should not have fragments.")
        if not has_poetry:
            raise ValueError("Format 'poem' requires stanzas or lines.")


def _validate_project(project: Project) -> None:
    _validate_format(project.plot)
    _validate_unique_ids(project)
    _validate_scene_order(project.plot)
    _validate_references(project)


def load_project(path: Path) -> Project:
    """Load an entire Fabulae project from a directory."""
    config_path = path / "fabulae.yml"
    if not config_path.exists():
        raise FileNotFoundError(f"Project manifest not found: {config_path}")

    config_data = load_yaml_file(config_path)
    config = ProjectConfig.model_validate(config_data)

    paths = config.paths or ProjectPaths()

    plot_path = path / paths.plot
    if not plot_path.exists():
        raise FileNotFoundError(f"Plot file not found: {plot_path}")
    plot = Plot.model_validate(load_yaml_file(plot_path))

    characters_path = path / paths.characters
    characters: list[Character] = []
    if characters_path.exists():
        characters_data = CharactersFile.model_validate(load_yaml_file(characters_path))
        characters = characters_data.characters

    world_path = path / paths.world
    world = World.model_validate(load_yaml_file(world_path)) if world_path.exists() else None

    style_path = path / paths.style
    style = Style.model_validate(load_yaml_file(style_path)) if style_path.exists() else None

    project = Project(
        config=config,
        plot=plot,
        characters=characters,
        world=world,
        style=style,
    )
    _validate_project(project)
    return project


def save_project(project: Project, path: Path) -> None:
    """Save a Fabulae project to a directory structure."""
    _validate_project(project)
    path.mkdir(parents=True, exist_ok=True)

    config = project.config
    paths = config.paths or ProjectPaths()
    save_yaml_file(path / "fabulae.yml", config.model_dump(exclude_none=True))

    plot_path = path / paths.plot
    save_yaml_file(plot_path, _dump_plot(project.plot))

    characters_path = path / paths.characters
    save_yaml_file(
        characters_path,
        CharactersFile(characters=project.characters).model_dump(exclude_none=True),
    )

    if project.world:
        world_path = path / paths.world
        save_yaml_file(world_path, project.world.model_dump(exclude_none=True))

    if project.style:
        style_path = path / paths.style
        save_yaml_file(style_path, project.style.model_dump(exclude_none=True, by_alias=True))
