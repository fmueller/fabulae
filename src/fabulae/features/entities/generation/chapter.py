"""Chapter generation function for CRUD and create commands.

This module provides a unified chapter generation function that works
for both CRUD suggest commands and the create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fabulae.features.entities.generation.prompts import build_chapter_prompt
from fabulae.features.entities.generation.schemas import ChapterOutput
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Chapter

if TYPE_CHECKING:
    from fabulae.features.create.schemas import StyleOutput
    from fabulae.models import Project, Scene


async def suggest_chapter(
    project: Project | None = None,
    existing_chapters: list[Chapter] | None = None,
    existing_scenes: list[Scene] | None = None,
    premise: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
    style: StyleOutput | None = None,
) -> Chapter:
    """Suggest a chapter based on context.

    This function is used by both:
    - `fabulae chapter suggest` command (CRUD)
    - `fabulae create` command's chapter generation phase

    There are two usage patterns:

    1. CRUD mode (pass project):
       ```python
       chapter = await suggest_chapter(
           project=project,
           guidance="a climactic confrontation",
           config=llm_config,
       )
       ```

    2. Create mode (pass individual parameters):
       ```python
       chapter = await suggest_chapter(
           existing_chapters=state.chapters,
           existing_scenes=state.scenes,
           premise=premise,
           assigned_id="chapter-01",
           language="en",
           style=style_output,
           config=llm_config,
       )
       ```

    Args:
        project: Existing project for context (for CRUD suggest).
            If provided, extracts chapters, scenes, and premise from it.
        existing_chapters: Chapters already in project (to avoid duplicates).
            Overrides project.plot.chapters if both are provided.
        existing_scenes: Scenes in project (for context).
            Overrides project.plot.scenes if both are provided.
        premise: Story premise for thematic alignment.
            Overrides project.plot.premise if both are provided.
        guidance: User-provided guidance text for the chapter.
        language: Language code for content generation (e.g., 'en', 'de').
            Overrides project.style.language if both are provided.
        assigned_id: Pre-assigned ID to use (for create pipeline).
            If not provided, LLM generates the ID.
        config: LLM configuration. Required.
        style: StyleOutput for narrative style context (from create pipeline).

    Returns:
        Generated Chapter model instance.

    Raises:
        ValueError: If config is not provided.
    """
    if config is None:
        raise ValueError("LLM config is required for chapter generation")

    if project:
        if existing_chapters is None:
            existing_chapters = project.plot.chapters
        if existing_scenes is None:
            existing_scenes = project.plot.scenes
        if premise is None and project.plot:
            premise = project.plot.premise
        if language is None and project.style:
            language = project.style.language

    prompt = build_chapter_prompt(
        premise=premise,
        existing_chapters=existing_chapters,
        existing_scenes=existing_scenes,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
        style=style,
    )

    user_prompt = "Generate a chapter based on the context provided."
    if guidance:
        user_prompt = f"Create a chapter: {guidance[:100]}"

    agent = create_agent(ChapterOutput, prompt, config)
    result = await agent.run(user_prompt)
    suggestion = result.output

    return Chapter(
        id=suggestion.id,
        title=suggestion.title,
        summary=suggestion.summary,
        scene_ids=[],
    )


def suggest_chapter_sync(
    project: Project | None = None,
    existing_chapters: list[Chapter] | None = None,
    existing_scenes: list[Scene] | None = None,
    premise: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    config: LLMConfig | None = None,
    style: StyleOutput | None = None,
) -> Chapter:
    """Synchronous wrapper for suggest_chapter.

    See suggest_chapter for argument documentation.
    """
    return asyncio.run(
        suggest_chapter(
            project=project,
            existing_chapters=existing_chapters,
            existing_scenes=existing_scenes,
            premise=premise,
            guidance=guidance,
            language=language,
            assigned_id=assigned_id,
            config=config,
            style=style,
        )
    )


__all__ = ["suggest_chapter", "suggest_chapter_sync"]
