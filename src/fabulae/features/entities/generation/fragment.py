"""Fragment generation function for CRUD and create commands.

This module provides a unified fragment generation function that works
for both CRUD suggest commands and the micro-prose create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fabulae.features.entities.generation.prompts import build_fragment_prompt
from fabulae.features.entities.generation.schemas import FragmentSuggestionOutput
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Fragment

if TYPE_CHECKING:
    from fabulae.models import Project


async def suggest_fragment(
    project: Project | None = None,
    existing_fragments: list[Fragment] | None = None,
    premise: str | None = None,
    position: int | None = None,
    total_fragments: int | None = None,
    previous_content: list[str] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Fragment:
    """Suggest a fragment based on context.

    This function is used by both:
    - `fabulae fragment suggest` command (CRUD)
    - `fabulae create` command's fragment generation phase (micro-prose)

    There are two usage patterns:

    1. CRUD mode (pass project):
       ```python
       fragment = await suggest_fragment(
           project=project,
           guidance="a moment of reflection",
           config=llm_config,
       )
       ```

    2. Create mode (pass individual parameters):
       ```python
       fragment = await suggest_fragment(
           existing_fragments=state.fragments,
           premise=premise,
           position=2,
           total_fragments=5,
           previous_content=["Fragment 1 content...", "Fragment 2 content..."],
           assigned_id="fragment-03",
           language="en",
           config=llm_config,
       )
       ```

    Args:
        project: Existing project for context (for CRUD suggest).
            If provided, extracts premise and existing fragments from it.
        existing_fragments: Fragments already in project (for context).
            Overrides project.plot.fragments if both are provided.
        premise: Story premise for thematic alignment.
            Overrides project.plot.premise if both are provided.
        position: Position in sequence (0-indexed) for create pipeline.
        total_fragments: Total number of fragments for create pipeline.
        previous_content: Content of previous fragments for continuity.
            Used instead of existing_fragments for sliding window context.
        guidance: User-provided guidance text for the fragment.
        language: Language code for content generation (e.g., 'en', 'de').
            Overrides project.style.language if both are provided.
        assigned_id: Pre-assigned ID to use (for create pipeline).
            If not provided, LLM generates the ID.
        config: LLM configuration. Required.

    Returns:
        Generated Fragment model instance.

    Raises:
        ValueError: If config is not provided.
    """
    if config is None:
        raise ValueError("LLM config is required for fragment generation")

    # Build context from project or individual parameters
    if project:
        if existing_fragments is None:
            existing_fragments = project.plot.fragments
        if premise is None and project.plot:
            premise = project.plot.premise
        if language is None and project.style:
            language = project.style.language

    # Build prompt
    prompt = build_fragment_prompt(
        premise=premise,
        existing_fragments=existing_fragments,
        position=position,
        total_fragments=total_fragments,
        previous_content=previous_content,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
    )

    # Generate using LLM
    user_prompt = "Generate a flash fiction fragment."
    if position is not None and total_fragments:
        user_prompt = f"Generate fragment {position + 1} of {total_fragments}."
    elif guidance:
        user_prompt = f"Create a fragment: {guidance[:100]}"

    agent = create_agent(FragmentSuggestionOutput, prompt, config)
    result = await agent.run(user_prompt)
    suggestion = result.output

    # Convert to Fragment model
    return Fragment(
        id=suggestion.id,
        content=suggestion.content,
        target_words=suggestion.target_words,
        notes=suggestion.notes,
    )


def suggest_fragment_sync(
    project: Project | None = None,
    existing_fragments: list[Fragment] | None = None,
    premise: str | None = None,
    position: int | None = None,
    total_fragments: int | None = None,
    previous_content: list[str] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Fragment:
    """Synchronous wrapper for suggest_fragment.

    See suggest_fragment for argument documentation.
    """
    return asyncio.run(
        suggest_fragment(
            project=project,
            existing_fragments=existing_fragments,
            premise=premise,
            position=position,
            total_fragments=total_fragments,
            previous_content=previous_content,
            guidance=guidance,
            language=language,
            assigned_id=assigned_id,
            config=config,
        )
    )


__all__ = ["suggest_fragment", "suggest_fragment_sync"]
