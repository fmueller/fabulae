"""Scene generation function for CRUD and create commands.

This module provides a unified scene generation function that works
for both CRUD suggest commands and the create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fabulae.features.entities.generation.prompts import BeatSlotInfo, build_scene_prompt
from fabulae.features.entities.generation.schemas import SceneOutput
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Beat, Scene

if TYPE_CHECKING:
    from fabulae.features.create.schemas import StyleOutput
    from fabulae.models import Character, Project, WorldFact


async def suggest_scene(
    project: Project | None = None,
    available_characters: list[Character] | None = None,
    available_locations: list[WorldFact] | None = None,
    existing_scenes: list[Scene] | None = None,
    premise: str | None = None,
    chapter_context: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    include_beats: bool = False,
    beat_count: int = 0,
    config: LLMConfig | None = None,
    style: StyleOutput | None = None,
    beat_slots: list[BeatSlotInfo] | None = None,
    previous_scene_summaries: list[str] | None = None,
    position_in_story: int | None = None,
    total_scenes: int | None = None,
    position_label: str | None = None,
) -> Scene:
    """Suggest a scene based on context.

    This function is used by both:
    - `fabulae scene suggest` command (CRUD)
    - `fabulae create` command's scene generation phase

    There are two usage patterns:

    1. CRUD mode (pass project):
       ```python
       scene = await suggest_scene(
           project=project,
           chapter_context="Chapter 1: The Beginning",
           guidance="a tense confrontation",
           config=llm_config,
       )
       ```

    2. Create mode (pass individual parameters with beat_slots):
       ```python
       scene = await suggest_scene(
           available_characters=[char1, char2],
           available_locations=[loc1],
           premise=premise,
           chapter_context="Chapter 1",
           assigned_id="scene-01",
           beat_slots=[BeatSlotInfo("scene-01-beat-01", "setup"), ...],
           previous_scene_summaries=["Previous scene summary..."],
           position_in_story=0,
           total_scenes=10,
           position_label="early",
           language="en",
           style=style_output,
           config=llm_config,
       )
       ```

    Args:
        project: Existing project for context (for CRUD suggest).
            If provided, extracts characters, locations, and scenes from it.
        available_characters: Characters that can appear in the scene.
            Overrides project.characters if both are provided.
        available_locations: Locations that can be used (WorldFacts with type="location").
            Extracted from project.world.facts if not provided.
        existing_scenes: Scenes already in project (to avoid duplicates).
            Overrides project.plot.scenes if both are provided.
        premise: Story premise for thematic alignment.
            Overrides project.plot.premise if both are provided.
        chapter_context: Information about the target chapter.
        guidance: User-provided guidance text for the scene.
        language: Language code for content generation (e.g., 'en', 'de').
            Overrides project.style.language if both are provided.
        assigned_id: Pre-assigned ID to use (for create pipeline).
            If not provided, LLM generates the ID.
        include_beats: Whether to generate beats within the scene (CRUD mode).
        beat_count: Number of beats to generate (CRUD mode, if include_beats).
        config: LLM configuration. Required.
        style: StyleOutput for narrative style context (from create pipeline).
        beat_slots: Pre-assigned beat slots with IDs and kinds (create pipeline mode).
        previous_scene_summaries: Recent scene summaries for continuity.
        position_in_story: Scene position in narrative (0-indexed).
        total_scenes: Total scenes in narrative.
        position_label: Position descriptor ('early', 'middle', 'late', 'climax').

    Returns:
        Generated Scene model instance.

    Raises:
        ValueError: If config is not provided.
    """
    if config is None:
        raise ValueError("LLM config is required for scene generation")

    if project:
        if available_characters is None:
            available_characters = project.characters
        if available_locations is None and project.world:
            available_locations = [f for f in project.world.facts if f.type == "location"]
        if existing_scenes is None:
            existing_scenes = project.plot.scenes
        if premise is None and project.plot:
            premise = project.plot.premise
        if language is None and project.style:
            language = project.style.language

    prompt = build_scene_prompt(
        premise=premise,
        available_characters=available_characters,
        available_locations=available_locations,
        existing_scenes=existing_scenes,
        chapter_context=chapter_context,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
        include_beats=include_beats,
        beat_count=beat_count,
        style=style,
        beat_slots=beat_slots,
        previous_scene_summaries=previous_scene_summaries,
        position_in_story=position_in_story,
        total_scenes=total_scenes,
        position_label=position_label,
    )

    user_prompt = "Generate a scene based on the context provided."
    if guidance:
        user_prompt = f"Create a scene: {guidance[:100]}"

    agent = create_agent(SceneOutput, prompt, config)
    result = await agent.run(user_prompt)
    suggestion = result.output

    beats: list[Beat] = []
    if suggestion.beats:
        for beat_output in suggestion.beats:
            beat = Beat(
                id=beat_output.id,
                kind=beat_output.kind,
                summary=beat_output.summary,
                goal=beat_output.goal,
                conflict=beat_output.conflict,
                outcome=beat_output.outcome,
                pace=beat_output.pace,
            )
            beats.append(beat)

    return Scene(
        id=suggestion.id,
        summary=suggestion.summary,
        goal=suggestion.goal,
        conflict=suggestion.conflict,
        outcome=suggestion.outcome,
        characters=suggestion.characters,
        location=suggestion.location,
        time=suggestion.time,
        beats=beats,
    )


def suggest_scene_sync(
    project: Project | None = None,
    available_characters: list[Character] | None = None,
    available_locations: list[WorldFact] | None = None,
    existing_scenes: list[Scene] | None = None,
    premise: str | None = None,
    chapter_context: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    include_beats: bool = False,
    beat_count: int = 0,
    config: LLMConfig | None = None,
    style: StyleOutput | None = None,
    beat_slots: list[BeatSlotInfo] | None = None,
    previous_scene_summaries: list[str] | None = None,
    position_in_story: int | None = None,
    total_scenes: int | None = None,
    position_label: str | None = None,
) -> Scene:
    """Synchronous wrapper for suggest_scene.

    See suggest_scene for argument documentation.
    """
    return asyncio.run(
        suggest_scene(
            project=project,
            available_characters=available_characters,
            available_locations=available_locations,
            existing_scenes=existing_scenes,
            premise=premise,
            chapter_context=chapter_context,
            guidance=guidance,
            language=language,
            assigned_id=assigned_id,
            include_beats=include_beats,
            beat_count=beat_count,
            config=config,
            style=style,
            beat_slots=beat_slots,
            previous_scene_summaries=previous_scene_summaries,
            position_in_story=position_in_story,
            total_scenes=total_scenes,
            position_label=position_label,
        )
    )


__all__ = ["suggest_scene", "suggest_scene_sync", "BeatSlotInfo"]
