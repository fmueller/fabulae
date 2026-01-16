"""Sequential generation pipeline for prose narratives.

This pipeline generates content one unit at a time with minimal context,
reducing LLM divergence and errors compared to batch generation.

The approach:
1. Generate structure deterministically using RNG (no LLM)
2. Generate style and premise (single LLM calls)
3. Generate characters one at a time
4. Generate locations one at a time
5. Generate chapter summaries one at a time
6. Generate scenes one at a time with only relevant context
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import cast

from fabulae import __version__
from fabulae.features.create.context import (
    ProjectState,
    build_chapter_context,
    build_character_context,
    build_location_context,
    build_scene_context,
)
from fabulae.features.create.graph import PlotGraph
from fabulae.features.create.progress import CreateProgress
from fabulae.features.create.prompts_v2 import (
    build_chapter_prompt_v2,
    build_character_prompt_v2,
    build_location_prompt_v2,
    build_premise_prompt_v2,
    build_scene_prompt_v2,
    build_style_prompt_v2,
)
from fabulae.features.create.schemas import (
    CharacterOutput,
    CreateOptions,
    PremiseOutput,
    SceneOutput,
    StyleOutput,
    WorldFactOutput,
)
from fabulae.features.create.service import (
    ErrorMode,
    _coerce_style,
    _extract_text_from_character,
    _extract_text_from_scene,
    _extract_text_from_style,
    _extract_text_from_world_fact,
    _normalize_character_output,
    _normalize_scene_output,
    _normalize_world_fact_output,
    _resolve_language,
    _write_artifact,
    _write_characters,
    _write_config,
    _write_plot,
    _write_style,
    _write_world,
    run_stage,
)
from fabulae.features.create.shapes.loader import load_shape, load_shape_from_file
from fabulae.features.create.shutdown import graceful_shutdown
from fabulae.features.create.state import GenerationState
from fabulae.features.create.structure import generate_plot_graph
from fabulae.features.create.validation import is_title_acceptable
from fabulae.llm import LLMConfig
from fabulae.llm.language_guard import LanguageGuardConfig
from fabulae.models import (
    Beat,
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


class ChapterSummaryOutput:
    """Simple output for chapter summary generation."""

    def __init__(self, id: str, title: str | None, summary: str | None):
        self.id = id
        self.title = title
        self.summary = summary


async def generate_prose_sequential(
    idea: str,
    format: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress,
    artifacts_dir: Path | None = None,
) -> Project:
    """Generate a complete prose narrative using sequential per-unit approach.

    This pipeline generates content one unit at a time with minimal context:
    1. Structure generation (deterministic, no LLM)
    2. Style generation (single call)
    3. Premise expansion (single call)
    4. Characters (one call per character)
    5. Locations (one call per location)
    6. Chapter summaries (one call per chapter)
    7. Scenes (one call per scene, with filtered context)

    Args:
        idea: The core idea or premise for the narrative
        format: The literature format ("novel", "novella", or "short-story")
        options: Configuration options including variation, seed, etc.
        llm_config: Configuration for LLM interactions
        progress: Progress reporter for user feedback
        artifacts_dir: Optional directory for saving intermediate artifacts

    Returns:
        A complete Project object with all narrative elements
    """
    # Validate format
    if format not in ("novel", "novella", "short-story"):
        raise ValueError(f"Invalid prose format: {format}. Expected novel, novella, or short-story.")

    format_name = cast(LiteratureFormat, format)

    # Load story shape if provided
    shape: StoryShape | None = None
    if options.shape_file:
        shape = load_shape_from_file(options.shape_file)
    elif options.shape_id:
        shape = load_shape(options.shape_id)

    # =========================================================================
    # Phase 1: Structure Generation (No LLM)
    # =========================================================================

    with progress.stage("Planning story structure..."):
        graph = generate_plot_graph(format_name, shape, options.variation, options.seed)

    progress.success(
        f"Structure planned: {len(graph.chapters)} chapters, {len(graph.scenes)} scenes, {graph.total_beats()} beats"
    )

    # Write structure artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "01-structure.yml",
            {
                "format": format_name,
                "chapters": len(graph.chapters),
                "scenes": len(graph.scenes),
                "total_beats": graph.total_beats(),
                "characters": len(graph.characters),
                "locations": len(graph.locations),
                "seed": graph.seed,
                "summary": graph.to_summary(),
            },
        )

    # Initialize generation state for graceful shutdown
    gen_state = GenerationState(idea=idea, format_name=format_name)
    output_dir = artifacts_dir or Path.cwd()

    with graceful_shutdown(gen_state, output_dir, progress):
        return await _generate_prose_sequential_inner(
            idea=idea,
            format_name=format_name,
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=artifacts_dir,
            graph=graph,
            gen_state=gen_state,
        )


async def _generate_prose_sequential_inner(
    idea: str,
    format_name: LiteratureFormat,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress,
    artifacts_dir: Path | None,
    graph: PlotGraph,
    gen_state: GenerationState,
) -> Project:
    """Inner generation logic wrapped by graceful shutdown handler."""
    # =========================================================================
    # Phase 2: Style Generation
    # =========================================================================

    # Resolve language from CLI override or detect from idea
    language_config = LanguageGuardConfig()
    expected_language = _resolve_language(idea, options.idea_language, language_config)

    with progress.stage("Determining narrative style..."):
        style_result = await run_stage(
            result_type=StyleOutput,
            system_prompt=build_style_prompt_v2(format_name, idea),
            user_prompt=f"Generate style for: {idea.strip()}",
            config=llm_config,
            expected_language=expected_language,
            extract_text=_extract_text_from_style,
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

    # Update generation state
    gen_state.style = style_output
    gen_state.current_stage = "style_complete"

    # Write style artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "02-style.yml", style_output.model_dump(exclude_none=True, by_alias=True))

    # =========================================================================
    # Phase 3: Premise Expansion
    # =========================================================================

    with progress.stage("Expanding premise..."):
        premise_result = await run_stage(
            result_type=PremiseOutput,
            system_prompt=build_premise_prompt_v2(format_name, idea, style_output),
            user_prompt=f"Expand this idea: {idea.strip()}",
            config=llm_config,
            expected_language=expected_language,
            extract_text=lambda p: p.premise,
            error_mode=ErrorMode.STRICT,
        )
        premise = premise_result.output.premise

    progress.success("Premise expanded")

    # Update generation state
    gen_state.premise = premise
    gen_state.current_stage = "premise_complete"

    # Write premise artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "03-premise.yml", {"premise": premise})

    # Initialize project state for accumulating generated content
    state = ProjectState()

    # =========================================================================
    # Phase 4: Character Generation (One at a time)
    # =========================================================================

    with progress.phase("Creating characters...") as phase:
        for i, char_slot in enumerate(graph.characters):
            phase.update(f"Creating character {i + 1}/{len(graph.characters)}...")
            context = build_character_context(char_slot, premise, style_output, state)

            def validate_char(output: CharacterOutput, slot_id: str = char_slot.id) -> str | None:
                if output.id != slot_id:
                    return f"Character ID {output.id!r} does not match expected {slot_id!r}."
                return None

            char_result = await run_stage(
                result_type=CharacterOutput,
                system_prompt=build_character_prompt_v2(context),
                user_prompt=f"Create character for role: {char_slot.role}",
                config=llm_config,
                expected_language=expected_language,
                extract_text=_extract_text_from_character,
                normalize=_normalize_character_output,
                validate=validate_char,
                error_mode=ErrorMode.WARN,
            )

            # Convert to domain model and add to state
            char_data = char_result.output.model_dump(exclude_none=True)
            character = Character.model_validate(char_data)
            state.characters.append(character)

            # Update generation state
            gen_state.characters.append(character)
            gen_state.current_stage = f"generating_characters ({i + 1}/{len(graph.characters)})"

    progress.success(f"Created {len(state.characters)} characters")
    gen_state.current_stage = "characters_complete"

    # Write characters artifact
    if artifacts_dir and state.characters:
        _write_artifact(
            artifacts_dir,
            "04-characters.yml",
            {"characters": [c.model_dump(exclude_none=True) for c in state.characters]},
        )

    # =========================================================================
    # Phase 5: Location Generation (One at a time)
    # =========================================================================

    with progress.phase("Creating locations...") as phase:
        for i, loc_slot in enumerate(graph.locations):
            phase.update(f"Creating location {i + 1}/{len(graph.locations)}...")
            loc_context = build_location_context(loc_slot, premise, style_output, state)

            def validate_loc(output: WorldFactOutput, slot_id: str = loc_slot.id) -> str | None:
                if output.id != slot_id:
                    return f"Location ID {output.id!r} does not match expected {slot_id!r}."
                if output.type != "location":
                    return f"World fact type {output.type!r} should be 'location'."
                return None

            loc_result = await run_stage(
                result_type=WorldFactOutput,
                system_prompt=build_location_prompt_v2(loc_context),
                user_prompt="Create location for the story",
                config=llm_config,
                expected_language=expected_language,
                extract_text=_extract_text_from_world_fact,
                normalize=_normalize_world_fact_output,
                validate=validate_loc,
                error_mode=ErrorMode.WARN,
            )

            # Convert to domain model and add to state
            loc_data = loc_result.output.model_dump(exclude_none=True)
            location = WorldFact.model_validate(loc_data)
            state.locations.append(location)

            # Update generation state
            gen_state.locations.append(location)
            gen_state.current_stage = f"generating_locations ({i + 1}/{len(graph.locations)})"

    progress.success(f"Created {len(state.locations)} locations")
    gen_state.current_stage = "locations_complete"

    # Write locations artifact
    if artifacts_dir and state.locations:
        _write_artifact(
            artifacts_dir,
            "05-locations.yml",
            {"locations": [loc.model_dump(exclude_none=True) for loc in state.locations]},
        )

    # =========================================================================
    # Phase 6: Chapter Summary Generation (One at a time)
    # =========================================================================

    if graph.chapters:
        # Define ChapterOutput class once outside the loop
        from pydantic import BaseModel, Field

        class ChapterOutput(BaseModel):
            id: str = Field(description="Chapter ID")
            title: str | None = Field(default=None, description="Chapter title")
            summary: str | None = Field(default=None, description="Chapter summary")

        with progress.phase("Planning chapters...") as phase:
            for i, chapter_slot in enumerate(graph.chapters):
                phase.update(f"Planning chapter {i + 1}/{len(graph.chapters)}...")

                # Get previous titles for validation
                previous_titles = [c.title for c in state.chapters if c.title]

                # Try to generate a chapter with acceptable title (retry once if needed)
                max_retries = 1
                rejection_feedback: str | None = None
                final_chapter_result = None

                for attempt in range(max_retries + 1):
                    chapter_context = build_chapter_context(chapter_slot, graph, premise, style_output, state)

                    # Build prompt, adding rejection feedback on retry
                    system_prompt = build_chapter_prompt_v2(chapter_context)
                    if rejection_feedback:
                        system_prompt += f"\n\nPREVIOUS ATTEMPT REJECTED: {rejection_feedback}"

                    def validate_chapter(output: ChapterOutput, slot_id: str = chapter_slot.id) -> str | None:
                        if output.id != slot_id:
                            return f"Chapter ID {output.id!r} does not match expected {slot_id!r}."
                        return None

                    chapter_result = await run_stage(
                        result_type=ChapterOutput,
                        system_prompt=system_prompt,
                        user_prompt=f"Create chapter {i + 1} summary",
                        config=llm_config,
                        expected_language=expected_language,
                        extract_text=lambda c: f"{c.title or ''}\n{c.summary or ''}",
                        validate=validate_chapter,
                        error_mode=ErrorMode.WARN,
                    )
                    final_chapter_result = chapter_result

                    # Validate title diversity
                    generated_title = chapter_result.output.title or ""
                    is_ok, reason = is_title_acceptable(generated_title, previous_titles)

                    if is_ok:
                        break  # Title is acceptable, proceed

                    if attempt < max_retries:
                        # Prepare rejection feedback for retry
                        rejection_feedback = (
                            f"Your title '{generated_title}' was rejected: {reason}. "
                            "Generate a COMPLETELY DIFFERENT title following the Required Structure."
                        )
                        continue

                    # Final attempt still failed - log warning but accept
                    progress.warn(f"Chapter {chapter_slot.id} title diversity issue: {reason}")

                # Convert to domain model and add to state
                assert final_chapter_result is not None  # Guaranteed by loop structure
                chapter = Chapter(
                    id=final_chapter_result.output.id,
                    title=final_chapter_result.output.title,
                    summary=final_chapter_result.output.summary,
                    scene_ids=chapter_slot.scene_ids,
                )
                state.chapters.append(chapter)

                # Update generation state
                gen_state.chapters.append(chapter.model_dump(exclude_none=True))
                gen_state.current_stage = f"generating_chapters ({i + 1}/{len(graph.chapters)})"

        progress.success(f"Planned {len(state.chapters)} chapters")
        gen_state.current_stage = "chapters_complete"

        # Write chapters artifact
        if artifacts_dir and state.chapters:
            _write_artifact(
                artifacts_dir,
                "06-chapters.yml",
                {"chapters": [c.model_dump(exclude_none=True) for c in state.chapters]},
            )

    # =========================================================================
    # Phase 7: Scene Generation (One at a time with minimal context)
    # =========================================================================

    # Build sets for validation
    available_characters = {c.id for c in state.characters}
    available_world_facts = {loc.id for loc in state.locations} | {wf.id for wf in state.world_facts}

    def make_scene_validator(
        expected_scene_id: str,
        expected_beat_count: int,
    ) -> Callable[[SceneOutput], str | None]:
        """Create a scene validator with captured values."""

        def validate_scene(output: SceneOutput) -> str | None:
            if output.id != expected_scene_id:
                return f"Scene ID {output.id!r} does not match expected {expected_scene_id!r}."
            if len(output.beats) != expected_beat_count:
                return f"Scene has {len(output.beats)} beats but expected {expected_beat_count}."
            # Validate character references
            for char_id in output.characters:
                if char_id not in available_characters:
                    return f"Unknown character ID: {char_id!r}"
            # Validate location reference
            if output.location and output.location not in available_world_facts:
                return f"Unknown location ID: {output.location!r}"
            return None

        return validate_scene

    with progress.phase("Writing scenes...") as phase:
        for i, scene_slot in enumerate(graph.scenes):
            phase.update(f"Writing scene {i + 1}/{len(graph.scenes)}...")
            scene_context = build_scene_context(scene_slot, graph, state, options)

            validate_scene = make_scene_validator(
                expected_scene_id=scene_slot.id,
                expected_beat_count=len(scene_slot.beat_slots),
            )

            scene_result = await run_stage(
                result_type=SceneOutput,
                system_prompt=build_scene_prompt_v2(scene_context, style_output),
                user_prompt=f"Generate scene {scene_slot.id}",
                config=llm_config,
                expected_language=expected_language,
                extract_text=_extract_text_from_scene,
                normalize=_normalize_scene_output,
                validate=validate_scene,
                error_mode=ErrorMode.WARN,
            )

            # Convert to domain model
            scene_data = scene_result.output.model_dump(exclude_none=True)

            # Build beats
            beats: list[Beat] = []
            for beat_output in scene_result.output.beats:
                beat = Beat(
                    id=beat_output.id,
                    kind=beat_output.kind,
                    summary=beat_output.summary,
                    goal=beat_output.goal,
                    conflict=beat_output.conflict,
                    outcome=beat_output.outcome,
                    pace=beat_output.pace,
                )
                beats.append(beat)

            # Build scene
            scene = Scene(
                id=scene_data["id"],
                location=scene_data.get("location"),
                time=scene_data.get("time"),
                characters=scene_data.get("characters", []),
                world_fact_ids=scene_data.get("world_fact_ids", []),
                summary=scene_data.get("summary"),
                goal=scene_data.get("goal"),
                conflict=scene_data.get("conflict"),
                outcome=scene_data.get("outcome"),
                beats=beats,
            )
            state.scenes.append(scene)

            # Update generation state
            gen_state.scenes.append(scene)
            gen_state.current_stage = f"generating_scenes ({i + 1}/{len(graph.scenes)})"

    progress.success(f"Written {len(state.scenes)} scenes")
    gen_state.current_stage = "scenes_complete"

    # Write scenes artifact
    if artifacts_dir and state.scenes:
        _write_artifact(
            artifacts_dir,
            "07-scenes.yml",
            {"scenes": [s.model_dump(exclude_none=True) for s in state.scenes]},
        )

    # =========================================================================
    # Phase 8: Project Assembly
    # =========================================================================

    gen_state.current_stage = "assembling_project"

    with progress.stage("Assembling project..."):
        project = _assemble_project(
            idea=idea,
            format_name=format_name,
            style_output=style_output,
            premise=premise,
            state=state,
            graph=graph,
            llm_config=llm_config,
            variation=options.variation,
            enrich=options.enrich,
        )

    progress.success("Project assembled")

    # Write final project files
    if artifacts_dir:
        _write_config(project.config, artifacts_dir)
        _write_style(project.style, project.config, artifacts_dir)
        _write_characters(project.characters, project.config, artifacts_dir)
        _write_world(project.world, project.config, artifacts_dir)
        _write_plot(project.plot, project.config, artifacts_dir)

    return project


def _assemble_project(
    idea: str,
    format_name: LiteratureFormat,
    style_output: StyleOutput,
    premise: str,
    state: ProjectState,
    graph: PlotGraph,
    llm_config: LLMConfig,
    variation: float,
    enrich: bool,
) -> Project:
    """Assemble the final Project from generated components."""
    # Build style
    style = _coerce_style(style_output)

    # Build world
    all_facts = list(state.locations) + list(state.world_facts)
    world = World(facts=all_facts) if all_facts else None

    # Build plot
    plot = Plot(
        format=format_name,
        title=None,  # Could be generated separately
        premise=premise,
        themes=[],  # Could be extracted from premise
        chapters=state.chapters if state.chapters else [],
        scenes=state.scenes,
    )

    # Build config with metadata
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea=idea,
        model=llm_config.model,
        temperature=llm_config.temperature,
        variation=variation,
        seed=graph.seed,
        enrichment_enabled=enrich,
        format=format_name,
    )

    config = ProjectConfig(
        defaults=ProjectDefaults(),
        metadata=metadata,
    )

    return Project(
        config=config,
        plot=plot,
        characters=state.characters,
        world=world,
        style=style,
    )


__all__ = ["generate_prose_sequential"]
