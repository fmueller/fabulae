"""Pydantic schemas for build command output."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class BuildMetadata(BaseModel):
    """Metadata about a build run."""

    project_name: str
    format: str
    seed: int | None = None
    model: str
    temperature: float
    timestamp: datetime
    version: str


class SceneOutput(BaseModel):
    """Generated prose for a single scene."""

    scene_id: str
    chapter_id: str | None = None
    title: str | None = None
    content: str = Field(description="The generated prose content for this scene")
    word_count: int = Field(ge=0)


class ChapterOutput(BaseModel):
    """Generated content for a chapter."""

    chapter_id: str
    title: str | None = None
    scenes: list[SceneOutput] = Field(default_factory=list)
    word_count: int = Field(ge=0)


class FragmentOutput(BaseModel):
    """Generated content for a micro-prose fragment."""

    fragment_id: str
    content: str = Field(description="The generated prose content for this fragment")
    word_count: int = Field(ge=0)


class StanzaOutput(BaseModel):
    """Generated content for a poem stanza."""

    stanza_id: str
    lines: list[str] = Field(default_factory=list)
    word_count: int = Field(ge=0)


class BuildOutput(BaseModel):
    """Complete build output for a project."""

    metadata: BuildMetadata
    chapters: list[ChapterOutput] | None = None
    scenes: list[SceneOutput] | None = None
    fragments: list[FragmentOutput] | None = None
    stanzas: list[StanzaOutput] | None = None
    poem: str | None = None
    full_text: str
    total_word_count: int = Field(ge=0)


class ContinuitySummary(BaseModel):
    """Summary of a scene for continuity threading."""

    summary: str = Field(description="Brief summary of key events and character development")


class SceneProseOutput(BaseModel):
    """LLM output schema for scene generation."""

    content: str = Field(description="The generated prose content for this scene")


class FragmentProseOutput(BaseModel):
    """LLM output schema for fragment generation."""

    content: str = Field(description="The generated prose content for this fragment")


class StanzaProseOutput(BaseModel):
    """LLM output schema for stanza generation."""

    lines: list[str] = Field(description="The lines of the stanza")


class PoemProseOutput(BaseModel):
    """LLM output schema for complete poem generation."""

    content: str = Field(description="The complete poem text")


__all__ = [
    "BuildMetadata",
    "BuildOutput",
    "ChapterOutput",
    "ContinuitySummary",
    "FragmentOutput",
    "FragmentProseOutput",
    "PoemProseOutput",
    "SceneOutput",
    "SceneProseOutput",
    "StanzaOutput",
    "StanzaProseOutput",
]
