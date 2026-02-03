"""Build service for orchestrating narrative generation."""

from __future__ import annotations

import random
from collections.abc import Callable
from datetime import datetime

from fabulae import __version__
from fabulae.features.build.scene_builder import (
    build_fragment,
    build_poem_from_lines,
    build_scene,
    build_stanza,
    generate_continuity_summary,
)
from fabulae.features.build.schemas import (
    BuildMetadata,
    BuildOutput,
    ChapterOutput,
    FragmentOutput,
    SceneOutput,
    StanzaOutput,
)
from fabulae.features.create.progress import CreateProgress
from fabulae.llm import LLMConfig
from fabulae.models import Project, Scene

SLIDING_WINDOW_SIZE = 5


def _make_language_correction_callback(
    progress: CreateProgress | None,
) -> Callable[[str, str, int], None] | None:
    """Create a callback to notify user of language correction attempts.

    Args:
        progress: Progress display instance, or None if not available.

    Returns:
        A callback function, or None if progress is not available.
    """
    if progress is None:
        return None

    def notify(expected: str, detected: str, attempt: int) -> None:
        progress.info(f"Language mismatch (expected: {expected}, got: {detected}), correcting (attempt {attempt})...")

    return notify


def _get_scene_by_id(scene_id: str, project: Project) -> Scene:
    """Get a scene by its ID."""
    for scene in project.plot.scenes:
        if scene.id == scene_id:
            return scene
    raise ValueError(f"Scene not found: {scene_id}")


def _count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


async def _build_chaptered(
    project: Project,
    config: LLMConfig,
    seed: int | None,
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> BuildOutput:
    """Build prose for chaptered formats (novel, novella)."""
    if not project.plot.chapters:
        if progress:
            progress.warn(
                "No chapters found — building scenes without chapter structure. "
                "Add chapters to plot.yml for chaptered output."
            )
        return await _build_short_story(project, config, seed, progress, expected_language)

    chapters: list[ChapterOutput] = []
    prior_summaries: list[str] = []
    total_scenes = sum(len(ch.scene_ids or []) for ch in project.plot.chapters)
    scene_count = 0
    on_language_correction = _make_language_correction_callback(progress)

    for chapter in project.plot.chapters:
        if not chapter.scene_ids:
            continue

        chapter_scenes: list[SceneOutput] = []
        for scene_id in chapter.scene_ids:
            scene = _get_scene_by_id(scene_id, project)
            scene_count += 1

            if progress:
                progress.console.print(f"  [dim]Building scene {scene_count}/{total_scenes}: {scene_id}[/dim]")

            # Use sliding window for prior context
            prior_context = "\n\n".join(prior_summaries[-SLIDING_WINDOW_SIZE:])

            scene_output = await build_scene(
                scene=scene,
                project=project,
                prior_context=prior_context,
                config=config,
                chapter_id=chapter.id,
                expected_language=expected_language,
                on_language_correction=on_language_correction,
            )
            chapter_scenes.append(scene_output)

            # Generate continuity summary
            summary = await generate_continuity_summary(scene_output.content, config)
            prior_summaries.append(summary)

        chapter_output = ChapterOutput(
            chapter_id=chapter.id,
            title=chapter.title,
            scenes=chapter_scenes,
            word_count=sum(s.word_count for s in chapter_scenes),
        )
        chapters.append(chapter_output)

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
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> BuildOutput:
    """Build prose for short-story format (scenes without chapters)."""
    scenes: list[SceneOutput] = []
    prior_summaries: list[str] = []
    total_scenes = len(project.plot.scenes)
    on_language_correction = _make_language_correction_callback(progress)

    # Determine scene order
    scene_order = project.plot.scene_ids or [s.id for s in project.plot.scenes]

    for i, scene_id in enumerate(scene_order, 1):
        scene = _get_scene_by_id(scene_id, project)

        if progress:
            progress.console.print(f"  [dim]Building scene {i}/{total_scenes}: {scene_id}[/dim]")

        # Use sliding window for prior context
        prior_context = "\n\n".join(prior_summaries[-SLIDING_WINDOW_SIZE:])

        scene_output = await build_scene(
            scene=scene,
            project=project,
            prior_context=prior_context,
            config=config,
            expected_language=expected_language,
            on_language_correction=on_language_correction,
        )
        scenes.append(scene_output)

        # Generate continuity summary
        summary = await generate_continuity_summary(scene_output.content, config)
        prior_summaries.append(summary)

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
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> BuildOutput:
    """Build prose for micro-prose format (fragments)."""
    fragments: list[FragmentOutput] = []
    prior_contents: list[str] = []
    total_fragments = len(project.plot.fragments)
    on_language_correction = _make_language_correction_callback(progress)

    for i, fragment in enumerate(project.plot.fragments, 1):
        if progress:
            progress.console.print(f"  [dim]Building fragment {i}/{total_fragments}: {fragment.id}[/dim]")

        fragment_output = await build_fragment(
            fragment=fragment,
            project=project,
            prior_fragments=prior_contents[-SLIDING_WINDOW_SIZE:],
            config=config,
            expected_language=expected_language,
            on_language_correction=on_language_correction,
        )
        fragments.append(fragment_output)
        prior_contents.append(fragment_output.content)

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
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> BuildOutput:
    """Build prose for poem format (stanzas or lines)."""
    on_language_correction = _make_language_correction_callback(progress)

    # If we have stanzas, generate them individually
    if project.plot.stanzas:
        stanzas: list[StanzaOutput] = []
        prior_stanzas: list[list[str]] = []
        total_stanzas = len(project.plot.stanzas)

        for i, stanza in enumerate(project.plot.stanzas, 1):
            if progress:
                progress.console.print(f"  [dim]Building stanza {i}/{total_stanzas}: {stanza.id}[/dim]")

            stanza_output = await build_stanza(
                stanza=stanza,
                project=project,
                prior_stanzas=prior_stanzas[-SLIDING_WINDOW_SIZE:],
                config=config,
                expected_language=expected_language,
                on_language_correction=on_language_correction,
            )
            stanzas.append(stanza_output)
            prior_stanzas.append(stanza_output.lines)

        full_text = "\n\n".join("\n".join(s.lines) for s in stanzas)
        return BuildOutput(
            metadata=_create_metadata(project, config, seed),
            stanzas=stanzas,
            full_text=full_text,
            total_word_count=_count_words(full_text),
        )

    # If we only have lines, generate the complete poem
    if progress:
        progress.console.print("  [dim]Building poem...[/dim]")

    poem_text = await build_poem_from_lines(
        project, config, expected_language=expected_language, on_language_correction=on_language_correction
    )
    return BuildOutput(
        metadata=_create_metadata(project, config, seed),
        poem=poem_text,
        full_text=poem_text,
        total_word_count=_count_words(poem_text),
    )


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


async def build_project(
    project: Project,
    config: LLMConfig,
    seed: int | None = None,
    progress: CreateProgress | None = None,
    expected_language: str | None = None,
) -> BuildOutput:
    """Orchestrate the complete build process.

    Args:
        project: The Fabulae project to build.
        config: LLM configuration.
        seed: Optional seed for reproducibility.
        progress: Optional progress display.
        expected_language: ISO 639-1 code for language enforcement (e.g. 'de').

    Returns:
        BuildOutput with complete generated narrative.

    Raises:
        ValueError: If the project format is unknown.
    """
    if seed is not None:
        random.seed(seed)

    format_type = project.plot.format or "novel"

    if format_type in ("novel", "novella"):
        return await _build_chaptered(project, config, seed, progress, expected_language)
    elif format_type == "short-story":
        return await _build_short_story(project, config, seed, progress, expected_language)
    elif format_type == "micro-prose":
        return await _build_micro_prose(project, config, seed, progress, expected_language)
    elif format_type == "poem":
        return await _build_poem(project, config, seed, progress, expected_language)
    else:
        raise ValueError(f"Unknown format: {format_type}")


__all__ = ["build_project"]
