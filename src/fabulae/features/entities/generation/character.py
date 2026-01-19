"""Character generation function for CRUD and create commands.

This module provides a unified character generation function that works
for both CRUD suggest commands and the create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fabulae.features.entities.generation.prompts import build_character_prompt
from fabulae.features.entities.generation.schemas import CharacterSuggestionOutput
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Character

if TYPE_CHECKING:
    from fabulae.models import Project


async def suggest_character(
    project: Project | None = None,
    existing_characters: list[Character] | None = None,
    premise: str | None = None,
    role_hint: str | None = None,
    name_hint: str | None = None,
    needs_hint: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Character:
    """Suggest a character based on context.

    This function is used by both:
    - `fabulae character suggest` command (CRUD)
    - `fabulae create` command's character generation phase

    There are two usage patterns:

    1. CRUD mode (pass project):
       ```python
       character = await suggest_character(
           project=project,
           guidance="a mysterious mentor figure",
           config=llm_config,
       )
       ```

    2. Create mode (pass individual parameters):
       ```python
       character = await suggest_character(
           existing_characters=state.characters,
           premise=premise,
           role_hint="protagonist",
           needs_hint="The hero who drives the plot",
           assigned_id="character-01",
           language="en",
           config=llm_config,
       )
       ```

    Args:
        project: Existing project for context (for CRUD suggest).
            If provided, extracts premise and existing characters from it.
        existing_characters: Characters already in project (for avoiding duplicates).
            Overrides project.characters if both are provided.
        premise: Story premise for thematic alignment.
            Overrides project.plot.premise if both are provided.
        role_hint: Suggested role (protagonist, antagonist, supporting).
        name_hint: Suggested name (from shape slot or user input).
        needs_hint: What this character should provide to the story.
        guidance: User-provided guidance text for the character.
        language: Language code for content generation (e.g., 'en', 'de').
            Overrides project.style.language if both are provided.
        assigned_id: Pre-assigned ID to use (for create pipeline).
            If not provided, LLM generates the ID.
        config: LLM configuration. Required.

    Returns:
        Generated Character model instance.

    Raises:
        ValueError: If config is not provided.
    """
    if config is None:
        raise ValueError("LLM config is required for character generation")

    # Build context from project or individual parameters
    if project:
        if existing_characters is None:
            existing_characters = project.characters
        if premise is None and project.plot:
            premise = project.plot.premise
        if language is None and project.style:
            language = project.style.language

    # Build prompt
    prompt = build_character_prompt(
        premise=premise,
        existing_characters=existing_characters,
        role_hint=role_hint,
        name_hint=name_hint,
        needs_hint=needs_hint,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
    )

    # Generate using LLM
    user_prompt = "Generate a character based on the context provided."
    if role_hint:
        user_prompt = f"Create a character for the role: {role_hint}"
    elif guidance:
        user_prompt = f"Create a character: {guidance[:100]}"

    agent = create_agent(CharacterSuggestionOutput, prompt, config)
    result = await agent.run(user_prompt)
    suggestion = result.output

    # Convert to Character model
    return Character(
        id=suggestion.id,
        name=suggestion.name,
        role=suggestion.role,
        desire=suggestion.desire,
        need=suggestion.need,
        flaw=suggestion.flaw,
        secret=suggestion.secret,
        traits=suggestion.traits,
    )


def suggest_character_sync(
    project: Project | None = None,
    existing_characters: list[Character] | None = None,
    premise: str | None = None,
    role_hint: str | None = None,
    name_hint: str | None = None,
    needs_hint: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Character:
    """Synchronous wrapper for suggest_character.

    See suggest_character for argument documentation.
    """
    return asyncio.run(
        suggest_character(
            project=project,
            existing_characters=existing_characters,
            premise=premise,
            role_hint=role_hint,
            name_hint=name_hint,
            needs_hint=needs_hint,
            guidance=guidance,
            language=language,
            assigned_id=assigned_id,
            config=config,
        )
    )


__all__ = ["suggest_character", "suggest_character_sync"]
