"""Structured LLM output schemas for create-from-idea."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CharacterOutput(BaseModel):
    id: str
    name: str
    role: str | None = None
    desire: str | None = None
    need: str | None = None
    flaw: str | None = None
    secret: str | None = None
    traits: list[str] = Field(default_factory=list)


class CharacterBatchOutput(BaseModel):
    characters: list[CharacterOutput] = Field(default_factory=list)


class CharacterPlanItem(BaseModel):
    id: str
    name: str
    role: str | None = None
    purpose: str | None = None


class CharacterPlanOutput(BaseModel):
    characters: list[CharacterPlanItem] = Field(default_factory=list)


class WorldFactOutput(BaseModel):
    id: str
    type: Literal["location", "culture", "history", "rule", "object"]
    name: str
    facts: list[str] = Field(default_factory=list)


class WorldOutput(BaseModel):
    setting: str | None = None
    time_period: str | None = None
    tone: str | None = None
    motifs: list[str] = Field(default_factory=list)
    facts: list[WorldFactOutput] = Field(default_factory=list)


class WorldFactPlanItem(BaseModel):
    id: str
    type: Literal["location", "culture", "history", "rule", "object"]
    name: str
    purpose: str | None = None


class WorldPlanOutput(BaseModel):
    setting: str | None = None
    time_period: str | None = None
    tone: str | None = None
    motifs: list[str] = Field(default_factory=list)
    facts: list[WorldFactPlanItem] = Field(default_factory=list)


class HookOutput(BaseModel):
    line: str | None = None
    question: str | None = None
    promise: str | None = None


class StakesOutput(BaseModel):
    external: str | None = None
    internal: str | None = None


class BeatOutput(BaseModel):
    id: str
    kind: str
    summary: str | None = None
    target_words: int | None = Field(default=None, ge=1)
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    pace: str | None = None
    constraints: list[str] = Field(default_factory=list)


class SceneOutput(BaseModel):
    id: str
    chapter: str | None = None
    location: str | None = None
    time: str | None = None
    characters: list[str] = Field(default_factory=list)
    world_fact_ids: list[str] = Field(default_factory=list)
    plot_pattern: str | None = None
    plot_pattern_beat: str | None = None
    summary: str | None = None
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    beats: list[BeatOutput] = Field(default_factory=list)


class OutlineSceneOutput(BaseModel):
    id: str
    chapter: str | None = None
    summary: str | None = None
    goal: str | None = None
    conflict: str | None = None
    outcome: str | None = None
    beat_count: int = Field(default=1, ge=1)


class ChapterOutput(BaseModel):
    id: str
    title: str | None = None
    summary: str | None = None
    scene_ids: list[str] | None = None


class FragmentOutput(BaseModel):
    id: str
    content: str
    target_words: int | None = Field(default=None, ge=1)
    notes: str | None = None


class StanzaOutput(BaseModel):
    id: str
    lines: list[str] = Field(default_factory=list)
    meter: str | None = None
    rhyme_scheme: str | None = None


class PlotPatternBeatAssignmentOutput(BaseModel):
    type: str
    scene: str
    scene_beat: str | None = None
    notes: str | None = None


class PlotOutput(BaseModel):
    format: Literal["novel", "novella", "short-story", "micro-prose", "poem"]
    title: str | None = None
    premise: str
    themes: list[str] = Field(default_factory=list)
    hook: HookOutput | None = None
    stakes: StakesOutput | None = None
    plot_pattern: str | None = None
    plot_pattern_beats: list[PlotPatternBeatAssignmentOutput] = Field(default_factory=list)
    chapters: list[ChapterOutput] = Field(default_factory=list)
    scenes: list[SceneOutput] = Field(default_factory=list)
    scene_ids: list[str] | None = None
    fragments: list[FragmentOutput] = Field(default_factory=list)
    stanzas: list[StanzaOutput] = Field(default_factory=list)
    lines: list[str] = Field(default_factory=list)
    poem_form: str | None = None
    poem_meter: str | None = None
    poem_rhyme_scheme: str | None = None


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


class FragmentPlanItem(BaseModel):
    id: str
    target_words: int | None = Field(default=None, ge=1)
    notes: str | None = None
    intent: str | None = None


class FragmentPlanOutput(BaseModel):
    title: str | None = None
    premise: str
    themes: list[str] = Field(default_factory=list)
    fragments: list[FragmentPlanItem] = Field(default_factory=list)


class StanzaPlanItem(BaseModel):
    id: str
    line_count: int = Field(default=1, ge=1)
    intent: str | None = None


class PoemPlanOutput(BaseModel):
    title: str | None = None
    premise: str
    themes: list[str] = Field(default_factory=list)
    poem_form: str | None = None
    poem_meter: str | None = None
    poem_rhyme_scheme: str | None = None
    stanzas: list[StanzaPlanItem] = Field(default_factory=list)


class StyleOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    language: str | None = None
    pov: str | None = None
    tense: str | None = None
    voice: str | None = None
    register_: str | None = Field(default=None, alias="register")
    constraints: list[str] = Field(default_factory=list)
