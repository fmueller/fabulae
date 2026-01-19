"""Shared Pydantic schemas for entity generation outputs.

These schemas define the structure of LLM-generated entity outputs.
They are the single source of truth for entity generation, used by both:
- CRUD suggest commands (e.g., `fabulae character suggest`)
- Create pipeline (e.g., `fabulae create`)

The naming convention uses `*Output` suffix for all entity schemas.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CharacterOutput(BaseModel):
    """LLM output for character generation."""

    id: str = Field(description="Character ID in lowercase-with-hyphens format (e.g., 'character-01').")
    name: str = Field(description="Character's full name.")
    role: str | None = Field(default=None, description="Role: 'protagonist', 'antagonist', 'mentor', etc.")
    desire: str | None = Field(default=None, description="What they consciously want (1 sentence).")
    need: str | None = Field(default=None, description="What they actually need for growth (1 sentence).")
    flaw: str | None = Field(default=None, description="Their key weakness (1-3 words).")
    secret: str | None = Field(default=None, description="Something hidden about them (1 sentence, optional).")
    traits: list[str] = Field(default_factory=list, description="2-4 personality traits as a list.")

    @field_validator("name", "role", "desire", "need", "flaw", "secret", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class WorldFactOutput(BaseModel):
    """LLM output for world fact generation."""

    id: str = Field(description="World fact ID in lowercase-with-hyphens format (e.g., 'location-01').")
    type: Literal["location", "culture", "history", "rule", "object"] = Field(
        description="Type: 'location', 'culture', 'history', 'rule', or 'object'."
    )
    name: str = Field(description="Name of the location or concept.")
    facts: list[str] = Field(default_factory=list, description="List of 2-4 specific details about this element.")

    @field_validator("name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class BeatOutput(BaseModel):
    """LLM output for beat generation."""

    id: str = Field(description="Beat ID in lowercase-with-hyphens format (e.g., 'scene-01-beat-01').")
    kind: str = Field(
        description="Type: 'action', 'dialogue', 'revelation', 'decision', 'transition', "
        "'setup', 'turn', 'escalation', 'resolution', 'bridge', or 'complication'."
    )
    summary: str | None = Field(default=None, description="1-2 sentences describing what happens.")
    target_words: int | None = Field(default=None, ge=1, description="Target word count for this beat.")
    goal: str | None = Field(default=None, description="What the POV character wants to achieve.")
    conflict: str | None = Field(default=None, description="What obstacle or tension exists.")
    outcome: str | None = Field(default=None, description="How the beat resolves.")
    pace: str | None = Field(default=None, description="Pacing note (e.g., 'fast', 'slow', 'tense').")
    constraints: list[str] = Field(default_factory=list, description="Writing constraints for this beat.")

    @field_validator("kind", "summary", "goal", "conflict", "outcome", "pace", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class SceneOutput(BaseModel):
    """LLM output for scene generation."""

    id: str = Field(description="Scene ID in lowercase-with-hyphens format (e.g., 'scene-01').")
    location: str | None = Field(default=None, description="Location ID from world facts (e.g., 'location-01').")
    time: str | None = Field(default=None, description="Time indicator (e.g., 'night', 'dawn').")
    characters: list[str] = Field(default_factory=list, description="List of character IDs who appear.")
    world_fact_ids: list[str] = Field(default_factory=list, description="World fact IDs relevant to this scene.")
    summary: str | None = Field(default=None, description="2-3 sentences describing what happens.")
    goal: str | None = Field(default=None, description="What the protagonist wants to achieve.")
    conflict: str | None = Field(default=None, description="The obstacle or tension.")
    outcome: str | None = Field(default=None, description="How the scene resolves.")
    beats: list[BeatOutput] = Field(default_factory=list, description="Beats in this scene.")

    @field_validator("summary", "goal", "conflict", "outcome", "time", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ChapterOutput(BaseModel):
    """LLM output for chapter generation."""

    id: str = Field(description="Chapter ID in lowercase-with-hyphens format (e.g., 'chapter-01').")
    title: str | None = Field(default=None, description="Short evocative title.")
    summary: str | None = Field(default=None, description="2-3 sentences describing the chapter's arc.")
    scene_ids: list[str] | None = Field(default=None, description="Scene IDs in this chapter.")

    @field_validator("title", "summary", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class FragmentOutput(BaseModel):
    """LLM output for fragment generation (micro-prose format)."""

    id: str = Field(description="Fragment ID in lowercase-with-hyphens format (e.g., 'fragment-01').")
    content: str = Field(description="The prose content of this fragment (1-3 paragraphs).")
    target_words: int | None = Field(default=None, ge=1, description="Target word count.")
    notes: str | None = Field(default=None, description="Optional notes about this fragment.")

    @field_validator("content", "notes", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class StanzaOutput(BaseModel):
    """LLM output for stanza generation (poem format)."""

    id: str = Field(description="Stanza ID in lowercase-with-hyphens format (e.g., 'stanza-01').")
    lines: list[str] = Field(default_factory=list, description="The lines of this stanza.")
    meter: str | None = Field(default=None, description="Meter pattern (e.g., 'iambic pentameter').")
    rhyme_scheme: str | None = Field(default=None, description="Rhyme scheme (e.g., 'ABAB').")

    @field_validator("meter", "rhyme_scheme", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


# Backward compatibility aliases for gradual migration
CharacterSuggestionOutput = CharacterOutput
WorldFactSuggestionOutput = WorldFactOutput
BeatSuggestionOutput = BeatOutput
SceneSuggestionOutput = SceneOutput
ChapterSuggestionOutput = ChapterOutput
FragmentSuggestionOutput = FragmentOutput
StanzaSuggestionOutput = StanzaOutput


__all__ = [
    # Primary exports (new naming)
    "CharacterOutput",
    "WorldFactOutput",
    "BeatOutput",
    "SceneOutput",
    "ChapterOutput",
    "FragmentOutput",
    "StanzaOutput",
    # Backward compatibility aliases
    "CharacterSuggestionOutput",
    "WorldFactSuggestionOutput",
    "BeatSuggestionOutput",
    "SceneSuggestionOutput",
    "ChapterSuggestionOutput",
    "FragmentSuggestionOutput",
    "StanzaSuggestionOutput",
]
