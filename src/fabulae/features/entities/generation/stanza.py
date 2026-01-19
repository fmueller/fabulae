"""Stanza generation function for CRUD and create commands.

This module provides a unified stanza generation function that works
for both CRUD suggest commands and the poem create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fabulae.features.entities.generation.prompts import build_stanza_prompt
from fabulae.features.entities.generation.schemas import StanzaSuggestionOutput
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Stanza

if TYPE_CHECKING:
    from fabulae.models import Project


async def suggest_stanza(
    project: Project | None = None,
    existing_stanzas: list[Stanza] | None = None,
    premise: str | None = None,
    position: int | None = None,
    total_stanzas: int | None = None,
    target_line_count: int = 4,
    poem_form: str | None = None,
    previous_stanza_texts: list[str] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Stanza:
    """Suggest a stanza based on context.

    This function is used by both:
    - `fabulae stanza suggest` command (CRUD)
    - `fabulae create` command's stanza generation phase (poem)

    There are two usage patterns:

    1. CRUD mode (pass project):
       ```python
       stanza = await suggest_stanza(
           project=project,
           guidance="a melancholic reflection on loss",
           config=llm_config,
       )
       ```

    2. Create mode (pass individual parameters):
       ```python
       stanza = await suggest_stanza(
           existing_stanzas=state.stanzas,
           premise=premise,
           position=2,
           total_stanzas=4,
           target_line_count=4,
           poem_form="sonnet",
           previous_stanza_texts=["First stanza...", "Second stanza..."],
           assigned_id="stanza-03",
           language="en",
           config=llm_config,
       )
       ```

    Args:
        project: Existing project for context (for CRUD suggest).
            If provided, extracts premise and existing stanzas from it.
        existing_stanzas: Stanzas already in poem (for context).
            Overrides project.plot.stanzas if both are provided.
        premise: Poem premise/theme for thematic alignment.
            Overrides project.plot.premise if both are provided.
        position: Position in sequence (0-indexed) for create pipeline.
        total_stanzas: Total number of stanzas for create pipeline.
        target_line_count: Number of lines for this stanza (default: 4).
        poem_form: Form of the poem (sonnet, haiku, etc.).
            Overrides project.plot.poem_form if both are provided.
        previous_stanza_texts: Text of previous stanzas for continuity.
            Used instead of existing_stanzas for sliding window context.
        guidance: User-provided guidance text for the stanza.
        language: Language code for content generation (e.g., 'en', 'de').
            Overrides project.style.language if both are provided.
        assigned_id: Pre-assigned ID to use (for create pipeline).
            If not provided, LLM generates the ID.
        config: LLM configuration. Required.

    Returns:
        Generated Stanza model instance.

    Raises:
        ValueError: If config is not provided.
    """
    if config is None:
        raise ValueError("LLM config is required for stanza generation")

    # Build context from project or individual parameters
    if project:
        if existing_stanzas is None:
            existing_stanzas = project.plot.stanzas
        if premise is None and project.plot:
            premise = project.plot.premise
        if poem_form is None and project.plot:
            poem_form = project.plot.poem_form
        if language is None and project.style:
            language = project.style.language

    # Build prompt
    prompt = build_stanza_prompt(
        premise=premise,
        existing_stanzas=existing_stanzas,
        position=position,
        total_stanzas=total_stanzas,
        target_line_count=target_line_count,
        poem_form=poem_form,
        previous_stanza_texts=previous_stanza_texts,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
    )

    # Generate using LLM
    user_prompt = f"Generate a stanza with {target_line_count} lines."
    if position is not None and total_stanzas:
        user_prompt = f"Generate stanza {position + 1} of {total_stanzas} with {target_line_count} lines."
    elif guidance:
        user_prompt = f"Create a stanza: {guidance[:100]}"

    agent = create_agent(StanzaSuggestionOutput, prompt, config)
    result = await agent.run(user_prompt)
    suggestion = result.output

    # Convert to Stanza model
    return Stanza(
        id=suggestion.id,
        lines=suggestion.lines,
        meter=suggestion.meter,
        rhyme_scheme=suggestion.rhyme_scheme,
    )


def suggest_stanza_sync(
    project: Project | None = None,
    existing_stanzas: list[Stanza] | None = None,
    premise: str | None = None,
    position: int | None = None,
    total_stanzas: int | None = None,
    target_line_count: int = 4,
    poem_form: str | None = None,
    previous_stanza_texts: list[str] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
) -> Stanza:
    """Synchronous wrapper for suggest_stanza.

    See suggest_stanza for argument documentation.
    """
    return asyncio.run(
        suggest_stanza(
            project=project,
            existing_stanzas=existing_stanzas,
            premise=premise,
            position=position,
            total_stanzas=total_stanzas,
            target_line_count=target_line_count,
            poem_form=poem_form,
            previous_stanza_texts=previous_stanza_texts,
            guidance=guidance,
            language=language,
            assigned_id=assigned_id,
            config=config,
        )
    )


__all__ = ["suggest_stanza", "suggest_stanza_sync"]
