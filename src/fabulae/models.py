"""Pydantic models for Fabulae narrative data structures."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _validate_id(value: str) -> str:
    """Validate that an ID is lowercase with hyphens, no spaces."""
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", value):
        raise ValueError(
            f"ID must be lowercase alphanumeric with hyphens, no spaces: {value!r}"
        )
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


class PlotPatternRole(BaseModel):
    """An abstract role within a plot pattern."""

    id: EntityId
    description: str
    required: bool = True


class PlotPatternBeat(BaseModel):
    """A required beat in a plot pattern."""

    type: str = Field(min_length=1)
    description: str


class PlotPattern(BaseModel):
    """A reusable plot structure pattern (writer-native alternative to microplots)."""

    id: EntityId
    name: str
    description: str
    roles: list[PlotPatternRole] = Field(default_factory=list)
    required_beats: list[PlotPatternBeat] = Field(default_factory=list)


class PlotPatternBeatAssignment(BaseModel):
    """Map a plot pattern beat to a scene (and optional scene beat)."""

    type: str = Field(min_length=1)
    scene: EntityId
    scene_beat: EntityId | None = None
    notes: str | None = None


class NarrativeRole(BaseModel):
    """An abstract role within a narrative pattern."""

    id: EntityId
    description: str
    required: bool = True


class NarrativePattern(BaseModel):
    """A reusable narrative system bundling plot, theme, and world cues."""

    id: EntityId
    name: str
    description: str
    plot_pattern: EntityId | None = None
    roles: list[NarrativeRole] = Field(default_factory=list)
    themes: list[SemanticValue] = Field(default_factory=list)
    motifs: list[SemanticValue] = Field(default_factory=list)
    setting: str | None = None
    time_period: str | None = None
    tone: str | None = None
    notes: list[str] = Field(default_factory=list)


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
    chapter: EntityId | None = None
    location: EntityId | None = None
    time: str | None = None
    characters: list[EntityId] = Field(default_factory=list)
    world_fact_ids: list[EntityId] = Field(default_factory=list)
    plot_pattern: EntityId | None = None
    plot_pattern_beat: str | None = None
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
    plot_pattern: EntityId | None = None
    plot_pattern_beats: list[PlotPatternBeatAssignment] = Field(default_factory=list)
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


class ProjectPaths(BaseModel):
    """Configurable file paths for project data."""

    plot: str = "plot.yml"
    characters: str = "characters.yml"
    world: str = "world.yml"
    style: str = "style.yml"
    plot_patterns: str = "plot_patterns.yml"
    narrative_patterns: str = "narrative_patterns.yml"


class ProjectDefaults(BaseModel):
    """Default values used when content omits them."""

    language: str | None = None


class ProjectConfig(BaseModel):
    """Project configuration loaded from fabulae.yml."""

    version: str | None = None
    title: str | None = None
    paths: ProjectPaths | None = None
    defaults: ProjectDefaults | None = None


class CharactersFile(BaseModel):
    """Wrapper for characters.yml."""

    characters: list[Character] = Field(default_factory=list)


class PlotPatternsFile(BaseModel):
    """Wrapper for plot_patterns.yml."""

    plot_patterns: list[PlotPattern] = Field(default_factory=list)


class NarrativePatternsFile(BaseModel):
    """Wrapper for narrative_patterns.yml."""

    narrative_patterns: list[NarrativePattern] = Field(default_factory=list)


class Project(BaseModel):
    """Fully loaded Fabulae project."""

    config: ProjectConfig
    plot: Plot
    characters: list[Character] = Field(default_factory=list)
    world: World | None = None
    style: Style | None = None
    plot_patterns: list[PlotPattern] = Field(default_factory=list)
    narrative_patterns: list[NarrativePattern] = Field(default_factory=list)


def load_yaml_file(path: Path) -> dict[str, object]:
    """Load a YAML file and return its contents as a dictionary."""
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def save_yaml_file(path: Path, data: dict[str, object]) -> None:
    """Save a dictionary to a YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)


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

    for pattern in project.plot_patterns:
        id_sources[pattern.id].append("plot_pattern")

    for narrative_pattern in project.narrative_patterns:
        id_sources[narrative_pattern.id].append("narrative_pattern")

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

        chapter_ids = {chapter.id for chapter in plot.chapters}
        for scene in plot.scenes:
            if scene.chapter is None:
                raise ValueError(f"Scene {scene.id!r} must reference a chapter when chapters exist.")
            if scene.chapter not in chapter_ids:
                raise ValueError(f"Scene {scene.id!r} references unknown chapter {scene.chapter!r}.")

        for chapter in plot.chapters:
            if chapter.scene_ids is None:
                continue

            if len(set(chapter.scene_ids)) != len(chapter.scene_ids):
                raise ValueError(f"Chapter {chapter.id!r} has duplicate scene IDs.")

            chapter_scene_ids = [scene.id for scene in plot.scenes if scene.chapter == chapter.id]
            missing = set(chapter_scene_ids) - set(chapter.scene_ids)
            extra = set(chapter.scene_ids) - set(chapter_scene_ids)
            if extra:
                raise ValueError(
                    f"Chapter {chapter.id!r} references unknown scenes: {sorted(extra)!r}."
                )
            if missing:
                raise ValueError(
                    f"Chapter {chapter.id!r} does not list all scenes: {sorted(missing)!r}."
                )
    else:
        if any(scene.chapter is not None for scene in plot.scenes):
            raise ValueError("Scenes must not reference chapters when no chapters are defined.")
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
    patterns = {pattern.id: pattern for pattern in project.plot_patterns}
    world_facts = {fact.id: fact for fact in project.world.facts} if project.world else {}
    scene_map = {scene.id: scene for scene in project.plot.scenes}

    if project.plot.plot_pattern and project.plot.plot_pattern not in patterns:
        raise ValueError(
            f"Plot references unknown plot pattern {project.plot.plot_pattern!r}."
        )

    if project.plot.plot_pattern_beats and not project.plot.plot_pattern:
        raise ValueError("plot.plot_pattern_beats requires plot.plot_pattern to be set.")

    if project.plot.plot_pattern and project.plot.plot_pattern_beats:
        beat_types = {beat.type for beat in patterns[project.plot.plot_pattern].required_beats}
        for assignment in project.plot.plot_pattern_beats:
            if assignment.type not in beat_types:
                raise ValueError(
                    f"Plot references unknown plot pattern beat {assignment.type!r}."
                )
            if assignment.scene not in scene_map:
                raise ValueError(
                    f"Plot plot_pattern_beats references unknown scene {assignment.scene!r}."
                )
            if assignment.scene_beat:
                scene_beat_ids = {beat.id for beat in scene_map[assignment.scene].beats}
                if assignment.scene_beat not in scene_beat_ids:
                    raise ValueError(
                        f"Plot plot_pattern_beats references unknown scene beat "
                        f"{assignment.scene_beat!r} in scene {assignment.scene!r}."
                    )

    for scene in project.plot.scenes:
        if scene.characters:
            missing_chars = set(scene.characters) - characters
            if missing_chars:
                raise ValueError(
                    f"Scene {scene.id!r} references unknown characters: {sorted(missing_chars)!r}."
                )

        if scene.location:
            if not world_facts:
                raise ValueError(
                    f"Scene {scene.id!r} references location {scene.location!r} but world facts are missing."
                )
            if scene.location not in world_facts:
                raise ValueError(
                    f"Scene {scene.id!r} references unknown location {scene.location!r}."
                )
            if world_facts[scene.location].type != "location":
                raise ValueError(
                    f"Scene {scene.id!r} location {scene.location!r} is not a world fact of type 'location'."
                )

        if scene.world_fact_ids:
            missing_facts = set(scene.world_fact_ids) - set(world_facts)
            if missing_facts:
                raise ValueError(
                    f"Scene {scene.id!r} references unknown world facts: {sorted(missing_facts)!r}."
                )

        if scene.plot_pattern_beat and not scene.plot_pattern:
            raise ValueError(
                f"Scene {scene.id!r} defines plot_pattern_beat without plot_pattern."
            )
        if scene.plot_pattern:
            if scene.plot_pattern not in patterns:
                raise ValueError(
                    f"Scene {scene.id!r} references unknown plot pattern {scene.plot_pattern!r}."
                )
            if scene.plot_pattern_beat:
                beat_types = {beat.type for beat in patterns[scene.plot_pattern].required_beats}
                if scene.plot_pattern_beat not in beat_types:
                    raise ValueError(
                        f"Scene {scene.id!r} references unknown plot pattern beat "
                        f"{scene.plot_pattern_beat!r}."
                    )

    for pattern in project.narrative_patterns:
        if pattern.plot_pattern and pattern.plot_pattern not in patterns:
            raise ValueError(
                f"Narrative pattern {pattern.id!r} references unknown plot pattern "
                f"{pattern.plot_pattern!r}."
            )


def _validate_format(plot: Plot) -> None:
    """Validate that format-appropriate fields are populated."""
    fmt = plot.format or "novel"

    prose_formats = {"novel", "novella", "short-story"}
    has_prose = bool(plot.chapters or plot.scenes)
    has_micro_prose = bool(plot.fragments)
    has_poetry = bool(plot.stanzas or plot.lines)
    has_plot_pattern = bool(plot.plot_pattern or plot.plot_pattern_beats)

    if fmt in prose_formats:
        if has_micro_prose:
            raise ValueError(
                f"Format {fmt!r} should not have fragments (use scenes/chapters instead)."
            )
        if has_poetry:
            raise ValueError(
                f"Format {fmt!r} should not have stanzas/lines (use scenes/chapters instead)."
            )
        if not plot.scenes:
            raise ValueError(f"Format {fmt!r} requires at least one scene.")

    elif fmt == "micro-prose":
        if has_prose or plot.scene_ids:
            raise ValueError(
                "Format 'micro-prose' should use fragments, not scenes/chapters."
            )
        if has_poetry:
            raise ValueError("Format 'micro-prose' should not have stanzas/lines.")
        if has_plot_pattern:
            raise ValueError("Format 'micro-prose' should not define plot patterns.")
        if not has_micro_prose:
            raise ValueError("Format 'micro-prose' requires at least one fragment.")

    elif fmt == "poem":
        if has_prose or plot.scene_ids:
            raise ValueError("Format 'poem' should not have scenes/chapters.")
        if has_micro_prose:
            raise ValueError("Format 'poem' should not have fragments.")
        if has_plot_pattern:
            raise ValueError("Format 'poem' should not define plot patterns.")
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

    patterns_path = path / paths.plot_patterns
    plot_patterns: list[PlotPattern] = []
    if patterns_path.exists():
        patterns_data = PlotPatternsFile.model_validate(load_yaml_file(patterns_path))
        plot_patterns = patterns_data.plot_patterns

    narrative_patterns_path = path / paths.narrative_patterns
    narrative_patterns: list[NarrativePattern] = []
    if narrative_patterns_path.exists():
        narrative_patterns_data = NarrativePatternsFile.model_validate(
            load_yaml_file(narrative_patterns_path)
        )
        narrative_patterns = narrative_patterns_data.narrative_patterns

    project = Project(
        config=config,
        plot=plot,
        characters=characters,
        world=world,
        style=style,
        plot_patterns=plot_patterns,
        narrative_patterns=narrative_patterns,
    )
    _validate_project(project)
    return project


def save_project(project: Project, path: Path) -> None:
    """Save a Fabulae project to a directory structure."""
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

    if project.plot_patterns:
        patterns_path = path / paths.plot_patterns
        save_yaml_file(
            patterns_path,
            PlotPatternsFile(plot_patterns=project.plot_patterns).model_dump(exclude_none=True),
        )

    if project.narrative_patterns:
        narrative_patterns_path = path / paths.narrative_patterns
        save_yaml_file(
            narrative_patterns_path,
            NarrativePatternsFile(narrative_patterns=project.narrative_patterns).model_dump(
                exclude_none=True
            ),
        )
