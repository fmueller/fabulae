"""Chapter generation function for CRUD and create commands.

This module provides a unified chapter generation function that works
for both CRUD suggest commands and the create pipeline.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from fabulae.features.entities.generation.prompts import build_chapter_prompt
from fabulae.features.entities.generation.schemas import ChapterOutput
from fabulae.features.entities.generation.title_structure import TitleRequirement, get_title_requirement
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
    chapter_index: int | None = None,
    total_chapters: int | None = None,
    scene_count: int | None = None,
    previous_chapter_summaries: list[str] | None = None,
    previous_chapter_titles: list[str] | None = None,
    title_requirement: TitleRequirement | None = None,
    max_title_retries: int = 0,
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

    2. Create mode (pass individual parameters with title diversity):
       ```python
       title_req = get_title_requirement(
           chapter_index=0,
           total_chapters=5,
           previous_titles=[],
       )
       chapter = await suggest_chapter(
           existing_chapters=state.chapters,
           existing_scenes=state.scenes,
           premise=premise,
           assigned_id="chapter-01",
           language="en",
           style=style_output,
           chapter_index=0,
           total_chapters=5,
           scene_count=3,
           previous_chapter_summaries=[],
           previous_chapter_titles=[],
           title_requirement=title_req,
           max_title_retries=1,
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
        chapter_index: 0-based chapter position (create pipeline).
        total_chapters: Total number of chapters (create pipeline).
        scene_count: Number of scenes in this chapter (create pipeline).
        previous_chapter_summaries: Recent chapter summaries for continuity.
        previous_chapter_titles: Previous titles for title diversity.
        title_requirement: Title structure requirements (create pipeline).
            If not provided but chapter_index is, will auto-generate.
        max_title_retries: Number of retries if title doesn't meet requirements.

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

    title_req = title_requirement
    if title_req is None and chapter_index is not None and total_chapters is not None:
        title_req = get_title_requirement(
            chapter_index=chapter_index,
            total_chapters=total_chapters,
            previous_titles=previous_chapter_titles or [],
        )

    title_requirement_str = None
    if title_req:
        title_requirement_str = title_req.format_for_prompt(language)

    prompt = build_chapter_prompt(
        premise=premise,
        existing_chapters=existing_chapters,
        existing_scenes=existing_scenes,
        guidance=guidance,
        language=language,
        assigned_id=assigned_id,
        style=style,
        chapter_index=chapter_index,
        total_chapters=total_chapters,
        scene_count=scene_count,
        previous_chapter_summaries=previous_chapter_summaries,
        title_requirement_str=title_requirement_str,
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
    chapter_index: int | None = None,
    total_chapters: int | None = None,
    scene_count: int | None = None,
    previous_chapter_summaries: list[str] | None = None,
    previous_chapter_titles: list[str] | None = None,
    title_requirement: TitleRequirement | None = None,
    max_title_retries: int = 0,
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
            chapter_index=chapter_index,
            total_chapters=total_chapters,
            scene_count=scene_count,
            previous_chapter_summaries=previous_chapter_summaries,
            previous_chapter_titles=previous_chapter_titles,
            title_requirement=title_requirement,
            max_title_retries=max_title_retries,
        )
    )


__all__ = ["suggest_chapter", "suggest_chapter_sync", "TitleRequirement", "get_title_requirement"]
