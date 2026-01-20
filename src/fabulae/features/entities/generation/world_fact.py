"""World fact generation function for CRUD and create commands.

This module provides a unified world fact generation function that works
for both CRUD suggest commands and the create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Literal

from fabulae.features.entities.generation.prompts import build_world_fact_prompt
from fabulae.features.entities.generation.schemas import WorldFactOutput
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import WorldFact

if TYPE_CHECKING:
    from fabulae.features.create.schemas import StyleOutput
    from fabulae.models import Project


WorldFactType = Literal["location", "culture", "history", "rule", "object"]


async def suggest_world_fact(
    project: Project | None = None,
    existing_facts: list[WorldFact] | None = None,
    premise: str | None = None,
    fact_type: WorldFactType | str | None = None,
    needs_hint: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
    style: StyleOutput | None = None,
) -> WorldFact:
    """Suggest a world fact based on context.

    This function is used by both:
    - `fabulae world suggest` command (CRUD)
    - `fabulae create` command's location generation phase

    There are two usage patterns:

    1. CRUD mode (pass project):
       ```python
       fact = await suggest_world_fact(
           project=project,
           fact_type="location",
           guidance="a mysterious forest",
           config=llm_config,
       )
       ```

    2. Create mode (pass individual parameters):
       ```python
       fact = await suggest_world_fact(
           existing_facts=state.locations,
           premise=premise,
           fact_type="location",
           needs_hint="The main setting for the story",
           assigned_id="location-01",
           language="en",
           config=llm_config,
       )
       ```

    Args:
        project: Existing project for context (for CRUD suggest).
            If provided, extracts premise and existing facts from it.
        existing_facts: World facts already in project (for avoiding duplicates).
            Overrides project.world.facts if both are provided.
        premise: Story premise for thematic alignment.
            Overrides project.plot.premise if both are provided.
        fact_type: Required type (location, culture, history, rule, object).
        needs_hint: What this world fact should provide to the story.
        guidance: User-provided guidance text for the world fact.
        language: Language code for content generation (e.g., 'en', 'de').
            Overrides project.style.language if both are provided.
        assigned_id: Pre-assigned ID to use (for create pipeline).
            If not provided, LLM generates the ID.
        config: LLM configuration. Required.
        style: StyleOutput for narrative style context (from create pipeline).

    Returns:
        Generated WorldFact model instance.

    Raises:
        ValueError: If config is not provided.
    """
    if config is None:
        raise ValueError("LLM config is required for world fact generation")

    if project:
        if existing_facts is None and project.world:
            existing_facts = project.world.facts
        if premise is None and project.plot:
            premise = project.plot.premise
        if language is None and project.style:
            language = project.style.language

    prompt = build_world_fact_prompt(
        premise=premise,
        existing_facts=existing_facts,
        fact_type=fact_type,
        needs_hint=needs_hint,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
        style=style,
    )

    user_prompt = "Generate a world fact based on the context provided."
    if fact_type:
        user_prompt = f"Create a {fact_type} for the story"
    elif guidance:
        user_prompt = f"Create a world element: {guidance[:100]}"

    agent = create_agent(WorldFactOutput, prompt, config)
    result = await agent.run(user_prompt)
    suggestion = result.output

    return WorldFact(
        id=suggestion.id,
        type=suggestion.type,
        name=suggestion.name,
        facts=suggestion.facts,
    )


def suggest_world_fact_sync(
    project: Project | None = None,
    existing_facts: list[WorldFact] | None = None,
    premise: str | None = None,
    fact_type: WorldFactType | str | None = None,
    needs_hint: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
    style: StyleOutput | None = None,
) -> WorldFact:
    """Synchronous wrapper for suggest_world_fact.

    See suggest_world_fact for argument documentation.
    """
    return asyncio.run(
        suggest_world_fact(
            project=project,
            existing_facts=existing_facts,
            premise=premise,
            fact_type=fact_type,
            needs_hint=needs_hint,
            guidance=guidance,
            language=language,
            assigned_id=assigned_id,
            config=config,
            style=style,
        )
    )


__all__ = ["suggest_world_fact", "suggest_world_fact_sync"]
