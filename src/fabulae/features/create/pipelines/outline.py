"""Outline-only pipeline for prose narratives.

This pipeline generates a structural outline without detailed content:
- Phase 1: Style determination
- Phase 2: Outline generation (title, premise, chapters, scenes, characters, locations)
- Phase 3: Project assembly

The outline includes:
- Story title and expanded premise
- Chapter structure with titles and summaries
- Scene sketches with titles, summaries, and character assignments
- Character sketches (name, role, brief description)
- Location list (names only)

The outline does NOT include:
- Detailed character attributes (desire, need, flaw, secret, traits)
- Beats for scenes
- Detailed world facts
- Enrichment content
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import cast

from fabulae import __version__
from fabulae.features.create.progress import CreateProgress, maybe_stage
from fabulae.features.create.prompts import (
    build_outline_only_prompt,
    build_style_prompt,
)
from fabulae.features.create.schemas import (
    CreateOptions,
    OutlineOutput,
    SceneSketchOutput,
    StyleOutput,
)
from fabulae.features.create.service import (
    FORMAT_COUNT_RANGES,
    ErrorMode,
    _coerce_style,
    _extract_text_from_style,
    _resolve_language,
    _validate_style_output,
    _write_artifact,
    _write_characters,
    _write_config,
    _write_plot,
    _write_style,
    _write_world,
    run_stage,
)
from fabulae.features.create.shapes.loader import load_shape, load_shape_from_file
from fabulae.features.create.shapes.selector import select_shape_for_idea
from fabulae.llm import LLMConfig
from fabulae.llm.language_guard import LanguageGuardConfig
from fabulae.models import (
    Chapter,
    Character,
    GenerationMetadata,
    LiteratureFormat,
    Plot,
    Project,
    ProjectConfig,
    ProjectDefaults,
    Scene,
    StoryShape,
    World,
    WorldFact,
)


def _extract_text_from_outline(output: OutlineOutput) -> str:
    """Extract text content from outline for language validation."""
    parts: list[str] = [output.title or "", output.premise]

    for chapter in output.chapters:
        parts.append(chapter.title or "")
        parts.append(chapter.summary or "")

    for scene in output.scenes:
        parts.append(scene.title or "")
        parts.append(scene.summary or "")

    for character in output.characters:
        parts.append(character.name)
        parts.append(character.role or "")
        parts.append(character.description or "")

    for location in output.locations:
        parts.append(location.name)

    return "\n".join(part for part in parts if part)


def _validate_outline_output(output: OutlineOutput) -> str | None:
    """Validate outline output for structural consistency."""
    # Check for duplicate IDs
    all_ids: set[str] = set()

    for chapter in output.chapters:
        if chapter.id in all_ids:
            return f"Duplicate chapter ID: {chapter.id!r}"
        all_ids.add(chapter.id)

    for scene in output.scenes:
        if scene.id in all_ids:
            return f"Duplicate scene ID: {scene.id!r}"
        all_ids.add(scene.id)

    for character in output.characters:
        if character.id in all_ids:
            return f"Duplicate character ID: {character.id!r}"
        all_ids.add(character.id)

    for location in output.locations:
        if location.id in all_ids:
            return f"Duplicate location ID: {location.id!r}"
        all_ids.add(location.id)

    # Validate chapter scene references
    scene_ids = {scene.id for scene in output.scenes}
    referenced_scenes: set[str] = set()

    for chapter in output.chapters:
        for scene_id in chapter.scene_ids:
            if scene_id not in scene_ids:
                return f"Chapter {chapter.id!r} references unknown scene: {scene_id!r}"
            if scene_id in referenced_scenes:
                return f"Scene {scene_id!r} is referenced by multiple chapters"
            referenced_scenes.add(scene_id)

    # Check for orphan scenes
    orphan_scenes = scene_ids - referenced_scenes
    if orphan_scenes and output.chapters:
        return f"Scenes not assigned to any chapter: {sorted(orphan_scenes)!r}"

    # Validate scene character references
    character_ids = {character.id for character in output.characters}
    for scene in output.scenes:
        for char_id in scene.character_ids:
            if char_id not in character_ids:
                return f"Scene {scene.id!r} references unknown character: {char_id!r}"

    return None


async def generate_outline_only(
    idea: str,
    format: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress,
    artifacts_dir: Path | None = None,
) -> Project:
    """Generate an outline-only project for prose narratives.

    This pipeline creates a structural outline without detailed content:
    - Style (tone, voice, POV, tense)
    - Expanded premise
    - Chapter structure with titles and summaries
    - Scene placeholders with titles and brief summaries
    - Character sketches (name, role, one-line description)
    - Location list (names only)

    Args:
        idea: The core idea or premise for the narrative
        format: The literature format ("novel", "novella", or "short-story")
        options: Configuration options for the generation process
        llm_config: Configuration for LLM interactions
        progress: Progress reporter for user feedback
        artifacts_dir: Optional directory for saving intermediate artifacts

    Returns:
        A Project object with outline-level content (no detailed beats or character attributes)

    Raises:
        ValueError: If format is not a valid prose format
    """
    # Validate format
    if format not in ("novel", "novella", "short-story"):
        raise ValueError(f"Invalid prose format: {format}. Expected novel, novella, or short-story.")

    format_name = cast(LiteratureFormat, format)

    # =========================================================================
    # Phase 1: Style Determination
    # =========================================================================

    # Resolve language from CLI override or detect from idea
    language_config = LanguageGuardConfig()
    expected_language = _resolve_language(idea, options.idea_language, language_config)

    with maybe_stage(progress, "Determining narrative style..."):
        style_result = await run_stage(
            result_type=StyleOutput,
            system_prompt=build_style_prompt(format_name),
            user_prompt=f"Idea: {idea.strip()}",
            config=llm_config,
            expected_language=expected_language,
            extract_text=_extract_text_from_style,
            validate=_validate_style_output(expected_language),
            error_mode=ErrorMode.WARN,
        )
        style_output = style_result.output

        # Default to English if no language was detected or overridden
        if expected_language is None:
            expected_language = "en"

        # Ensure style reflects the enforced language (CLI override takes precedence)
        if expected_language and style_output.language != expected_language:
            style_output = style_output.model_copy(update={"language": expected_language})

    progress.success("Style determined")

    # Write style artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "01-style.yml", style_output.model_dump(exclude_none=True, by_alias=True))

    # =========================================================================
    # Shape Selection (auto-select if not provided)
    # =========================================================================

    shape: StoryShape | None = None
    if options.shape_file:
        shape = load_shape_from_file(options.shape_file)
    elif options.shape_id:
        shape = load_shape(options.shape_id)
    elif not options.no_shape:
        # Auto-select shape based on idea
        with maybe_stage(progress, "Selecting story shape..."):
            shape = await select_shape_for_idea(idea, llm_config)
        if progress and shape:
            progress.info(f"Selected shape: {shape.id}")

        # Write shape selection artifact
        if artifacts_dir and shape:
            _write_artifact(
                artifacts_dir,
                "01a-shape.yml",
                {
                    "shape_id": shape.id,
                    "auto_selected": True,
                },
            )

    # =========================================================================
    # Phase 2: Outline Generation
    # =========================================================================

    # Get count ranges for format
    count_ranges = FORMAT_COUNT_RANGES.get(format_name, {})
    outline_ranges = {
        "chapters": count_ranges.get("chapters", (6, 12)),
        "scenes": count_ranges.get("scenes", (18, 36)),
        "characters": count_ranges.get("characters", (4, 8)),
        "locations": count_ranges.get("world_facts", (4, 8)),  # Reuse world_facts count for locations
    }

    with maybe_stage(progress, "Creating outline..."):
        outline_result = await run_stage(
            result_type=OutlineOutput,
            system_prompt=build_outline_only_prompt(format_name, style_output, outline_ranges),
            user_prompt=f"Create an outline for this idea: {idea.strip()}",
            config=llm_config,
            expected_language=expected_language,
            extract_text=_extract_text_from_outline,
            validate=_validate_outline_output,
            error_mode=ErrorMode.WARN,
        )
        outline = outline_result.output

    progress.success(
        f"Outline created: {len(outline.chapters)} chapters, "
        f"{len(outline.scenes)} scenes, {len(outline.characters)} characters"
    )

    # Write outline artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "02-outline.yml", outline.model_dump(exclude_none=True))

    # =========================================================================
    # Phase 3: Project Assembly
    # =========================================================================

    # Determine the effective shape ID for metadata (user-provided or auto-selected)
    auto_selected_shape_id: str | None = None
    if not options.shape_id and not options.shape_file and shape:
        # Shape was auto-selected (not explicitly provided)
        auto_selected_shape_id = shape.id

    with maybe_stage(progress, "Assembling project..."):
        project = _convert_outline_to_project(
            outline=outline,
            style_output=style_output,
            format_name=format_name,
            idea=idea,
            llm_config=llm_config,
            options=options,
            auto_selected_shape_id=auto_selected_shape_id,
        )

    progress.success("Project assembled")

    # Write project files if artifacts_dir provided
    if artifacts_dir:
        _write_config(project.config, artifacts_dir)
        _write_style(project.style, project.config, artifacts_dir)
        _write_characters(project.characters, project.config, artifacts_dir)
        if project.world:
            _write_world(project.world, project.config, artifacts_dir)
        _write_plot(project.plot, project.config, artifacts_dir)

    return project


def _convert_outline_to_project(
    outline: OutlineOutput,
    style_output: StyleOutput,
    format_name: LiteratureFormat,
    idea: str,
    llm_config: LLMConfig,
    options: CreateOptions,
    auto_selected_shape_id: str | None = None,
) -> Project:
    """Convert outline output to Project structure with placeholder content.

    Characters have minimal info (name, role) - detailed attributes left empty.
    Scenes have no beats - to be filled in with --full mode later.
    World facts are minimal (just location names).

    Args:
        outline: The outline output from the LLM
        style_output: The style output from the LLM
        format_name: The literature format
        idea: The original idea
        llm_config: The LLM config
        options: The create options
        auto_selected_shape_id: The ID of the auto-selected shape, if any
    """
    # Convert style
    style = _coerce_style(style_output)

    # Convert characters (minimal info only)
    characters = [
        Character(
            id=char.id,
            name=char.name,
            role=char.role,
            # Detailed attributes left as None/empty - to be filled with --full
            desire=None,
            need=None,
            flaw=None,
            secret=None,
            traits=[],
        )
        for char in outline.characters
    ]

    # Convert locations to world facts (minimal info only)
    world_facts = [
        WorldFact(
            id=loc.id,
            type="location",
            name=loc.name,
            facts=[],  # Empty - to be filled with --full
        )
        for loc in outline.locations
    ]

    # Build World object if we have facts
    world = World(facts=world_facts) if world_facts else None

    # Convert scenes (no beats)
    # Note: Scene model doesn't have 'title' field, but SceneSketchOutput does.
    # We include the title in the summary if provided.
    def _build_scene_summary(sketch: SceneSketchOutput) -> str | None:
        if sketch.title and sketch.summary:
            return f"{sketch.title}: {sketch.summary}"
        return sketch.summary or sketch.title

    scenes = [
        Scene(
            id=scene.id,
            summary=_build_scene_summary(scene),
            characters=scene.character_ids,
            beats=[],  # Empty - to be filled with --full
        )
        for scene in outline.scenes
    ]

    # Convert chapters
    chapters = [
        Chapter(
            id=chapter.id,
            title=chapter.title,
            summary=chapter.summary,
            scene_ids=chapter.scene_ids if chapter.scene_ids else None,
        )
        for chapter in outline.chapters
    ]

    # Determine scene ordering if no chapters
    scene_ids_list: list[str] | None = None
    if not chapters:
        scene_ids_list = [scene.id for scene in scenes]

    # Build Plot
    plot = Plot(
        format=format_name,
        title=outline.title,
        premise=outline.premise,
        themes=[],
        chapters=chapters,
        scenes=scenes,
        scene_ids=scene_ids_list,
    )

    # Determine the effective shape ID for metadata (explicit takes precedence over auto-selected)
    effective_shape_id: str | None = None
    if options.shape_id:
        effective_shape_id = options.shape_id
    elif auto_selected_shape_id:
        effective_shape_id = auto_selected_shape_id

    # Build metadata
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea=idea,
        model=llm_config.model,
        temperature=llm_config.temperature,
        shape=effective_shape_id,
        shape_file=str(options.shape_file) if options.shape_file else None,
        no_shape=options.no_shape if options.no_shape else None,
        variation=options.variation,
        seed=llm_config.seed,
        enrichment_enabled=False,  # Enrichment disabled in outline mode
        format=format_name,
        language=style_output.language,
    )

    # Build config
    config = ProjectConfig(
        version=__version__,
        title=outline.title,
        defaults=ProjectDefaults(language=style_output.language) if style_output.language else None,
        metadata=metadata,
    )

    return Project(
        config=config,
        plot=plot,
        characters=characters,
        world=world,
        style=style,
    )


__all__ = ["generate_outline_only"]
