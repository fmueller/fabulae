"""Structured LLM output schemas for create-from-idea."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Import entity schemas from the generation module (single source of truth)
from fabulae.features.entities.generation.schemas import (
    BeatOutput,
    ChapterOutput,
    CharacterOutput,
    FragmentOutput,
    SceneOutput,
    StanzaOutput,
    WorldFactOutput,
)

PipelineMode = Literal["batch", "sequential"]


@dataclass
class CreateOptions:
    """Configuration options for create command behavior."""

    shape_id: str | None = None
    shape_file: Path | None = None
    no_shape: bool = False  # Explicitly skip story shape (free-form generation)
    variation: float = 0.5
    seed: int | None = None
    enrich: bool = True
    # Language override from CLI (ISO 639-1 code)
    idea_language: str | None = None
    # Small model optimizations
    is_small_model: bool = False
    sliding_window_scenes: int | None = None  # None = unlimited, 5 recommended for small models
    # Pipeline selection
    pipeline: PipelineMode = "batch"  # "batch" (current) or "sequential" (new)
    # Full mode: when False, generates outline only; when True, generates complete project
    full: bool = False


class CharacterBatchOutput(BaseModel):
    characters: list[CharacterOutput] = Field(default_factory=list)


class CharacterPlanItem(BaseModel):
    """A brief character outline for the cast list."""

    id: str = Field(description="Lowercase-hyphenated ID (e.g., 'character-01').")
    name: str = Field(description="Character's name.")
    role: str | None = Field(default=None, description="Role: 'protagonist', 'antagonist', etc.")
    purpose: str | None = Field(default=None, description="Brief description of character's purpose in the story.")

    @field_validator("name", "role", "purpose", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class CharacterPlanOutput(BaseModel):
    characters: list[CharacterPlanItem] = Field(default_factory=list)


class WorldOutput(BaseModel):
    setting: str | None = None
    time_period: str | None = None
    tone: str | None = None
    motifs: list[str] = Field(default_factory=list)
    facts: list[WorldFactOutput] = Field(default_factory=list)

    @field_validator("setting", "time_period", "tone", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class WorldFactPlanItem(BaseModel):
    id: str
    type: Literal["location", "culture", "history", "rule", "object"]
    name: str
    purpose: str | None = None

    @field_validator("name", "purpose", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class WorldPlanOutput(BaseModel):
    setting: str | None = None
    time_period: str | None = None
    tone: str | None = None
    motifs: list[str] = Field(default_factory=list)
    facts: list[WorldFactPlanItem] = Field(default_factory=list)

    @field_validator("setting", "time_period", "tone", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class HookOutput(BaseModel):
    line: str | None = None
    question: str | None = None
    promise: str | None = None

    @field_validator("line", "question", "promise", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class StakesOutput(BaseModel):
    external: str | None = None
    internal: str | None = None

    @field_validator("external", "internal", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class BeatTemplateItem(BaseModel):
    kind: str
    required: bool = False
    plot_pattern_beat: str | None = None
    notes: str | None = None
    variation_point_description: str | None = None

    @field_validator("kind", "plot_pattern_beat", "notes", "variation_point_description", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class SceneBeatTemplate(BaseModel):
    scene_id: str
    beat_count: int = Field(default=1, ge=1)
    beats: list[BeatTemplateItem] = Field(default_factory=list)


class OutlineSceneOutput(BaseModel):
    """A scene outline with planned beat count."""

    id: str = Field(description="Lowercase-hyphenated ID (e.g., 'scene-01').")
    summary: str | None = Field(default=None, description="Brief summary of the scene's events.")
    goal: str | None = Field(default=None, description="What the protagonist wants to achieve.")
    conflict: str | None = Field(default=None, description="The obstacle or tension in this scene.")
    outcome: str | None = Field(default=None, description="How the scene resolves.")
    beat_count: int = Field(default=1, ge=1, description="Number of beats. Must be within beats-per-scene range.")

    @field_validator("summary", "goal", "conflict", "outcome", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class PlotOutput(BaseModel):
    format: Literal["novel", "novella", "short-story", "micro-prose", "poem"]
    title: str | None = None
    premise: str
    themes: list[str] = Field(default_factory=list)
    hook: HookOutput | None = None
    stakes: StakesOutput | None = None
    chapters: list[ChapterOutput] = Field(default_factory=list)
    scenes: list[SceneOutput] = Field(default_factory=list)
    scene_ids: list[str] | None = None
    fragments: list[FragmentOutput] = Field(default_factory=list)
    stanzas: list[StanzaOutput] = Field(default_factory=list)
    lines: list[str] = Field(default_factory=list)
    poem_form: str | None = None
    poem_meter: str | None = None
    poem_rhyme_scheme: str | None = None

    @field_validator("title", "premise", "poem_form", "poem_meter", "poem_rhyme_scheme", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class PlotOutlineOutput(BaseModel):
    format: Literal["novel", "novella", "short-story"]
    title: str | None = None
    premise: str
    themes: list[str] = Field(default_factory=list)
    hook: HookOutput | None = None
    stakes: StakesOutput | None = None
    chapters: list[ChapterOutput] = Field(default_factory=list)
    scenes: list[OutlineSceneOutput] = Field(default_factory=list)
    scene_ids: list[str] | None = None

    @field_validator("title", "premise", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class FragmentPlanItem(BaseModel):
    id: str
    target_words: int | None = Field(default=None, ge=1)
    notes: str | None = None
    intent: str | None = None

    @field_validator("notes", "intent", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class FragmentPlanOutput(BaseModel):
    title: str | None = None
    premise: str
    themes: list[str] = Field(default_factory=list)
    fragments: list[FragmentPlanItem] = Field(default_factory=list)

    @field_validator("title", "premise", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class StanzaPlanItem(BaseModel):
    id: str
    line_count: int = Field(default=1, ge=1)
    intent: str | None = None

    @field_validator("intent", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class PoemPlanOutput(BaseModel):
    title: str | None = None
    premise: str
    themes: list[str] = Field(default_factory=list)
    poem_form: str | None = None
    poem_meter: str | None = None
    poem_rhyme_scheme: str | None = None
    stanzas: list[StanzaPlanItem] = Field(default_factory=list)

    @field_validator("title", "premise", "poem_form", "poem_meter", "poem_rhyme_scheme", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class PremiseOutput(BaseModel):
    """Expanded premise generated from user's idea."""

    title: str | None = Field(
        default=None,
        description="A compelling title for the story.",
    )
    premise: str = Field(
        description="A 2-4 sentence narrative premise expanding on the original idea. "
        "Should capture the core conflict, setting, and emotional hook."
    )

    @field_validator("title", "premise", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class StyleOutput(BaseModel):
    """Narrative style configuration."""

    model_config = ConfigDict(populate_by_name=True)

    language: str | None = Field(default=None, description="ISO 639-1 language code (e.g., 'en', 'de', 'fr').")
    pov: str | None = Field(default=None, description="POV: 'first', 'second', 'third', or 'third-omniscient'.")
    tense: str | None = Field(default=None, description="Narrative tense: 'past', 'present', or 'future'.")
    voice: str | None = Field(default=None, description="Narrative voice (e.g., 'observant', 'intimate', 'detached').")
    register_: str | None = Field(default=None, alias="register", description="Register: 'formal', 'informal'.")
    constraints: list[str] = Field(default_factory=list, description="Writing constraints.")

    @field_validator("language", "pov", "tense", "voice", "register_", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ChapterContentOutput(BaseModel):
    id: str
    title: str | None = None
    summary: str | None = None

    @field_validator("title", "summary", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class SceneContentOutput(BaseModel):
    id: str
    chapter_id: str | None = None
    title: str | None = None
    summary: str | None = None
    beat_count: int = Field(ge=1)

    @field_validator("title", "summary", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class OutlineContentOutput(BaseModel):
    chapters: list[ChapterContentOutput] = Field(default_factory=list)
    scenes: list[SceneContentOutput] = Field(default_factory=list)


class SubplotAddition(BaseModel):
    """A subplot seed or addition to weave into the narrative."""

    description: str
    involved_characters: list[str] = Field(default_factory=list)
    scenes_to_modify: list[str] = Field(default_factory=list)

    @field_validator("description", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ForeshadowingElement(BaseModel):
    """A foreshadowing element to weave into the narrative."""

    description: str
    setup_scene: str | None = None
    payoff_scene: str | None = None

    @field_validator("description", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class EnrichmentOutput(BaseModel):
    """Output schema for narrative enrichment suggestions."""

    new_characters: list[CharacterOutput] = Field(default_factory=list)
    new_locations: list[WorldFactOutput] = Field(default_factory=list)
    new_world_facts: list[WorldFactOutput] = Field(default_factory=list)
    subplot_additions: list[SubplotAddition] = Field(default_factory=list)
    foreshadowing_elements: list[ForeshadowingElement] = Field(default_factory=list)


# ============================================================================
# Outline-only schemas (for outline mode without --full flag)
# ============================================================================


class CharacterSketchOutput(BaseModel):
    """Minimal character info for outline mode."""

    id: str = Field(description="Lowercase-hyphenated ID (e.g., 'character-01').")
    name: str = Field(description="Character's name.")
    role: str | None = Field(default=None, description="Role: 'protagonist', 'antagonist', 'supporting', etc.")
    description: str | None = Field(default=None, description="One-line character description.")

    @field_validator("name", "role", "description", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class SceneSketchOutput(BaseModel):
    """Minimal scene info for outline mode."""

    id: str = Field(description="Lowercase-hyphenated ID (e.g., 'scene-01').")
    title: str | None = Field(default=None, description="Brief scene title.")
    summary: str | None = Field(default=None, description="2-3 sentence scene summary.")
    character_ids: list[str] = Field(default_factory=list, description="Character IDs appearing in this scene.")

    @field_validator("title", "summary", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ChapterSketchOutput(BaseModel):
    """Chapter with scene sketches for outline mode."""

    id: str = Field(description="Lowercase-hyphenated ID (e.g., 'chapter-01').")
    title: str | None = Field(default=None, description="Chapter title.")
    summary: str | None = Field(default=None, description="2-3 sentence chapter summary.")
    scene_ids: list[str] = Field(default_factory=list, description="Scene IDs in this chapter.")

    @field_validator("title", "summary", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class LocationSketchOutput(BaseModel):
    """Minimal location info for outline mode."""

    id: str = Field(description="Lowercase-hyphenated ID (e.g., 'location-01').")
    name: str = Field(description="Location name.")

    @field_validator("name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class OutlineOutput(BaseModel):
    """Complete outline for outline-only mode (no --full flag)."""

    title: str | None = Field(default=None, description="Story title.")
    premise: str = Field(description="Expanded premise (2-4 sentences).")
    chapters: list[ChapterSketchOutput] = Field(default_factory=list, description="Chapter outlines.")
    scenes: list[SceneSketchOutput] = Field(default_factory=list, description="Scene sketches.")
    characters: list[CharacterSketchOutput] = Field(default_factory=list, description="Character sketches.")
    locations: list[LocationSketchOutput] = Field(default_factory=list, description="Location names.")

    @field_validator("title", "premise", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


# Explicit exports for mypy compatibility
__all__ = [
    # Re-exports from entities/generation/schemas.py (single source of truth)
    "BeatOutput",
    "ChapterOutput",
    "CharacterOutput",
    "FragmentOutput",
    "SceneOutput",
    "StanzaOutput",
    "WorldFactOutput",
    # Create-specific schemas
    "CreateOptions",
    "PipelineMode",
    "CharacterBatchOutput",
    "CharacterPlanItem",
    "CharacterPlanOutput",
    "WorldOutput",
    "WorldFactPlanItem",
    "WorldPlanOutput",
    "HookOutput",
    "StakesOutput",
    "BeatTemplateItem",
    "SceneBeatTemplate",
    "OutlineSceneOutput",
    "PlotOutput",
    "PlotOutlineOutput",
    "FragmentPlanItem",
    "FragmentPlanOutput",
    "StanzaPlanItem",
    "PoemPlanOutput",
    "PremiseOutput",
    "StyleOutput",
    "ChapterContentOutput",
    "SceneContentOutput",
    "OutlineContentOutput",
    "SubplotAddition",
    "ForeshadowingElement",
    "EnrichmentOutput",
    "CharacterSketchOutput",
    "SceneSketchOutput",
    "ChapterSketchOutput",
    "LocationSketchOutput",
    "OutlineOutput",
]
