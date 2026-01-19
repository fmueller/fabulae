"""Shared Pydantic schemas for entity generation outputs.

These schemas define the structure of LLM-generated entity suggestions.
They are used by both CRUD suggest commands and the create pipeline.
"""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CharacterSuggestionOutput(BaseModel):
    """LLM output for character suggestion."""

    id: str = Field(description="Character ID in lowercase-with-hyphens format (e.g., 'detective-chen').")
    name: str = Field(description="Character's full name.")
    role: str | None = Field(default=None, description="Role: 'protagonist', 'antagonist', or 'supporting'.")
    desire: str | None = Field(default=None, description="What they consciously want (1 sentence).")
    need: str | None = Field(default=None, description="What they actually need for growth (1 sentence).")
    flaw: str | None = Field(default=None, description="Their key weakness (1-3 words).")
    secret: str | None = Field(default=None, description="Something hidden about them (1 sentence, optional).")
    traits: list[str] = Field(default_factory=list, description="2-4 personality traits as a list.")

    @field_validator("name", "role", "desire", "need", "flaw", "secret", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class WorldFactSuggestionOutput(BaseModel):
    """LLM output for world fact suggestion."""

    id: str = Field(description="World fact ID in lowercase-with-hyphens format (e.g., 'location-tavern').")
    type: Literal["location", "culture", "history", "rule", "object"] = Field(
        description="Type: 'location', 'culture', 'history', 'rule', or 'object'."
    )
    name: str = Field(description="Name of the location or concept.")
    facts: list[str] = Field(default_factory=list, description="List of 2-4 specific details about this element.")

    @field_validator("name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class BeatSuggestionOutput(BaseModel):
    """LLM output for beat suggestion."""

    id: str = Field(description="Beat ID in lowercase-with-hyphens format (e.g., 'beat-confrontation').")
    kind: str = Field(
        description="Type: 'action', 'dialogue', 'revelation', 'decision', 'transition', "
        "'setup', 'turn', 'escalation', 'resolution', 'bridge', or 'complication'."
    )
    summary: str | None = Field(default=None, description="1-2 sentences describing what happens.")
    goal: str | None = Field(default=None, description="What the POV character wants to achieve.")
    conflict: str | None = Field(default=None, description="What obstacle or tension exists.")
    outcome: str | None = Field(default=None, description="How the beat resolves.")
    pace: str | None = Field(default=None, description="Pacing note (e.g., 'fast', 'slow', 'tense').")

    @field_validator("kind", "summary", "goal", "conflict", "outcome", "pace", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class SceneSuggestionOutput(BaseModel):
    """LLM output for scene suggestion."""

    id: str = Field(description="Scene ID in lowercase-with-hyphens format (e.g., 'scene-confrontation').")
    summary: str | None = Field(default=None, description="2-3 sentences describing what happens.")
    goal: str | None = Field(default=None, description="What the protagonist wants to achieve.")
    conflict: str | None = Field(default=None, description="The obstacle or tension.")
    outcome: str | None = Field(default=None, description="How the scene resolves.")
    characters: list[str] = Field(default_factory=list, description="List of character IDs who appear.")
    location: str | None = Field(default=None, description="Optional location ID from world facts.")
    time: str | None = Field(default=None, description="Optional time indicator.")
    beats: list[BeatSuggestionOutput] = Field(default_factory=list, description="Beats in this scene.")

    @field_validator("summary", "goal", "conflict", "outcome", "time", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ChapterSuggestionOutput(BaseModel):
    """LLM output for chapter suggestion."""

    id: str = Field(description="Chapter ID in lowercase-with-hyphens format (e.g., 'chapter-revelation').")
    title: str | None = Field(default=None, description="Short evocative title.")
    summary: str | None = Field(default=None, description="2-3 sentences describing the chapter's arc.")

    @field_validator("title", "summary", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class FragmentSuggestionOutput(BaseModel):
    """LLM output for fragment suggestion (micro-prose format)."""

    id: str = Field(description="Fragment ID in lowercase-with-hyphens format (e.g., 'fragment-03').")
    content: str = Field(description="The prose content of this fragment (1-3 paragraphs).")
    target_words: int | None = Field(default=None, ge=1, description="Target word count.")
    notes: str | None = Field(default=None, description="Optional notes about this fragment.")

    @field_validator("content", "notes", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class StanzaSuggestionOutput(BaseModel):
    """LLM output for stanza suggestion (poem format)."""

    id: str = Field(description="Stanza ID in lowercase-with-hyphens format (e.g., 'stanza-03').")
    lines: list[str] = Field(default_factory=list, description="The lines of this stanza.")
    meter: str | None = Field(default=None, description="Meter pattern (e.g., 'iambic pentameter').")
    rhyme_scheme: str | None = Field(default=None, description="Rhyme scheme (e.g., 'ABAB').")

    @field_validator("meter", "rhyme_scheme", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


__all__ = [
    "CharacterSuggestionOutput",
    "WorldFactSuggestionOutput",
    "BeatSuggestionOutput",
    "SceneSuggestionOutput",
    "ChapterSuggestionOutput",
    "FragmentSuggestionOutput",
    "StanzaSuggestionOutput",
]
