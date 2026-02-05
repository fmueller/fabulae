"""Sequential build pipeline with sliding window context."""

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
from fabulae.llm.json_guard import JsonErrorType, JsonGuardConfig
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


def _make_json_error_callback(
    progress: CreateProgress | None,
    max_retries: int = 2,
) -> Callable[[JsonErrorType, str, int], None] | None:
    """Create a callback to notify user of JSON error retries."""
    if progress is None:
        return None

    def notify(error_type: JsonErrorType, _error_msg: str, attempt: int) -> None:
        progress.info(f"JSON error ({error_type.name}), retrying (attempt {attempt}/{max_retries})...")

    return notify


async def build_chaptered_sequential(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
    json_guard_config: JsonGuardConfig | None = None,
) -> tuple[list[ChapterOutput], list[str]]:
    """Build chaptered format (novel/novella) with sliding window context.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options including enhanced mode and window size.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.
        json_guard_config: Configuration for JSON guard (retries, etc.).

    Returns:
        Tuple of (chapter outputs, prior summaries for full context).
    """
    if not project.plot.chapters:
        return [], []

    chapters: list[ChapterOutput] = []
    prior_summaries: list[str] = []
    prior_hooks: list[str] = []
    total_scenes = sum(len(ch.scene_ids or []) for ch in project.plot.chapters)
    scene_count = 0
    resolved_json_config = json_guard_config or JsonGuardConfig()
    on_language_correction = _make_language_correction_callback(progress)
    on_json_error = _make_json_error_callback(progress, resolved_json_config.max_retries)
    window_size = options.sliding_window_size

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

            # Use sliding window for prior context
            prior_context = "\n\n".join(prior_summaries[-window_size:])

            if options.enhanced:
                scene_output = await build_enhanced_scene(
                    scene=scene,
                    project=project,
                    prior_context=prior_context,
                    config=config,
                    chapter_id=chapter.id,
                    prior_hooks=prior_hooks[-window_size:],
                    expected_language=expected_language,
                    on_language_correction=on_language_correction,
                    on_json_error=on_json_error,
                )
                # Track hook for diversity
                if scene_output.hook:
                    prior_hooks.append(scene_output.hook.content)
                    # First scene's hook becomes chapter hook
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
                    on_json_error=on_json_error,
                )

            chapter_scenes.append(scene_output)

            # Generate continuity summary
            summary = await generate_continuity_summary(scene_output.content, config, on_json_error=on_json_error)
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


async def build_scenes_sequential(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
    json_guard_config: JsonGuardConfig | None = None,
) -> tuple[list[SceneOutput], list[str]]:
    """Build short-story format (scenes without chapters) with sliding window context.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.
        json_guard_config: Configuration for JSON guard (retries, etc.).

    Returns:
        Tuple of (scene outputs, prior summaries).
    """
    scenes: list[SceneOutput] = []
    prior_summaries: list[str] = []
    prior_hooks: list[str] = []
    total_scenes = len(project.plot.scenes)
    resolved_json_config = json_guard_config or JsonGuardConfig()
    on_language_correction = _make_language_correction_callback(progress)
    on_json_error = _make_json_error_callback(progress, resolved_json_config.max_retries)
    window_size = options.sliding_window_size

    # Determine scene order
    scene_order = project.plot.scene_ids or [s.id for s in project.plot.scenes]

    for i, scene_id in enumerate(scene_order, 1):
        scene = _get_scene_by_id(scene_id, project)

        if progress:
            progress.console.print(f"  [dim]Building scene {i}/{total_scenes}: {scene_id}[/dim]")

        # Use sliding window for prior context
        prior_context = "\n\n".join(prior_summaries[-window_size:])

        if options.enhanced:
            scene_output = await build_enhanced_scene(
                scene=scene,
                project=project,
                prior_context=prior_context,
                config=config,
                prior_hooks=prior_hooks[-window_size:],
                expected_language=expected_language,
                on_language_correction=on_language_correction,
                on_json_error=on_json_error,
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
                on_json_error=on_json_error,
            )

        scenes.append(scene_output)

        # Generate continuity summary
        summary = await generate_continuity_summary(scene_output.content, config, on_json_error=on_json_error)
        prior_summaries.append(summary)

    return scenes, prior_summaries


async def build_micro_prose_sequential(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
    json_guard_config: JsonGuardConfig | None = None,
) -> list[FragmentOutput]:
    """Build micro-prose format (fragments) with sliding window context.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.
        json_guard_config: Configuration for JSON guard (retries, etc.).

    Returns:
        List of fragment outputs.
    """
    fragments: list[FragmentOutput] = []
    prior_contents: list[str] = []
    prior_hooks: list[str] = []
    total_fragments = len(project.plot.fragments)
    resolved_json_config = json_guard_config or JsonGuardConfig()
    on_language_correction = _make_language_correction_callback(progress)
    on_json_error = _make_json_error_callback(progress, resolved_json_config.max_retries)
    window_size = options.sliding_window_size

    for i, fragment in enumerate(project.plot.fragments, 1):
        if progress:
            progress.console.print(f"  [dim]Building fragment {i}/{total_fragments}: {fragment.id}[/dim]")

        if options.enhanced:
            fragment_output = await build_enhanced_fragment(
                fragment=fragment,
                project=project,
                prior_fragments=prior_contents[-window_size:],
                config=config,
                prior_hooks=prior_hooks[-window_size:],
                expected_language=expected_language,
                on_language_correction=on_language_correction,
                on_json_error=on_json_error,
            )
            if fragment_output.hook:
                prior_hooks.append(fragment_output.hook.content)
        else:
            fragment_output = await build_fragment(
                fragment=fragment,
                project=project,
                prior_fragments=prior_contents[-window_size:],
                config=config,
                expected_language=expected_language,
                on_language_correction=on_language_correction,
                on_json_error=on_json_error,
            )

        fragments.append(fragment_output)
        prior_contents.append(fragment_output.content)

    return fragments


async def build_poem_sequential(
    project: Project,
    config: LLMConfig,
    options: BuildOptions,
    progress: CreateProgress | None,
    expected_language: str | None = None,
    json_guard_config: JsonGuardConfig | None = None,
) -> tuple[list[StanzaOutput] | None, str | None]:
    """Build poem format (stanzas or lines) with sliding window context.

    Args:
        project: The project to build.
        config: LLM configuration.
        options: Build options.
        progress: Progress display.
        expected_language: ISO 639-1 code for language enforcement.
        json_guard_config: Configuration for JSON guard (retries, etc.).

    Returns:
        Tuple of (stanza outputs or None, poem text or None).
    """
    resolved_json_config = json_guard_config or JsonGuardConfig()
    on_language_correction = _make_language_correction_callback(progress)
    on_json_error = _make_json_error_callback(progress, resolved_json_config.max_retries)
    window_size = options.sliding_window_size

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
                    prior_stanzas=prior_stanzas[-window_size:],
                    config=config,
                    prior_hooks=prior_hooks[-window_size:],
                    expected_language=expected_language,
                    on_language_correction=on_language_correction,
                    on_json_error=on_json_error,
                )
                if stanza_output.hook:
                    prior_hooks.append(stanza_output.hook.content)
            else:
                stanza_output = await build_stanza(
                    stanza=stanza,
                    project=project,
                    prior_stanzas=prior_stanzas[-window_size:],
                    config=config,
                    expected_language=expected_language,
                    on_language_correction=on_language_correction,
                    on_json_error=on_json_error,
                )

            stanzas.append(stanza_output)
            prior_stanzas.append(stanza_output.lines)

        return stanzas, None

    # If we only have lines, generate the complete poem
    if progress:
        progress.console.print("  [dim]Building poem...[/dim]")

    poem_text = await build_poem_from_lines(
        project,
        config,
        expected_language=expected_language,
        on_language_correction=on_language_correction,
        on_json_error=on_json_error,
    )
    return None, poem_text


__all__ = [
    "build_chaptered_sequential",
    "build_micro_prose_sequential",
    "build_poem_sequential",
    "build_scenes_sequential",
]
