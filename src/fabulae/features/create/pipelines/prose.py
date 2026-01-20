"""Prose narrative pipeline for novel, novella, and short-story formats.

This module implements the generation pipeline for prose-based narratives,
including full story structure with chapters, scenes, beats, and detailed content.

The pipeline follows a plot-first approach:
- Phase 1: Setup (style, language, shape loading)
- Phase 2: Structure (outline structure, ID allocation)
- Phase 3: Content (outline content, characters, world)
- Phase 3.5: Enrichment (optional - secondary characters, subplots, foreshadowing)
- Phase 4: Patterns & Beats (plot patterns, narrative patterns, beat templates)
- Phase 5: Scene Expansion (full scene generation)
- Phase 6: Assembly (project creation, artifact writing)
"""

from __future__ import annotations

import random
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast

from fabulae import __version__
from fabulae.features.create.enrichment import (
    generate_enrichment,
    merge_enrichment_characters,
    merge_enrichment_plot,
    merge_enrichment_world,
)
from fabulae.features.create.ids import allocate_prose_ids
from fabulae.features.create.pipelines.plot_first import (
    BeatAssignment,
    assign_required_beats_to_scenes,
    build_beat_templates_with_variation,
    generate_characters_from_slots,
    generate_outline_content,
    generate_outline_structure,
    generate_world_from_slots,
)
from fabulae.features.create.progress import CreateProgress, maybe_stage
from fabulae.features.create.prompts import (
    build_character_plan_prompt,
    build_character_prompt,
    build_premise_expansion_prompt,
    build_scene_prompt,
    build_style_prompt,
    build_world_fact_prompt,
    build_world_plan_prompt,
)
from fabulae.features.create.schemas import (
    ChapterContentOutput,
    CharacterOutput,
    CharacterPlanOutput,
    CreateOptions,
    OutlineContentOutput,
    OutlineSceneOutput,
    PremiseOutput,
    SceneBeatTemplate,
    SceneContentOutput,
    SceneOutput,
    StyleOutput,
    WorldFactOutput,
    WorldPlanOutput,
)
from fabulae.features.create.service import (
    FORMAT_BEATS_PER_SCENE,
    ErrorMode,
    SceneContext,
    _build_scene_prompt_context,
    _coerce_style,
    _count_range,
    _extract_text_from_character,
    _extract_text_from_character_plan,
    _extract_text_from_scene,
    _extract_text_from_style,
    _extract_text_from_world_fact,
    _extract_text_from_world_plan,
    _normalize_character_output,
    _normalize_character_plan_output,
    _normalize_scene_output,
    _normalize_world_fact_output,
    _normalize_world_plan_output,
    _resolve_language,
    _style_hint,
    _summarize_characters,
    _summarize_outline_summaries,
    _summarize_world_facts,
    _validate_character_output,
    _validate_character_plan_output,
    _validate_scene_output,
    _validate_scene_template,
    _validate_style_output,
    _validate_world_fact_output,
    _validate_world_plan_output,
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
from fabulae.features.create.shutdown import graceful_shutdown
from fabulae.features.create.state import GenerationState
from fabulae.features.create.variation import (
    VariationEngine,
    create_variation_config_from_level,
)
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
    SemanticValue,
    StoryShape,
    Style,
    World,
    WorldFact,
)

if TYPE_CHECKING:
    pass


async def generate_prose(
    idea: str,
    format: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress | None = None,
    artifacts_dir: Path | None = None,
) -> Project:
    """Generate a complete prose narrative project (novel, novella, or short-story).

    This is the main entry point for prose generation, orchestrating the multi-pass
    pipeline to create a structured narrative with chapters, scenes, and beats.

    Args:
        idea: The core idea or premise for the narrative
        format: The literature format ("novel", "novella", or "short-story")
        options: Configuration options for the generation process
        llm_config: Configuration for LLM interactions
        artifacts_dir: Optional directory for saving intermediate artifacts

    Returns:
        A complete Project object with all narrative elements

    Raises:
        CreateProjectError: If generation fails at any stage
        ValueError: If format is not a valid prose format
    """
    # Validate format
    if format not in ("novel", "novella", "short-story"):
        raise ValueError(f"Invalid prose format: {format}. Expected novel, novella, or short-story.")

    format_name = cast(LiteratureFormat, format)

    # =========================================================================
    # Phase 1: Setup
    # =========================================================================

    # Resolve language from CLI override or detect from idea
    language_config = LanguageGuardConfig()
    expected_language = _resolve_language(idea, options.idea_language, language_config)

    # Generate style
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

        style_hint_str = _style_hint(style_output)
        style = _coerce_style(style_output)

    if progress:
        progress.success("Style determined")

    # Write style artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "01-style.yml", style_output.model_dump(exclude_none=True, by_alias=True))

    # Initialize generation state for graceful shutdown
    gen_state = GenerationState(idea=idea, format_name=format_name)
    gen_state.style = style_output
    gen_state.current_stage = "style_complete"
    output_dir = artifacts_dir or Path.cwd()

    with graceful_shutdown(gen_state, output_dir, progress):
        return await _generate_prose_inner(
            idea=idea,
            format_name=format_name,
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=artifacts_dir,
            style_output=style_output,
            style_hint_str=style_hint_str,
            style=style,
            expected_language=expected_language,
            gen_state=gen_state,
        )


async def _generate_prose_inner(
    idea: str,
    format_name: LiteratureFormat,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress | None,
    artifacts_dir: Path | None,
    style_output: StyleOutput,
    style_hint_str: str,
    style: Style | None,
    expected_language: str,
    gen_state: GenerationState,
) -> Project:
    """Inner generation logic wrapped by graceful shutdown handler."""
    rng = random.Random(options.seed)

    # Generate premise expansion
    with maybe_stage(progress, "Expanding premise..."):
        premise_result = await run_stage(
            result_type=PremiseOutput,
            system_prompt=build_premise_expansion_prompt(format_name, expected_language),
            user_prompt=f"Idea: {idea.strip()}\nStyle: {style_hint_str}",
            config=llm_config,
            expected_language=expected_language,
            extract_text=lambda p: p.premise,
            error_mode=ErrorMode.STRICT,
        )
        premise = premise_result.output.premise

    if progress:
        progress.success("Premise expanded")

    # Update generation state
    gen_state.premise = premise
    gen_state.current_stage = "premise_complete"

    # Write premise artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "02-premise.yml", {"premise": premise})

    # Load story shape
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
                "02a-shape.yml",
                {
                    "shape_id": shape.id,
                    "auto_selected": True,
                },
            )

    # =========================================================================
    # Phase 2: Structure
    # =========================================================================

    # Generate outline structure (deterministic, no LLM)
    with maybe_stage(progress, "Planning story structure..."):
        structure = generate_outline_structure(format_name, shape, rng)

        # Extract slot names for ID allocation
        character_slot_names: list[str] | None = None
        location_slot_names: list[str] | None = None

        if shape:
            character_slot_names = [slot.slot for slot in shape.character_slots if not slot.optional]
            # Include optional slots that we'll fill based on variation
            optional_char_slots = [slot.slot for slot in shape.character_slots if slot.optional]
            character_slot_names.extend(optional_char_slots)

            location_slot_names = [slot.slot for slot in shape.setting_slots if not slot.optional]
            # Include optional slots
            optional_loc_slots = [slot.slot for slot in shape.setting_slots if slot.optional]
            location_slot_names.extend(optional_loc_slots)

        # Allocate all IDs upfront
        project_ids = allocate_prose_ids(
            num_chapters=structure.num_chapters,
            scenes_per_chapter=structure.scenes_per_chapter,
            beats_per_scene=structure.beats_per_scene,
            character_slots=character_slot_names,
            location_slots=location_slot_names,
            extra_world_facts=0,  # We'll generate additional world facts separately if needed
        )

    if progress:
        progress.success(f"Structure planned: {structure.num_chapters} chapters, {structure.total_scenes} scenes")

    # Write structure artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "03-structure.yml",
            {
                "num_chapters": structure.num_chapters,
                "scenes_per_chapter": structure.scenes_per_chapter,
                "beats_per_scene": structure.beats_per_scene,
                "total_scenes": structure.total_scenes,
                "total_beats": structure.total_beats,
                "chapter_ids": project_ids.chapters,
                "scene_ids": project_ids.scenes,
            },
        )

    # =========================================================================
    # Phase 3: Content
    # =========================================================================

    # Generate outline content (chapter/scene titles and summaries)
    with maybe_stage(progress, "Generating outline..."):
        outline_content = await generate_outline_content(
            idea=idea,
            format=format_name,
            structure=structure,
            shape=shape,
            llm_config=llm_config,
            chapter_ids=project_ids.chapters,
            scene_ids=project_ids.scenes,
            expected_language=expected_language,
        )

    # Write outline content artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "04-outline-content.yml",
            {
                "chapters": [
                    {"id": ch.id, "title": ch.title, "summary": ch.summary} for ch in outline_content.chapters
                ],
                "scenes": [
                    {
                        "id": sc.id,
                        "chapter_id": sc.chapter_id,
                        "title": sc.title,
                        "summary": sc.summary,
                        "beat_count": sc.beat_count,
                    }
                    for sc in outline_content.scenes
                ],
            },
        )

    if progress:
        progress.success("Outline generated")

    # Generate characters
    characters: list[Character] = []

    with maybe_stage(progress, "Creating characters..."):
        if shape and shape.character_slots:
            # Generate characters from shape slots
            characters = await generate_characters_from_slots(
                idea=idea,
                format=format_name,
                shape=shape,
                character_ids=project_ids.characters,
                slot_mapping=project_ids.character_slot_mapping,
                llm_config=llm_config,
                style=style_output,
            )
        else:
            # Generate characters using existing prompts (plan then expand)
            character_count_range = _count_range(format_name, "characters")

            # Generate character plan
            char_plan_result = await run_stage(
                result_type=CharacterPlanOutput,
                system_prompt=build_character_plan_prompt(format_name, style_hint_str, character_count_range),
                user_prompt=f"Idea: {idea.strip()}",
                config=llm_config,
                expected_language=expected_language,
                extract_text=_extract_text_from_character_plan,
                normalize=_normalize_character_plan_output,
                validate=_validate_character_plan_output,
                error_mode=ErrorMode.WARN,
            )
            char_plan = char_plan_result.output

            # Write character plan artifact
            if artifacts_dir:
                _write_artifact(artifacts_dir, "05-character-plan.yml", char_plan.model_dump(exclude_none=True))

            # Expand each character
            existing_char_ids: set[str] = set()
            for plan_item in char_plan.characters:
                existing_summary = _summarize_characters(characters)

                def validate_char(output: CharacterOutput, expected_id: str = plan_item.id) -> str | None:
                    return _validate_character_output(output, expected_id, existing_char_ids)

                char_prompt = build_character_prompt(format_name, style_hint_str, existing_summary, plan_item.id)
                char_user = f"Idea: {idea.strip()}\nCharacter: {plan_item.name} ({plan_item.role or 'unknown role'})"
                char_result = await run_stage(
                    result_type=CharacterOutput,
                    system_prompt=char_prompt,
                    user_prompt=char_user,
                    config=llm_config,
                    expected_language=expected_language,
                    extract_text=_extract_text_from_character,
                    normalize=_normalize_character_output,
                    validate=validate_char,
                    error_mode=ErrorMode.WARN,
                )

                char_output = char_result.output
                existing_char_ids.add(char_output.id)

                character = Character(
                    id=char_output.id,
                    name=char_output.name,
                    role=char_output.role,
                    desire=char_output.desire,
                    need=char_output.need,
                    flaw=char_output.flaw,
                    secret=char_output.secret,
                    traits=char_output.traits,
                )
                characters.append(character)

    if progress:
        progress.success(f"Created {len(characters)} characters")

    # Update generation state
    gen_state.characters = list(characters)
    gen_state.current_stage = "characters_complete"

    # Write characters artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "06-characters.yml",
            {"characters": [c.model_dump(exclude_none=True) for c in characters]},
        )

    # Generate world
    world_facts: list[WorldFact] = []
    world_setting: str | None = None
    world_time_period: str | None = None
    world_tone: str | None = None
    world_motifs: list[SemanticValue] = []

    with maybe_stage(progress, "Creating world..."):
        if shape and shape.setting_slots:
            # Generate world from shape slots
            world_facts = await generate_world_from_slots(
                idea=idea,
                format=format_name,
                shape=shape,
                location_ids=project_ids.locations,
                slot_mapping=project_ids.location_slot_mapping,
                llm_config=llm_config,
                style=style_output,
                extra_world_fact_ids=project_ids.world_facts,
            )

            # Use shape's tone/themes as world metadata
            if shape.tone:
                world_tone = shape.tone
            if shape.themes:
                world_motifs = list(shape.themes)
        else:
            # Generate world using existing prompts (plan then expand)
            world_fact_count_range = _count_range(format_name, "world_facts")

            # Generate world plan
            world_plan_result = await run_stage(
                result_type=WorldPlanOutput,
                system_prompt=build_world_plan_prompt(format_name, style_hint_str, world_fact_count_range),
                user_prompt=f"Idea: {idea.strip()}",
                config=llm_config,
                expected_language=expected_language,
                extract_text=_extract_text_from_world_plan,
                normalize=_normalize_world_plan_output,
                validate=_validate_world_plan_output,
                error_mode=ErrorMode.WARN,
            )
            world_plan = world_plan_result.output

            # Extract world metadata
            world_setting = world_plan.setting
            world_time_period = world_plan.time_period
            world_tone = world_plan.tone
            world_motifs = list(world_plan.motifs)

            # Write world plan artifact
            if artifacts_dir:
                _write_artifact(artifacts_dir, "07-world-plan.yml", world_plan.model_dump(exclude_none=True))

            # Expand each world fact
            existing_fact_ids: set[str] = set()
            for fact_plan_item in world_plan.facts:
                existing_summary = _summarize_world_facts(world_facts)

                def validate_fact(output: WorldFactOutput, expected_id: str = fact_plan_item.id) -> str | None:
                    return _validate_world_fact_output(output, expected_id, existing_fact_ids)

                fact_prompt = build_world_fact_prompt(format_name, style_hint_str, existing_summary, fact_plan_item.id)
                fact_user = f"Idea: {idea.strip()}\nWorld fact: {fact_plan_item.name} ({fact_plan_item.type})"
                fact_result = await run_stage(
                    result_type=WorldFactOutput,
                    system_prompt=fact_prompt,
                    user_prompt=fact_user,
                    config=llm_config,
                    expected_language=expected_language,
                    extract_text=_extract_text_from_world_fact,
                    normalize=_normalize_world_fact_output,
                    validate=validate_fact,
                    error_mode=ErrorMode.WARN,
                )

                fact_output = fact_result.output
                existing_fact_ids.add(fact_output.id)

                world_fact = WorldFact(
                    id=fact_output.id,
                    type=fact_output.type,
                    name=fact_output.name,
                    facts=fact_output.facts,
                )
                world_facts.append(world_fact)

        # Create World object
        world = World(
            setting=world_setting,
            time_period=world_time_period,
            tone=world_tone,
            motifs=world_motifs,
            facts=world_facts,
        )

    if progress:
        progress.success(f"Created {len(world_facts)} world facts")

    # Update generation state
    gen_state.locations = [f for f in world_facts if f.type == "location"]
    gen_state.current_stage = "world_complete"

    # Write world artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "08-world.yml", world.model_dump(exclude_none=True))

    # =========================================================================
    # Phase 3.5: Enrichment (Optional)
    # =========================================================================

    # Generate enrichment if enabled
    project_variation = None
    if options.enrich:
        with maybe_stage(progress, "Enriching narrative..."):
            # Generate project variation early if we have a shape (for subplot seeds)
            if shape:
                variation_config = create_variation_config_from_level(options.variation)
                variation_engine = VariationEngine(shape, variation_config)
                character_ids_for_variation = [c.id for c in characters]
                project_variation = variation_engine.generate_project_variation(
                    project_ids.scenes, character_ids_for_variation
                )

            # Convert outline to OutputContentOutput format for enrichment
            outline_content_output = OutlineContentOutput(
                chapters=[
                    ChapterContentOutput(
                        id=ch.id,
                        title=ch.title,
                        summary=ch.summary,
                    )
                    for ch in outline_content.chapters
                ],
                scenes=[
                    SceneContentOutput(
                        id=sc.id,
                        chapter_id=sc.chapter_id,
                        title=sc.title,
                        summary=sc.summary,
                        beat_count=sc.beat_count,
                    )
                    for sc in outline_content.scenes
                ],
            )

            # Generate enrichment
            enrichment = await generate_enrichment(
                idea=idea,
                format_name=format_name,
                style=style_output,
                characters=characters,
                world=world,
                outline=outline_content_output,
                config=llm_config,
                variation=project_variation,
                shape=shape,
            )

            # Merge enrichment if we have any new content
            if (
                enrichment.new_characters
                or enrichment.new_locations
                or enrichment.new_world_facts
                or enrichment.subplot_additions
                or enrichment.foreshadowing_elements
            ):
                # Calculate next indices for ID generation
                next_char_idx = len(characters) + 1
                next_loc_idx = sum(1 for f in world.facts if f.type == "location") + 1
                next_fact_idx = sum(1 for f in world.facts if f.type != "location") + 1

                # Merge characters
                characters, char_id_mapping = merge_enrichment_characters(characters, enrichment, next_char_idx)

                # Merge world
                world, world_id_mapping = merge_enrichment_world(world, enrichment, next_loc_idx, next_fact_idx)

                # Combine ID mappings
                id_mapping = {**char_id_mapping, **world_id_mapping}

                # Update outline with subplot/foreshadowing notes
                outline_content_output = merge_enrichment_plot(outline_content_output, enrichment, id_mapping)

                # Convert back to outline_content for scene expansion
                # Update the original outline_content.scenes with enriched summaries
                scene_summary_map = {sc.id: sc.summary for sc in outline_content_output.scenes}
                for outline_sc in outline_content.scenes:
                    if outline_sc.id in scene_summary_map:
                        outline_sc.summary = scene_summary_map[outline_sc.id]

                # Write enrichment artifacts
                if artifacts_dir:
                    _write_artifact(
                        artifacts_dir,
                        "08a-enrichment.yml",
                        enrichment.model_dump(exclude_none=True),
                    )
                    _write_artifact(
                        artifacts_dir,
                        "08b-enriched-characters.yml",
                        {"characters": [c.model_dump(exclude_none=True) for c in characters]},
                    )
                    _write_artifact(
                        artifacts_dir,
                        "08c-enriched-world.yml",
                        world.model_dump(exclude_none=True),
                    )
                    _write_artifact(
                        artifacts_dir,
                        "08d-enriched-outline.yml",
                        outline_content_output.model_dump(exclude_none=True),
                    )

        if progress:
            new_chars = len(enrichment.new_characters) if enrichment.new_characters else 0
            new_locs = len(enrichment.new_locations) if enrichment.new_locations else 0
            subplots = len(enrichment.subplot_additions) if enrichment.subplot_additions else 0
            parts = []
            if new_chars:
                parts.append(f"{new_chars} characters")
            if new_locs:
                parts.append(f"{new_locs} locations")
            if subplots:
                parts.append(f"{subplots} subplots")
            if parts:
                progress.success(f"Enriched narrative ({', '.join(parts)} added)")

    # =========================================================================
    # Phase 4: Patterns & Beats
    # =========================================================================

    with maybe_stage(progress, "Preparing beat templates..."):
        # Assign required beats to scenes (if shape has required beats)
        beat_assignments: list[BeatAssignment] = []
        if shape and shape.required_beats:
            beat_assignments = assign_required_beats_to_scenes(shape, project_ids.scenes, rng)

            # Write beat assignments artifact
            if artifacts_dir:
                _write_artifact(
                    artifacts_dir,
                    "09-beat-assignments.yml",
                    {"assignments": [{"beat_type": a.beat_type, "scene_id": a.scene_id} for a in beat_assignments]},
                )

        # Generate project variation for beat templates (if not already generated during enrichment)
        scene_variations = None
        if shape:
            if project_variation is None:
                # Only generate if we didn't already do it during enrichment
                variation_config = create_variation_config_from_level(options.variation)
                variation_engine = VariationEngine(shape, variation_config)
                character_ids_for_variation = [c.id for c in characters]
                project_variation = variation_engine.generate_project_variation(
                    project_ids.scenes, character_ids_for_variation
                )

            scene_variations = project_variation.scene_variations

            # Write variation artifact
            if artifacts_dir:
                _write_artifact(
                    artifacts_dir,
                    "10-variation.yml",
                    {
                        "subplot_seeds": project_variation.subplot_seeds,
                        "scene_variations": [
                            {
                                "scene_id": sv.scene_id,
                                "position": sv.position,
                                "has_complication": sv.has_complication,
                                "complication_type": sv.complication_type,
                                "has_character_moment": sv.has_character_moment,
                                "character_focus": sv.character_focus,
                                "subplot_seed": sv.subplot_seed,
                                "filler_beats": sv.filler_beats,
                            }
                            for sv in scene_variations
                        ],
                        "selected_variation_points": [
                            {
                                "type": vp.type,
                                "description": vp.description,
                                "position": vp.position,
                                "assigned_scene_id": vp.assigned_scene_id,
                            }
                            for vp in project_variation.selected_variation_points
                        ],
                    },
                )

        # Get selected variation points for beat templates
        selected_variation_points = project_variation.selected_variation_points if project_variation else None

        # Build beat templates
        beat_templates = build_beat_templates_with_variation(
            scene_ids=project_ids.scenes,
            beats_per_scene=structure.beats_per_scene,
            beat_assignments=beat_assignments,
            scene_variations=scene_variations,
            selected_variation_points=selected_variation_points,
            rng=rng,
        )

    if progress:
        progress.success("Beat templates prepared")

    # Write beat templates artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "11-beat-templates.yml",
            {
                scene_id: {
                    "scene_id": template.scene_id,
                    "beat_count": template.beat_count,
                    "beats": [b.model_dump(exclude_none=True) for b in template.beats],
                }
                for scene_id, template in beat_templates.items()
            },
        )

    # =========================================================================
    # Phase 5: Scene Expansion
    # =========================================================================

    # Prepare available entity sets
    available_characters = {c.id for c in characters}
    available_world_facts = {f.id for f in world_facts}
    available_location_ids = {f.id for f in world_facts if f.type == "location"}

    # Prepare summaries
    available_character_summary = _summarize_characters(characters)
    available_location_summary = _summarize_world_facts([f for f in world_facts if f.type == "location"])
    world_summary = _summarize_world_facts(world_facts)

    beats_per_scene_range = FORMAT_BEATS_PER_SCENE[format_name]

    # Convert outline content to scene outlines
    scene_outlines: dict[str, OutlineSceneOutput] = {}
    for sc in outline_content.scenes:
        scene_outlines[sc.id] = OutlineSceneOutput(
            id=sc.id,
            summary=sc.summary,
            goal=None,
            conflict=None,
            outcome=None,
            beat_count=sc.beat_count,
        )

    # Expand each scene
    scenes: list[Scene] = []
    prior_scene_summaries: list[str] = []

    with maybe_stage(progress, "Writing scenes..."):
        for scene_id in project_ids.scenes:
            scene_outline = scene_outlines[scene_id]
            beat_template = beat_templates.get(scene_id)

            # Apply sliding window for small model optimization
            window_size = options.sliding_window_scenes
            if window_size is not None and len(prior_scene_summaries) > window_size:
                windowed_summaries = prior_scene_summaries[-window_size:]
            else:
                windowed_summaries = prior_scene_summaries

            # Build scene context
            scene_context = SceneContext(
                idea=idea,
                format_name=format_name,
                style=style_output,
                style_hint=style_hint_str,
                scene_outline=scene_outline,
                characters=characters,
                world_facts=world_facts,
                beat_template=beat_template,
                available_characters=available_characters,
                available_world_facts=available_world_facts,
                available_location_ids=available_location_ids,
                available_character_summary=available_character_summary,
                available_location_summary=available_location_summary,
                world_summary=world_summary,
                prior_scene_summaries=list(windowed_summaries),
                beats_per_scene=beats_per_scene_range,
            )

            existing_summaries = _summarize_outline_summaries(windowed_summaries)

            # Build validation functions that capture scene context
            def validate_scene(
                output: SceneOutput,
                expected_scene: OutlineSceneOutput = scene_outline,
                avail_chars: set[str] = available_characters,
                avail_facts: set[str] = available_world_facts,
                beat_range: tuple[int, int] = beats_per_scene_range,
            ) -> str | None:
                return _validate_scene_output(output, expected_scene, avail_chars, avail_facts, beat_range)

            def validate_template(
                output: SceneOutput,
                template: SceneBeatTemplate | None = beat_template,
            ) -> str | None:
                return _validate_scene_template(output, template)

            # Build prompt context
            prompt_context = _build_scene_prompt_context(scene_context)

            scene_result = await run_stage(
                result_type=SceneOutput,
                system_prompt=build_scene_prompt(
                    format_name,
                    style_hint_str,
                    available_character_summary,
                    available_location_summary,
                    existing_summaries,
                    scene_id,
                ),
                user_prompt=(
                    f"Idea: {idea.strip()}\n"
                    f"Scene outline: {scene_outline.model_dump(exclude_none=True)}\n"
                    f"Context: {prompt_context}"
                ),
                config=llm_config,
                expected_language=expected_language,
                extract_text=_extract_text_from_scene,
                normalize=_normalize_scene_output,
                validate=validate_scene,
                warn_validate=validate_template,
                error_mode=ErrorMode.WARN,
            )

            scene_output = scene_result.output

            # Convert beats
            scene_beats: list[Beat] = []
            for beat_out in scene_output.beats:
                beat = Beat(
                    id=beat_out.id,
                    kind=beat_out.kind,
                    summary=beat_out.summary,
                    target_words=beat_out.target_words,
                    goal=beat_out.goal,
                    conflict=beat_out.conflict,
                    outcome=beat_out.outcome,
                    pace=beat_out.pace,
                    constraints=beat_out.constraints,
                )
                scene_beats.append(beat)

            # Create Scene
            scene = Scene(
                id=scene_output.id,
                location=scene_output.location,
                time=scene_output.time,
                characters=scene_output.characters,
                world_fact_ids=scene_output.world_fact_ids,
                summary=scene_output.summary,
                goal=scene_output.goal,
                conflict=scene_output.conflict,
                outcome=scene_output.outcome,
                beats=scene_beats,
            )
            scenes.append(scene)

            # Update generation state
            gen_state.scenes.append(scene)
            gen_state.current_stage = f"generating_scenes ({len(scenes)}/{len(project_ids.scenes)})"

            # Track summaries for context
            if scene_output.summary:
                prior_scene_summaries.append(scene_output.summary)

    if progress:
        progress.success(f"Written {len(scenes)} scenes")
    gen_state.current_stage = "scenes_complete"

    # Write scenes artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "12-scenes.yml",
            {"scenes": [s.model_dump(exclude_none=True) for s in scenes]},
        )

    # =========================================================================
    # Phase 6: Assembly
    # =========================================================================

    with maybe_stage(progress, "Assembling project..."):
        # Build chapters (derive scene_ids from outline scenes' chapter_id)
        chapters: list[Chapter] = []
        for ch in outline_content.chapters:
            chapter_scene_ids = [sc.id for sc in outline_content.scenes if sc.chapter_id == ch.id]
            chapter = Chapter(
                id=ch.id,
                title=ch.title,
                summary=ch.summary,
                scene_ids=chapter_scene_ids if chapter_scene_ids else None,
            )
            chapters.append(chapter)

        # Determine scene ordering (scene_ids for chapterless format)
        scene_ids_list: list[str] | None = None
        if not chapters:
            scene_ids_list = [s.id for s in scenes]

        # Build Plot
        plot = Plot(
            format=format_name,
            title=outline_content.chapters[0].title if outline_content.chapters else None,
            premise=premise,
            themes=[],
            hook=None,
            stakes=None,
            chapters=chapters,
            scenes=scenes,
            scene_ids=scene_ids_list,
        )

        # Build Project
        # Determine the effective shape ID for metadata (user-provided or auto-selected)
        effective_shape_id: str | None = None
        if options.shape_id:
            effective_shape_id = options.shape_id
        elif shape:
            # Auto-selected shape
            effective_shape_id = shape.id

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
            enrichment_enabled=options.enrich,
            format=format_name,
            language=expected_language,
        )

        project_config = ProjectConfig(
            version=__version__,
            title=plot.title,
            defaults=ProjectDefaults(language=expected_language) if expected_language else None,
            metadata=metadata,
        )

        project = Project(
            config=project_config,
            plot=plot,
            characters=characters,
            world=world,
            style=style,
        )

        # Write project files if artifacts_dir provided
        if artifacts_dir:
            _write_config(project_config, artifacts_dir)
            _write_style(style, project_config, artifacts_dir)
            _write_characters(characters, project_config, artifacts_dir)
            _write_world(world, project_config, artifacts_dir)
            _write_plot(plot, project_config, artifacts_dir)

    if progress:
        progress.success("Project assembled")

    return project


__all__ = ["generate_prose"]
