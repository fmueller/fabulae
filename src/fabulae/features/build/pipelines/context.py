"""Context dataclasses for build pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field

from fabulae.models import Character, Fragment, Scene, Stanza, Style, WorldFact


@dataclass
class BuildSceneContext:
    """Context for generating a single scene."""

    scene: Scene
    scene_id: str

    # Position info
    chapter_id: str | None
    chapter_title: str | None
    position_in_chapter: int
    total_scenes_in_chapter: int
    position_in_story: int
    total_scenes: int

    # Entities (filtered to scene in sequential, full in batch)
    characters: list[Character] = field(default_factory=list)
    location: WorldFact | None = None
    world_facts: list[WorldFact] = field(default_factory=list)

    # Style and premise
    style: Style | None = None
    premise: str = ""

    # Prior context
    prior_summaries: list[str] = field(default_factory=list)  # Windowed in sequential, full in batch
    prior_hooks: list[str] = field(default_factory=list)  # For hook diversity


@dataclass
class BuildFragmentContext:
    """Context for generating a micro-prose fragment."""

    fragment: Fragment
    position: int
    total_fragments: int

    # Style and premise
    style: Style | None = None
    premise: str = ""

    # Prior context
    prior_contents: list[str] = field(default_factory=list)
    prior_hooks: list[str] = field(default_factory=list)


@dataclass
class BuildStanzaContext:
    """Context for generating a poem stanza."""

    stanza: Stanza
    position: int
    total_stanzas: int

    # Style and premise
    style: Style | None = None
    premise: str = ""

    # Poem attributes
    poem_form: str | None = None
    poem_meter: str | None = None
    poem_rhyme_scheme: str | None = None

    # Prior context
    prior_stanzas: list[list[str]] = field(default_factory=list)
    prior_hooks: list[str] = field(default_factory=list)


__all__ = [
    "BuildFragmentContext",
    "BuildSceneContext",
    "BuildStanzaContext",
]
