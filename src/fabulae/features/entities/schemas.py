"""Pydantic schemas for entity suggestion outputs."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


class CharacterSuggestion(BaseModel):
    """Suggested character from LLM."""

    id: str = Field(description="Unique lowercase-with-hyphens identifier (e.g., 'detective-chen').")
    name: str = Field(description="Full character name.")
    role: str | None = Field(default=None, description="One of 'protagonist', 'antagonist', or 'supporting'.")
    desire: str | None = Field(default=None, description="What they consciously want (1 sentence).")
    need: str | None = Field(default=None, description="What they actually need for growth (1 sentence).")
    flaw: str | None = Field(default=None, description="Their key weakness (1-3 words).")
    secret: str | None = Field(default=None, description="Something hidden about them (1 sentence, optional).")
    traits: list[str] = Field(default_factory=list, description="2-4 personality traits as a list.")

    @field_validator("name", "role", "desire", "need", "flaw", "secret", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class BeatSuggestion(BaseModel):
    """Suggested beat from LLM."""

    id: str = Field(description="Unique lowercase-with-hyphens (e.g., 'beat-confrontation').")
    kind: str = Field(
        description="One of 'action', 'dialogue', 'revelation', 'decision', 'transition', "
        "'setup', 'turn', 'escalation', 'resolution', 'bridge', 'complication'."
    )
    summary: str | None = Field(default=None, description="1-2 sentences describing what happens.")
    goal: str | None = Field(default=None, description="What the POV character wants to achieve.")
    conflict: str | None = Field(default=None, description="What obstacle or tension exists.")
    outcome: str | None = Field(default=None, description="How the beat resolves.")

    @field_validator("kind", "summary", "goal", "conflict", "outcome", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class SceneSuggestion(BaseModel):
    """Suggested scene from LLM."""

    id: str = Field(description="Unique lowercase-with-hyphens (e.g., 'scene-confrontation').")
    summary: str | None = Field(default=None, description="2-3 sentences describing what happens.")
    goal: str | None = Field(default=None, description="What the protagonist wants to achieve.")
    conflict: str | None = Field(default=None, description="The obstacle or tension.")
    outcome: str | None = Field(default=None, description="How the scene resolves.")
    characters: list[str] = Field(default_factory=list, description="List of character IDs who appear.")
    location: str | None = Field(default=None, description="Optional location ID from world facts.")
    time: str | None = Field(default=None, description="Optional time indicator.")

    @field_validator("summary", "goal", "conflict", "outcome", "time", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class ChapterSuggestion(BaseModel):
    """Suggested chapter from LLM."""

    id: str = Field(description="Unique lowercase-with-hyphens (e.g., 'chapter-revelation').")
    title: str | None = Field(default=None, description="Short evocative title.")
    summary: str | None = Field(default=None, description="2-3 sentences describing the chapter's arc.")

    @field_validator("title", "summary", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class WorldFactSuggestion(BaseModel):
    """Suggested world fact from LLM."""

    id: str = Field(description="Unique lowercase-with-hyphens (e.g., 'location-tavern' or 'culture-elven').")
    type: Literal["location", "culture", "history", "rule", "object"] = Field(
        description="One of 'location', 'culture', 'history', 'rule', 'object'."
    )
    name: str = Field(description="Name of the location or concept.")
    facts: list[str] = Field(default_factory=list, description="List of 2-4 specific details about this world element.")

    @field_validator("name", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class FragmentSuggestion(BaseModel):
    """Suggested fragment from LLM (for micro-prose format)."""

    id: str = Field(description="Unique lowercase-with-hyphens (e.g., 'fragment-03').")
    content: str = Field(description="The prose content of this fragment (1-3 paragraphs).")
    target_words: int | None = Field(default=None, ge=1, description="Target word count.")
    notes: str | None = Field(default=None, description="Optional notes about this fragment.")

    @field_validator("content", "notes", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class StanzaSuggestion(BaseModel):
    """Suggested stanza from LLM (for poem format)."""

    id: str = Field(description="Unique lowercase-with-hyphens (e.g., 'stanza-03').")
    lines: list[str] = Field(default_factory=list, description="The lines of this stanza.")
    meter: str | None = Field(default=None, description="Meter pattern (e.g., 'iambic pentameter').")
    rhyme_scheme: str | None = Field(default=None, description="Rhyme scheme (e.g., 'ABAB').")

    @field_validator("meter", "rhyme_scheme", mode="before")
    @classmethod
    def strip_whitespace(cls, v: str | None) -> str | None:
        return v.strip() if v else v
