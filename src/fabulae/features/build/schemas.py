"""Pydantic schemas for build command output."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

# Pipeline mode type
BuildPipelineMode = Literal["sequential", "batch"]


@dataclass
class BuildOptions:
    """Configuration options for build command."""

    pipeline: BuildPipelineMode = "sequential"
    enhanced: bool = True  # Enable hooks and beat-level tracking
    sliding_window_size: int = 5  # Only used in sequential mode


class SceneHook(BaseModel):
    """Opening hook for a scene, fragment, or stanza."""

    hook_type: str = Field(description="Type: question, action, dialog, image, tension")
    content: str = Field(description="The hook text")


class BeatProseOutput(BaseModel):
    """Generated prose for a single beat within a scene."""

    beat_id: str
    prose: str = Field(description="The generated prose for this beat")
    word_count: int = Field(ge=0)


class EnhancedSceneProseOutput(BaseModel):
    """LLM output schema for enhanced scene generation."""

    hook: SceneHook | None = None
    beats: list[BeatProseOutput] = Field(default_factory=list)


class EnhancedFragmentProseOutput(BaseModel):
    """LLM output schema for enhanced fragment generation."""

    hook: SceneHook | None = None
    content: str = Field(description="The generated prose content")


class EnhancedStanzaProseOutput(BaseModel):
    """LLM output schema for enhanced stanza generation."""

    hook: SceneHook | None = None  # Opening line that hooks
    lines: list[str] = Field(description="The lines of the stanza")


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
    hook: SceneHook | None = None
    beats: list[BeatProseOutput] = Field(default_factory=list)
    content: str = Field(description="The generated prose content for this scene")
    word_count: int = Field(ge=0)


class ChapterOutput(BaseModel):
    """Generated content for a chapter."""

    chapter_id: str
    title: str | None = None
    hook: SceneHook | None = None  # Chapter-level hook (from first scene)
    scenes: list[SceneOutput] = Field(default_factory=list)
    word_count: int = Field(ge=0)


class FragmentOutput(BaseModel):
    """Generated content for a micro-prose fragment."""

    fragment_id: str
    hook: SceneHook | None = None
    content: str = Field(description="The generated prose content for this fragment")
    word_count: int = Field(ge=0)


class StanzaOutput(BaseModel):
    """Generated content for a poem stanza."""

    stanza_id: str
    hook: SceneHook | None = None  # Opening line hook
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
    "BeatProseOutput",
    "BuildMetadata",
    "BuildOptions",
    "BuildOutput",
    "BuildPipelineMode",
    "ChapterOutput",
    "ContinuitySummary",
    "EnhancedFragmentProseOutput",
    "EnhancedSceneProseOutput",
    "EnhancedStanzaProseOutput",
    "FragmentOutput",
    "FragmentProseOutput",
    "PoemProseOutput",
    "SceneHook",
    "SceneOutput",
    "SceneProseOutput",
    "StanzaOutput",
    "StanzaProseOutput",
]
