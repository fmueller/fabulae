"""Batch build pipeline with full context (no sliding window)."""

from __future__ import annotations

from collections.abc import Callable

from fabulae.features.build.scene_builder import (
    build_enhanced_fragment,
    build_enhanced_scene,
    build_enhanced_stanza,
    build_fragment,
    build_poem_from_lines,
    build_scene,
    build_stanza,
    generate_continuity_summary,
)
from fabulae.features.build.schemas import (
    BuildOptions,
    ChapterOutput,
    FragmentOutput,
    SceneOutput,
    StanzaOutput,
)
from fabulae.features.create.progress import CreateProgress
from fabulae.llm import LLMConfig
from fabulae.models import Project, Scene


def _get_scene_by_id(scene_id: str, project: Project) -> Scene:
    """Get a scene by its ID."""
    for scene in project.plot.scenes:
        if scene.id == scene_id:
            return scene
    raise ValueError(f"Scene not found: {scene_id}")


def _make_language_correction_callback(
    progress: CreateProgress | None,
) -> Callable[[str, str, int], None] | None:
    """Create a callback to notify user of language correction attempts."""
    if progress is None:
        return None

    def notify(expected: str, detected: str, attempt: int) -> None:
        progress.info(f"Language mismatch (expected: {expected}, got: {detected}), correcting (attempt {attempt})...")

    return notify


async def build_chaptered_batch(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> tuple[list[ChapterOutput], list[str]]:
    """Build chaptered format (novel/novella) with full context.

    Unlike sequential mode, batch mode includes ALL prior summaries and hooks
    in the context, providing better coherence for models with large context windows.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options including enhanced mode.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.

    Returns:
        Tuple of (chapter outputs, all prior summaries).
    """
    if not project.plot.chapters:
        return [], []

    chapters: list[ChapterOutput] = []
    prior_summaries: list[str] = []
    prior_hooks: list[str] = []
    total_scenes = sum(len(ch.scene_ids or []) for ch in project.plot.chapters)
    scene_count = 0
    on_language_correction = _make_language_correction_callback(progress)

    for chapter in project.plot.chapters:
        if not chapter.scene_ids:
            continue

        chapter_scenes: list[SceneOutput] = []
        chapter_hook = None

        for scene_id in chapter.scene_ids:
            scene = _get_scene_by_id(scene_id, project)
            scene_count += 1

            if progress:
                progress.console.print(f"  [dim]Building scene {scene_count}/{total_scenes}: {scene_id}[/dim]")

            # Use ALL prior context (batch mode - no sliding window)
            prior_context = "\n\n".join(prior_summaries)

            if options.enhanced:
                scene_output = await build_enhanced_scene(
                    scene=scene,
                    project=project,
                    prior_context=prior_context,
                    config=config,
                    chapter_id=chapter.id,
                    prior_hooks=prior_hooks,  # All hooks for diversity
                    expected_language=expected_language,
                    on_language_correction=on_language_correction,
                )
                if scene_output.hook:
                    prior_hooks.append(scene_output.hook.content)
                    if chapter_hook is None:
                        chapter_hook = scene_output.hook
            else:
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
            hook=chapter_hook,
            scenes=chapter_scenes,
            word_count=sum(s.word_count for s in chapter_scenes),
        )
        chapters.append(chapter_output)

    return chapters, prior_summaries


async def build_scenes_batch(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> tuple[list[SceneOutput], list[str]]:
    """Build short-story format (scenes without chapters) with full context.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.

    Returns:
        Tuple of (scene outputs, all prior summaries).
    """
    scenes: list[SceneOutput] = []
    prior_summaries: list[str] = []
    prior_hooks: list[str] = []
    total_scenes = len(project.plot.scenes)
    on_language_correction = _make_language_correction_callback(progress)

    # Determine scene order
    scene_order = project.plot.scene_ids or [s.id for s in project.plot.scenes]

    for i, scene_id in enumerate(scene_order, 1):
        scene = _get_scene_by_id(scene_id, project)

        if progress:
            progress.console.print(f"  [dim]Building scene {i}/{total_scenes}: {scene_id}[/dim]")

        # Use ALL prior context (batch mode)
        prior_context = "\n\n".join(prior_summaries)

        if options.enhanced:
            scene_output = await build_enhanced_scene(
                scene=scene,
                project=project,
                prior_context=prior_context,
                config=config,
                prior_hooks=prior_hooks,
                expected_language=expected_language,
                on_language_correction=on_language_correction,
            )
            if scene_output.hook:
                prior_hooks.append(scene_output.hook.content)
        else:
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

    return scenes, prior_summaries


async def build_micro_prose_batch(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> list[FragmentOutput]:
    """Build micro-prose format (fragments) with full context.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.

    Returns:
        List of fragment outputs.
    """
    fragments: list[FragmentOutput] = []
    prior_contents: list[str] = []
    prior_hooks: list[str] = []
    total_fragments = len(project.plot.fragments)
    on_language_correction = _make_language_correction_callback(progress)

    for i, fragment in enumerate(project.plot.fragments, 1):
        if progress:
            progress.console.print(f"  [dim]Building fragment {i}/{total_fragments}: {fragment.id}[/dim]")

        if options.enhanced:
            fragment_output = await build_enhanced_fragment(
                fragment=fragment,
                project=project,
                prior_fragments=prior_contents,  # All prior fragments
                config=config,
                prior_hooks=prior_hooks,
                expected_language=expected_language,
                on_language_correction=on_language_correction,
            )
            if fragment_output.hook:
                prior_hooks.append(fragment_output.hook.content)
        else:
            fragment_output = await build_fragment(
                fragment=fragment,
                project=project,
                prior_fragments=prior_contents,
                config=config,
                expected_language=expected_language,
                on_language_correction=on_language_correction,
            )

        fragments.append(fragment_output)
        prior_contents.append(fragment_output.content)

    return fragments


async def build_poem_batch(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
) -> tuple[list[StanzaOutput] | None, str | None]:
    """Build poem format (stanzas or lines) with full context.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.

    Returns:
        Tuple of (stanza outputs or None, poem text or None).
    """
    on_language_correction = _make_language_correction_callback(progress)

    # If we have stanzas, generate them individually
    if project.plot.stanzas:
        stanzas: list[StanzaOutput] = []
        prior_stanzas: list[list[str]] = []
        prior_hooks: list[str] = []
        total_stanzas = len(project.plot.stanzas)

        for i, stanza in enumerate(project.plot.stanzas, 1):
            if progress:
                progress.console.print(f"  [dim]Building stanza {i}/{total_stanzas}: {stanza.id}[/dim]")

            if options.enhanced:
                stanza_output = await build_enhanced_stanza(
                    stanza=stanza,
                    project=project,
                    prior_stanzas=prior_stanzas,  # All prior stanzas
                    config=config,
                    prior_hooks=prior_hooks,
                    expected_language=expected_language,
                    on_language_correction=on_language_correction,
                )
                if stanza_output.hook:
                    prior_hooks.append(stanza_output.hook.content)
            else:
                stanza_output = await build_stanza(
                    stanza=stanza,
                    project=project,
                    prior_stanzas=prior_stanzas,
                    config=config,
                    expected_language=expected_language,
                    on_language_correction=on_language_correction,
                )

            stanzas.append(stanza_output)
            prior_stanzas.append(stanza_output.lines)

        return stanzas, None

    # If we only have lines, generate the complete poem
    if progress:
        progress.console.print("  [dim]Building poem...[/dim]")

    poem_text = await build_poem_from_lines(
        project, config, expected_language=expected_language, on_language_correction=on_language_correction
    )
    return None, poem_text


__all__ = [
    "build_chaptered_batch",
    "build_micro_prose_batch",
    "build_poem_batch",
    "build_scenes_batch",
]
