"""Beat generation function for CRUD and create commands.

This module provides a unified beat generation function that works
for both CRUD suggest commands and the create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fabulae.features.entities.generation.prompts import build_beat_prompt
from fabulae.features.entities.generation.schemas import BeatOutput
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Beat

if TYPE_CHECKING:
    from fabulae.models import Character, Project, Scene


async def suggest_beat(
    scene: Scene | None = None,
    project: Project | None = None,
    scene_id: str | None = None,
    scene_summary: str | None = None,
    scene_characters: list[Character] | None = None,
    existing_beats: list[Beat] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Beat:
    """Suggest a beat based on context.

    This function is used by both:
    - `fabulae beat suggest` command (CRUD)
    - `fabulae create` command (indirectly via scene generation)

    There are two usage patterns:

    1. CRUD mode (pass scene and project):
       ```python
       beat = await suggest_beat(
           scene=scene,
           project=project,
           guidance="a tense confrontation",
           config=llm_config,
       )
       ```

    2. Create mode (pass individual parameters):
       ```python
       beat = await suggest_beat(
           scene_id="scene-01",
           scene_summary="The hero arrives at the castle",
           scene_characters=[char1, char2],
           existing_beats=scene.beats,
           assigned_id="scene-01-beat-01",
           language="en",
           config=llm_config,
       )
       ```

    Args:
        scene: The scene to add the beat to (for CRUD suggest).
            If provided, extracts scene_id, scene_summary, and existing_beats.
        project: The project containing the scene (for CRUD suggest).
            If provided, extracts scene_characters and language.
        scene_id: ID of the parent scene.
            Overrides scene.id if both are provided.
        scene_summary: Summary of the scene.
            Overrides scene.summary if both are provided.
        scene_characters: Characters in this scene.
            Extracted from project if not provided.
        existing_beats: Beats already in the scene (to avoid duplicates).
            Overrides scene.beats if both are provided.
        guidance: User-provided guidance text for the beat.
        language: Language code for content generation (e.g., 'en', 'de').
            Overrides project.style.language if both are provided.
        assigned_id: Pre-assigned ID to use (for create pipeline).
            If not provided, LLM generates the ID.
        config: LLM configuration. Required.

    Returns:
        Generated Beat model instance.

    Raises:
        ValueError: If config is not provided or scene_id cannot be determined.
    """
    if config is None:
        raise ValueError("LLM config is required for beat generation")

    if scene:
        if scene_id is None:
            scene_id = scene.id
        if scene_summary is None:
            scene_summary = scene.summary
        if existing_beats is None:
            existing_beats = scene.beats

    if project:
        if scene and scene_characters is None:
            # Find characters referenced in the scene
            scene_char_ids = scene.characters or []
            scene_characters = [c for c in project.characters if c.id in scene_char_ids]
        if language is None and project.style:
            language = project.style.language

    if scene_id is None:
        raise ValueError("scene_id is required for beat generation")

    prompt = build_beat_prompt(
        scene_id=scene_id,
        scene_summary=scene_summary,
        scene_characters=scene_characters,
        existing_beats=existing_beats,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
    )

    user_prompt = f"Generate a beat for scene '{scene_id}'."
    if guidance:
        user_prompt = f"Create a beat: {guidance[:100]}"

    agent = create_agent(BeatOutput, prompt, config)
    result = await agent.run(user_prompt)
    suggestion = result.output

    return Beat(
        id=suggestion.id,
        kind=suggestion.kind,
        summary=suggestion.summary,
        goal=suggestion.goal,
        conflict=suggestion.conflict,
        outcome=suggestion.outcome,
        pace=suggestion.pace,
    )


def suggest_beat_sync(
    scene: Scene | None = None,
    project: Project | None = None,
    scene_id: str | None = None,
    scene_summary: str | None = None,
    scene_characters: list[Character] | None = None,
    existing_beats: list[Beat] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Beat:
    """Synchronous wrapper for suggest_beat.

    See suggest_beat for argument documentation.
    """
    return asyncio.run(
        suggest_beat(
            scene=scene,
            project=project,
            scene_id=scene_id,
            scene_summary=scene_summary,
            scene_characters=scene_characters,
            existing_beats=existing_beats,
            guidance=guidance,
            language=language,
            assigned_id=assigned_id,
            config=config,
        )
    )


__all__ = ["suggest_beat", "suggest_beat_sync"]
