"""Build service for orchestrating narrative generation."""

from __future__ import annotations

import random
from datetime import datetime

from fabulae import __version__
from fabulae.features.build.pipelines.batch import (
    build_chaptered_batch,
    build_micro_prose_batch,
    build_poem_batch,
    build_scenes_batch,
)
from fabulae.features.build.pipelines.sequential import (
    build_chaptered_sequential,
    build_micro_prose_sequential,
    build_poem_sequential,
    build_scenes_sequential,
)
from fabulae.features.build.progress import BuildProgress
from fabulae.features.build.schemas import (
    BuildMetadata,
    BuildOptions,
    BuildOutput,
    ChapterOutput,
    SceneOutput,
)
from fabulae.llm import LLMConfig
from fabulae.models import Project


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def _combine_chapters(chapters: list[ChapterOutput]) -> str:
    """Combine chapter outputs into full text."""
    parts: list[str] = []
    for chapter in chapters:
        if chapter.title:
            parts.append(f"# {chapter.title}\n")
        scene_text = _combine_scenes(chapter.scenes)
        parts.append(scene_text)
    return "\n\n".join(parts)


def _combine_scenes(scenes: list[SceneOutput]) -> str:
    """Combine scene outputs into full text."""
    parts: list[str] = []
    for scene in scenes:
        if scene.title:
            parts.append(f"## {scene.title}\n")
        parts.append(scene.content)
    return "\n\n".join(parts)


def _create_metadata(
    project: Project,
    config: LLMConfig,
    seed: int | None,
) -> BuildMetadata:
    """Create build metadata."""
    return BuildMetadata(
        project_name=project.plot.title or project.config.title or "Untitled",
        format=project.plot.format or "novel",
        seed=seed,
        model=config.model,
        temperature=config.temperature,
        timestamp=datetime.now(),
        version=__version__,
    )


async def _build_chaptered(
    project: Project,
    config: LLMConfig,
    seed: int | None,
    progress: BuildProgress | None,
    expected_language: str | None,
    options: BuildOptions,
) -> BuildOutput:
    """Build prose for chaptered formats (novel, novella)."""
    if not project.plot.chapters:
        if progress:
            progress.warn(
                "No chapters found — building scenes without chapter structure. "
                "Add chapters to plot.yml for chaptered output."
            )
        return await _build_short_story(project, config, seed, progress, expected_language, options)

    # Choose pipeline based on options
    if options.pipeline == "batch":
        chapters, _ = await build_chaptered_batch(project, config, options, progress, expected_language)
    else:
        chapters, _ = await build_chaptered_sequential(project, config, options, progress, expected_language)

    full_text = _combine_chapters(chapters)
    return BuildOutput(
        metadata=_create_metadata(project, config, seed),
        chapters=chapters,
        full_text=full_text,
        total_word_count=_count_words(full_text),
    )


async def _build_short_story(
    project: Project,
    config: LLMConfig,
    seed: int | None,
    progress: BuildProgress | None,
    expected_language: str | None,
    options: BuildOptions,
) -> BuildOutput:
    """Build prose for short-story format (scenes without chapters)."""
    # Choose pipeline based on options
    if options.pipeline == "batch":
        scenes, _ = await build_scenes_batch(project, config, options, progress, expected_language)
    else:
        scenes, _ = await build_scenes_sequential(project, config, options, progress, expected_language)

    full_text = _combine_scenes(scenes)
    return BuildOutput(
        metadata=_create_metadata(project, config, seed),
        scenes=scenes,
        full_text=full_text,
        total_word_count=_count_words(full_text),
    )


async def _build_micro_prose(
    project: Project,
    config: LLMConfig,
    seed: int | None,
    progress: BuildProgress | None,
    expected_language: str | None,
    options: BuildOptions,
) -> BuildOutput:
    """Build prose for micro-prose format (fragments)."""
    # Choose pipeline based on options
    if options.pipeline == "batch":
        fragments = await build_micro_prose_batch(project, config, options, progress, expected_language)
    else:
        fragments = await build_micro_prose_sequential(project, config, options, progress, expected_language)

    full_text = "\n\n---\n\n".join(f.content for f in fragments)
    return BuildOutput(
        metadata=_create_metadata(project, config, seed),
        fragments=fragments,
        full_text=full_text,
        total_word_count=_count_words(full_text),
    )


async def _build_poem(
    project: Project,
    config: LLMConfig,
    seed: int | None,
    progress: BuildProgress | None,
    expected_language: str | None,
    options: BuildOptions,
) -> BuildOutput:
    """Build prose for poem format (stanzas or lines)."""
    # Choose pipeline based on options
    if options.pipeline == "batch":
        stanzas, poem_text = await build_poem_batch(project, config, options, progress, expected_language)
    else:
        stanzas, poem_text = await build_poem_sequential(project, config, options, progress, expected_language)

    if stanzas is not None:
        full_text = "\n\n".join("\n".join(s.lines) for s in stanzas)
        return BuildOutput(
            metadata=_create_metadata(project, config, seed),
            stanzas=stanzas,
            full_text=full_text,
            total_word_count=_count_words(full_text),
        )

    # Line-based poem
    return BuildOutput(
        metadata=_create_metadata(project, config, seed),
        poem=poem_text,
        full_text=poem_text or "",
        total_word_count=_count_words(poem_text or ""),
    )


async def build_project(
    project: Project,
    config: LLMConfig,
    seed: int | None = None,
    progress: BuildProgress | None = None,
    expected_language: str | None = None,
    options: BuildOptions | None = None,
) -> BuildOutput:
    """Orchestrate the complete build process.

    Args:
        project: The Fabulae project to build.
        config: LLM configuration.
        seed: Optional seed for reproducibility.
        progress: Optional progress display.
        expected_language: ISO 639-1 code for language enforcement (e.g. 'de').
        options: Build options (pipeline mode, enhanced mode). Defaults to sequential with enhanced.

    Returns:
        BuildOutput with complete generated narrative.

    Raises:
        ValueError: If the project format is unknown.
    """
    if seed is not None:
        random.seed(seed)

    if options is None:
        options = BuildOptions()

    format_type = project.plot.format or "novel"

    if format_type in ("novel", "novella"):
        return await _build_chaptered(project, config, seed, progress, expected_language, options)
    elif format_type == "short-story":
        return await _build_short_story(project, config, seed, progress, expected_language, options)
    elif format_type == "micro-prose":
        return await _build_micro_prose(project, config, seed, progress, expected_language, options)
    elif format_type == "poem":
        return await _build_poem(project, config, seed, progress, expected_language, options)
    else:
        raise ValueError(f"Unknown format: {format_type}")


__all__ = ["build_project"]
