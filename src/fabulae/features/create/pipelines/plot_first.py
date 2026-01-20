"""Plot-first generation functions for prose pipeline.

This module contains functions for the plot-first reordering where structure is
determined before content generation.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import TYPE_CHECKING

from fabulae.features.create.schemas import CharacterOutput, StyleOutput, WorldFactOutput
from fabulae.features.create.service import (
    FORMAT_BEATS_PER_SCENE,
    FORMAT_COUNT_RANGES,
    ErrorMode,
    run_stage,
)
from fabulae.llm import LLMConfig
from fabulae.models import Character, LiteratureFormat, StoryShape, WorldFact
from fabulae.prompts import build_system_prompt, format_sections

if TYPE_CHECKING:
    from fabulae.features.create.schemas import SceneBeatTemplate
    from fabulae.features.create.variation import SceneVariation, SelectedVariationPoint


@dataclass
class OutlineStructure:
    """Structure counts for narrative outline."""

    num_chapters: int
    scenes_per_chapter: list[int]
    beats_per_scene: list[int]
    total_scenes: int
    total_beats: int


@dataclass
class ChapterOutline:
    """Content outline for a single chapter."""

    id: str
    title: str | None
    summary: str | None


@dataclass
class SceneOutline:
    """Content outline for a single scene."""

    id: str
    chapter_id: str | None
    title: str | None
    summary: str | None
    beat_count: int


@dataclass
class OutlineContent:
    """Generated content for pre-allocated outline structure."""

    chapters: list[ChapterOutline]
    scenes: list[SceneOutline]


@dataclass
class BeatAssignment:
    """Assignment of a required beat to a specific scene."""

    beat_type: str
    scene_id: str


def generate_outline_structure(
    format: LiteratureFormat,
    shape: StoryShape | None,
    rng: random.Random | None = None,
) -> OutlineStructure:
    """Generate outline structure counts before content generation.

    Args:
        format: The literature format (novel, novella, short-story)
        shape: Optional story shape to guide structure
        rng: Optional random number generator for reproducibility

    Returns:
        OutlineStructure with determined counts

    Raises:
        ValueError: If format is not a prose format or ranges are invalid
    """
    if format not in ("novel", "novella", "short-story"):
        raise ValueError(f"Format {format!r} is not a prose format")

    if rng is None:
        rng = random.Random()

    # Get format ranges
    ranges = FORMAT_COUNT_RANGES[format]
    chapters_range = ranges["chapters"]
    scenes_range = ranges["scenes"]
    beats_range = ranges["beats"]
    beats_per_scene_range = FORMAT_BEATS_PER_SCENE[format]

    # Determine minimum required beats from shape
    min_required_beats = 0
    if shape and shape.required_beats:
        min_required_beats = len(shape.required_beats)

    # Pick number of chapters
    num_chapters = rng.randint(*chapters_range)

    # Pick total number of scenes
    min_scenes, max_scenes = scenes_range
    total_scenes = rng.randint(min_scenes, max_scenes)

    # Ensure we have enough scenes to accommodate required beats
    # Each scene can have beats_per_scene_range[1] beats max
    if min_required_beats > 0:
        min_scenes_needed = (min_required_beats + beats_per_scene_range[1] - 1) // beats_per_scene_range[1]
        total_scenes = max(total_scenes, min_scenes_needed)

    # Distribute scenes across chapters
    scenes_per_chapter = _distribute_items(total_scenes, num_chapters, rng) if num_chapters > 0 else []

    # Determine target total beats considering both format range and required beats
    min_beats, max_beats = beats_range
    target_min_beats = max(min_beats, min_required_beats)

    # Assign beat counts to each scene
    beats_per_scene: list[int] = []

    # First pass: assign random beats within range
    for _ in range(total_scenes):
        beat_count = rng.randint(*beats_per_scene_range)
        beats_per_scene.append(beat_count)

    # Calculate current total
    total_beats_allocated = sum(beats_per_scene)

    # If we need more beats to meet minimum requirement, add them
    if total_beats_allocated < target_min_beats:
        beats_needed = target_min_beats - total_beats_allocated
        attempts = 0
        max_attempts = beats_needed * 10  # Safety limit

        while beats_needed > 0 and attempts < max_attempts:
            scene_index = rng.randint(0, total_scenes - 1)
            # Add beat if we haven't exceeded max beats per scene
            if beats_per_scene[scene_index] < beats_per_scene_range[1]:
                beats_per_scene[scene_index] += 1
                beats_needed -= 1
            attempts += 1

    # Calculate final total
    total_beats = sum(beats_per_scene)

    return OutlineStructure(
        num_chapters=num_chapters,
        scenes_per_chapter=scenes_per_chapter,
        beats_per_scene=beats_per_scene,
        total_scenes=total_scenes,
        total_beats=total_beats,
    )


def _distribute_items(total: int, buckets: int, rng: random.Random) -> list[int]:
    """Distribute items across buckets with some variation.

    Uses a fair distribution with small random variations.

    Args:
        total: Total number of items to distribute
        buckets: Number of buckets
        rng: Random number generator

    Returns:
        List of counts per bucket
    """
    if buckets <= 0:
        return []
    if total <= 0:
        return [0] * buckets

    # Start with base distribution
    base = total // buckets
    remainder = total % buckets

    counts = [base] * buckets

    # Distribute remainder
    for i in range(remainder):
        counts[i] += 1

    # Add small random variation by shuffling around items
    # This creates a more natural distribution
    for _ in range(rng.randint(0, min(total // 4, buckets * 2))):
        # Pick two random buckets
        i = rng.randint(0, buckets - 1)
        j = rng.randint(0, buckets - 1)

        # Transfer one item if possible
        if i != j and counts[i] > 0:
            counts[i] -= 1
            counts[j] += 1

    return counts


async def generate_world_from_slots(
    idea: str,
    format: str,
    shape: StoryShape,
    location_ids: list[str],
    slot_mapping: dict[str, str],
    llm_config: LLMConfig,
    style: StyleOutput | None = None,
    extra_world_fact_ids: list[str] | None = None,
) -> list[WorldFact]:
    """Generate world elements to fill story shape setting slots.

    Args:
        idea: Story idea for context
        format: Literature format (e.g., "novel", "short-story")
        shape: Story shape with setting_slots defined
        location_ids: All pre-allocated location IDs
        slot_mapping: Maps slot name to location ID (e.g., {"ordinary-world": "location-01"})
        llm_config: LLM configuration
        style: Optional style for tone guidance
        extra_world_fact_ids: Optional additional world fact IDs for non-location facts

    Returns:
        List of WorldFact objects (locations and other world facts)

    Raises:
        CreateProjectError: If generation fails after retries
    """
    world_facts: list[WorldFact] = []
    extra_world_fact_ids = extra_world_fact_ids or []

    # Generate locations for setting slots
    for slot in shape.setting_slots:
        # Skip optional slots that aren't in the mapping
        if slot.optional and slot.slot not in slot_mapping:
            continue

        # Get the assigned location ID for this slot
        if slot.slot not in slot_mapping:
            raise ValueError(f"Required setting slot {slot.slot!r} not found in slot_mapping")

        assigned_id = slot_mapping[slot.slot]

        # Build prompt for this location
        system_prompt = _build_location_prompt(
            format=format,
            slot=slot.slot,
            needs=slot.needs,
            assigned_id=assigned_id,
            style=style,
        )

        user_prompt = f"Story idea: {idea}"

        # Extract text for language guard
        def extract_text(output: WorldFactOutput) -> str:
            parts = [output.name] + output.facts
            return " ".join(parts)

        # Validate that ID is unchanged (bind loop var with default arg)
        def validate(output: WorldFactOutput, expected_id: str = assigned_id) -> str | None:
            if output.id != expected_id:
                return f"ID must be {expected_id!r}, got {output.id!r}"
            if output.type != "location":
                return f"Type must be 'location' for setting slot, got {output.type!r}"
            return None

        # Run stage with validation
        result = await run_stage(
            result_type=WorldFactOutput,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=llm_config,
            expected_language=style.language if style else None,
            extract_text=extract_text,
            validate=validate,
            error_mode=ErrorMode.STRICT,
        )

        # Convert to WorldFact model
        world_fact = WorldFact(
            id=result.output.id,
            type=result.output.type,
            name=result.output.name,
            facts=result.output.facts,
        )
        world_facts.append(world_fact)

    # Generate additional world facts if IDs provided
    if extra_world_fact_ids:
        for fact_id in extra_world_fact_ids:
            # Build prompt for generic world fact
            system_prompt = _build_world_fact_prompt(
                format=format,
                assigned_id=fact_id,
                existing_locations=[wf.name for wf in world_facts if wf.type == "location"],
                style=style,
            )

            user_prompt = f"Story idea: {idea}"

            # Extract text for language guard
            def extract_text(output: WorldFactOutput) -> str:
                parts = [output.name] + output.facts
                return " ".join(parts)

            # Validate that ID is unchanged (bind loop var with default arg)
            def validate(output: WorldFactOutput, expected_id: str = fact_id) -> str | None:
                if output.id != expected_id:
                    return f"ID must be {expected_id!r}, got {output.id!r}"
                return None

            # Run stage with validation
            result = await run_stage(
                result_type=WorldFactOutput,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                config=llm_config,
                expected_language=style.language if style else None,
                extract_text=extract_text,
                validate=validate,
                error_mode=ErrorMode.STRICT,
            )

            # Convert to WorldFact model
            world_fact = WorldFact(
                id=result.output.id,
                type=result.output.type,
                name=result.output.name,
                facts=result.output.facts,
            )
            world_facts.append(world_fact)

    return world_facts


def _build_location_prompt(
    format: str,
    slot: str,
    needs: str,
    assigned_id: str,
    style: StyleOutput | None,
) -> str:
    """Build prompt for generating a location for a setting slot."""
    purpose = (
        f"Generate a location for the '{slot}' setting slot in the story. "
        "This location serves a specific narrative function."
    )

    guidelines = [
        "Return valid JSON only (no markdown, no extra text).",
        "Match the schema exactly; omit fields you do not use.",
        "Use the provided ID exactly, do not change it.",
        "The type must be 'location' for setting slots.",
        "Keep facts concise and evocative.",
    ]

    # Add language requirement if specified
    if style and style.language:
        guidelines.append(f"CRITICAL: Generate ALL text (name, facts) in {style.language.upper()} language.")

    schema = (
        "{\n"
        f'  "id": "{assigned_id}",\n'
        '  "type": "location",\n'
        '  "name": "The Harbor District",\n'
        '  "facts": ["foggy streets", "sounds of distant ships", "smell of brine and rust"]\n'
        "}"
    )

    sections: dict[str, str] = {
        "Format": format,
        "Setting Slot": slot,
        "Narrative Function": needs,
        "Assigned ID": f'"{assigned_id}" - Use this ID exactly in your output. Do not change it.',
        "Output Schema (JSON)": schema,
    }

    if style:
        style_parts = []
        if style.voice:
            style_parts.append(f"Voice: {style.voice}")
        if style.register_:
            style_parts.append(f"Register: {style.register_}")
        if style_parts:
            sections["Style"] = ", ".join(style_parts)

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


def _build_world_fact_prompt(
    format: str,
    assigned_id: str,
    existing_locations: list[str],
    style: StyleOutput | None,
) -> str:
    """Build prompt for generating a general world fact."""
    purpose = "Generate a world-building element that adds depth to the story setting."

    guidelines = [
        "Return valid JSON only (no markdown, no extra text).",
        "Match the schema exactly; omit fields you do not use.",
        "Use the provided ID exactly, do not change it.",
        "Choose appropriate type: location, culture, history, rule, or object.",
        "Keep facts concise and relevant.",
    ]

    # Add language requirement if specified
    if style and style.language:
        guidelines.append(f"CRITICAL: Generate ALL text (name, facts) in {style.language.upper()} language.")

    schema = (
        "{\n"
        f'  "id": "{assigned_id}",\n'
        '  "type": "culture",\n'
        '  "name": "The Guild of Watchers",\n'
        '  "facts": ["ancient tradition", "sworn to neutrality", "recognizable by their silver pins"]\n'
        "}"
    )

    sections: dict[str, str] = {
        "Format": format,
        "Assigned ID": f'"{assigned_id}" - Use this ID exactly in your output. Do not change it.',
        "Output Schema (JSON)": schema,
    }

    if existing_locations:
        sections["Existing Locations"] = ", ".join(existing_locations)

    if style:
        style_parts = []
        if style.voice:
            style_parts.append(f"Voice: {style.voice}")
        if style.register_:
            style_parts.append(f"Register: {style.register_}")
        if style_parts:
            sections["Style"] = ", ".join(style_parts)

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


async def generate_outline_content(
    idea: str,
    format: LiteratureFormat,
    structure: OutlineStructure,
    shape: StoryShape | None,
    llm_config: LLMConfig,
    chapter_ids: list[str],
    scene_ids: list[str],
    expected_language: str | None = None,
) -> OutlineContent:
    """Generate chapter and scene content for pre-allocated IDs.

    Args:
        idea: The core narrative idea
        format: The literature format (novel, novella, short-story)
        structure: Pre-generated outline structure with counts
        shape: Optional story shape for thematic guidance
        llm_config: LLM configuration for generation
        chapter_ids: Pre-assigned chapter IDs to fill
        scene_ids: Pre-assigned scene IDs to fill
        expected_language: Optional ISO 639-1 language code to enforce

    Returns:
        OutlineContent with chapters and scenes filled with content

    Raises:
        ValueError: If IDs don't match structure
        CreateProjectError: If LLM generation fails
    """
    from fabulae.features.create.schemas import OutlineContentOutput

    # Validate inputs
    if len(chapter_ids) != structure.num_chapters:
        raise ValueError(f"Expected {structure.num_chapters} chapter IDs, got {len(chapter_ids)}")
    if len(scene_ids) != structure.total_scenes:
        raise ValueError(f"Expected {structure.total_scenes} scene IDs, got {len(scene_ids)}")

    # Build scene-to-chapter mapping and scene beat counts
    scene_to_chapter: dict[str, str | None] = {}
    scene_beat_counts: dict[str, int] = {}

    scene_index = 0
    if structure.num_chapters > 0:
        for chapter_index, scene_count in enumerate(structure.scenes_per_chapter):
            chapter_id = chapter_ids[chapter_index]
            for _ in range(scene_count):
                scene_id = scene_ids[scene_index]
                scene_to_chapter[scene_id] = chapter_id
                scene_beat_counts[scene_id] = structure.beats_per_scene[scene_index]
                scene_index += 1
    else:
        for scene_index, scene_id in enumerate(scene_ids):
            scene_to_chapter[scene_id] = None
            scene_beat_counts[scene_id] = structure.beats_per_scene[scene_index]

    # Build context for prompt
    context_parts = [
        f"Idea: {idea.strip()}",
        f"Format: {format}",
        f"Structure: {structure.num_chapters} chapters, {structure.total_scenes} scenes, {structure.total_beats} beats",
    ]

    if shape:
        context_parts.append(f"Story Shape: {shape.name} - {shape.description}")

    # Build chapter requirements
    if chapter_ids:
        chapter_list = []
        for _chapter_index, chapter_id in enumerate(chapter_ids):
            scenes_in_chapter = [sid for sid in scene_ids if scene_to_chapter[sid] == chapter_id]
            chapter_list.append(f"  - {chapter_id} ({len(scenes_in_chapter)} scenes)")
        context_parts.append("Chapters:\n" + "\n".join(chapter_list))

    # Build scene requirements
    scene_list = []
    for scene_id in scene_ids:
        beat_count = scene_beat_counts[scene_id]
        chapter_ref = f" (chapter: {scene_to_chapter[scene_id]})" if scene_to_chapter[scene_id] else ""
        scene_list.append(f"  - {scene_id}{chapter_ref}: {beat_count} beats")
    context_parts.append("Scenes:\n" + "\n".join(scene_list))

    # Build language instruction
    language_instruction = ""
    if expected_language:
        lang = expected_language.upper()
        language_instruction = f"\n6. Generate ALL text content (titles, summaries) in {lang} language"

    system_prompt = f"""You are a narrative architect generating chapter and scene outlines.

CRITICAL REQUIREMENTS:
1. You MUST use the EXACT IDs provided - do not generate new IDs
2. All chapter IDs must appear in your output: {chapter_ids}
3. All scene IDs must appear in your output: {scene_ids}
4. Each scene MUST have the correct beat_count as specified
5. Scenes must be assigned to their designated chapters{language_instruction}

Generate compelling titles and summaries that:
- Match the story idea and format
- Create narrative progression across chapters
- Build dramatic tension across scenes
- Respect the story shape if provided"""

    user_prompt = "\n\n".join(context_parts)

    # Validation function
    def validate_output(output: OutlineContentOutput) -> str | None:
        # Check chapter IDs
        output_chapter_ids = {ch.id for ch in output.chapters}
        expected_chapter_ids = set(chapter_ids)
        if output_chapter_ids != expected_chapter_ids:
            missing = expected_chapter_ids - output_chapter_ids
            extra = output_chapter_ids - expected_chapter_ids
            errors = []
            if missing:
                errors.append(f"missing chapters: {sorted(missing)}")
            if extra:
                errors.append(f"unexpected chapters: {sorted(extra)}")
            # Add clear guidance about expected chapters
            expected_info = f"Expected exactly {len(chapter_ids)} chapters with IDs: {chapter_ids}"
            return f"Chapter ID mismatch - {', '.join(errors)}. {expected_info}"

        # Check scene IDs
        output_scene_ids = {sc.id for sc in output.scenes}
        expected_scene_ids = set(scene_ids)
        if output_scene_ids != expected_scene_ids:
            missing = expected_scene_ids - output_scene_ids
            extra = output_scene_ids - expected_scene_ids
            errors = []
            if missing:
                errors.append(f"missing scenes: {sorted(missing)}")
            if extra:
                errors.append(f"unexpected scenes: {sorted(extra)}")
            # Add clear guidance about expected scenes
            expected_info = f"Expected exactly {len(scene_ids)} scenes with IDs: {scene_ids}"
            return f"Scene ID mismatch - {', '.join(errors)}. {expected_info}"

        # Check scene-to-chapter assignments
        for scene in output.scenes:
            expected_chapter = scene_to_chapter[scene.id]
            if scene.chapter_id != expected_chapter:
                return f"Scene {scene.id} has wrong chapter: expected {expected_chapter}, got {scene.chapter_id}"

        # Check beat counts
        for scene in output.scenes:
            expected_beats = scene_beat_counts[scene.id]
            if scene.beat_count != expected_beats:
                return f"Scene {scene.id} has wrong beat_count: expected {expected_beats}, got {scene.beat_count}"

        return None

    # Extract text for language guard
    def extract_text(output: OutlineContentOutput) -> str:
        parts = []
        for chapter in output.chapters:
            if chapter.title:
                parts.append(chapter.title)
            if chapter.summary:
                parts.append(chapter.summary)
        for scene in output.scenes:
            if scene.title:
                parts.append(scene.title)
            if scene.summary:
                parts.append(scene.summary)
        return "\n".join(parts)

    result = await run_stage(
        result_type=OutlineContentOutput,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        config=llm_config,
        expected_language=expected_language,
        extract_text=extract_text,
        validate=validate_output,
        max_retries=3,
    )

    # Convert to domain dataclasses
    chapters = [ChapterOutline(id=ch.id, title=ch.title, summary=ch.summary) for ch in result.output.chapters]

    scenes = [
        SceneOutline(
            id=sc.id,
            chapter_id=sc.chapter_id,
            title=sc.title,
            summary=sc.summary,
            beat_count=sc.beat_count,
        )
        for sc in result.output.scenes
    ]

    return OutlineContent(chapters=chapters, scenes=scenes)


async def generate_characters_from_slots(
    idea: str,
    format: str,
    shape: StoryShape,
    character_ids: list[str],
    slot_mapping: dict[str, str],
    llm_config: LLMConfig,
    style: StyleOutput | None = None,
) -> list[Character]:
    """Generate characters to fill story shape character slots.

    Args:
        idea: Story idea for context
        format: Literature format (e.g., "novel", "short-story")
        shape: Story shape with character_slots defined
        character_ids: All pre-allocated character IDs
        slot_mapping: Maps slot name to character ID (e.g., {"hero": "character-01"})
        llm_config: LLM configuration
        style: Optional style for tone guidance

    Returns:
        List of Character objects

    Raises:
        CreateProjectError: If generation fails after retries
        ValueError: If a required slot is missing from slot_mapping
    """
    characters: list[Character] = []

    # Generate characters for each slot
    for slot in shape.character_slots:
        # Skip optional slots that aren't in the mapping
        if slot.optional and slot.slot not in slot_mapping:
            continue

        # Get the assigned character ID for this slot
        if slot.slot not in slot_mapping:
            raise ValueError(f"Required character slot {slot.slot!r} not found in slot_mapping")

        assigned_id = slot_mapping[slot.slot]

        # Build prompt for this character
        system_prompt = _build_character_slot_prompt(
            format=format,
            slot=slot.slot,
            needs=slot.needs,
            assigned_id=assigned_id,
            style=style,
        )

        user_prompt = f"Story idea: {idea}"

        # Extract text for language guard
        def extract_text(output: CharacterOutput) -> str:
            parts = [
                output.name,
                output.role or "",
                output.desire or "",
                output.need or "",
                output.flaw or "",
                output.secret or "",
                " ".join(output.traits),
            ]
            return " ".join(part for part in parts if part)

        # Validate that ID is unchanged (bind loop var with default arg)
        def validate(output: CharacterOutput, expected_id: str = assigned_id) -> str | None:
            if output.id != expected_id:
                return f"ID must be {expected_id!r}, got {output.id!r}"
            if not output.name:
                return "Character name is required"
            return None

        # Run stage with validation
        result = await run_stage(
            result_type=CharacterOutput,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=llm_config,
            expected_language=style.language if style else None,
            extract_text=extract_text,
            validate=validate,
            error_mode=ErrorMode.STRICT,
        )

        # Convert to Character model
        character = Character(
            id=result.output.id,
            name=result.output.name,
            role=result.output.role,
            desire=result.output.desire,
            need=result.output.need,
            flaw=result.output.flaw,
            secret=result.output.secret,
            traits=result.output.traits,
        )
        characters.append(character)

    return characters


def _build_character_slot_prompt(
    format: str,
    slot: str,
    needs: str,
    assigned_id: str,
    style: StyleOutput | None,
) -> str:
    """Build prompt for generating a character for a character slot."""
    purpose = (
        f"Generate a character for the '{slot}' slot in the story. This character serves a specific narrative function."
    )

    guidelines = [
        "Return valid JSON only (no markdown, no extra text).",
        "Match the schema exactly; omit fields you do not use.",
        "Use the provided ID exactly, do not change it.",
        "Create a character that fulfills the slot's narrative needs.",
        "Include desire, need, and flaw to create a compelling arc.",
    ]

    # Add language requirement if specified
    if style and style.language:
        guidelines.append(
            f"CRITICAL: Generate ALL text (name, role, desire, need, flaw, secret, traits) "
            f"in {style.language.upper()} language."
        )

    schema = (
        "{\n"
        f'  "id": "{assigned_id}",\n'
        '  "name": "Alex Chen",\n'
        '  "role": "protagonist",\n'
        '  "desire": "solve the mystery",\n'
        '  "need": "learn to trust others",\n'
        '  "flaw": "impatient and impulsive",\n'
        '  "secret": "hiding a past failure",\n'
        '  "traits": ["sharp", "determined", "guarded"]\n'
        "}"
    )

    sections: dict[str, str] = {
        "Format": format,
        "Character Slot": slot,
        "Narrative Function": needs,
        "Assigned ID": f'"{assigned_id}" - Use this ID exactly in your output. Do not change it.',
        "Output Schema (JSON)": schema,
    }

    if style:
        style_parts = []
        if style.voice:
            style_parts.append(f"Voice: {style.voice}")
        if style.register_:
            style_parts.append(f"Register: {style.register_}")
        if style_parts:
            sections["Style"] = ", ".join(style_parts)

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


def assign_required_beats_to_scenes(
    shape: StoryShape, scene_ids: list[str], rng: random.Random | None = None
) -> list[BeatAssignment]:
    """Assign required beats from story shape to scenes based on position constraints.

    Args:
        shape: Story shape containing required beats
        scene_ids: List of scene IDs to assign beats to
        rng: Optional random number generator for reproducibility

    Returns:
        List of BeatAssignment objects mapping beat types to scene IDs

    Raises:
        ValueError: If there are no scenes or no required beats
    """
    if not scene_ids:
        raise ValueError("Cannot assign beats to empty scene list")

    if not shape.required_beats:
        return []

    if rng is None:
        rng = random.Random()

    assignments: list[BeatAssignment] = []
    num_scenes = len(scene_ids)

    # Calculate position boundaries based on scene count
    # early: first 25%, middle: 25-70%, late: 70-90%, climax: last 10%
    early_end = max(1, int(num_scenes * 0.25))
    middle_start = max(0, int(num_scenes * 0.25))
    middle_end = max(1, int(num_scenes * 0.70))
    late_start = max(0, int(num_scenes * 0.70))
    late_end = max(1, int(num_scenes * 0.90))
    climax_start = max(0, int(num_scenes * 0.90))

    # Ensure climax_start doesn't exceed num_scenes
    climax_start = min(climax_start, num_scenes - 1)

    for beat in shape.required_beats:
        # Determine valid scene range based on position
        if beat.position == "early":
            start_idx = 0
            end_idx = early_end
        elif beat.position == "middle":
            start_idx = middle_start
            end_idx = middle_end
        elif beat.position == "late":
            start_idx = late_start
            end_idx = late_end
        elif beat.position == "climax":
            start_idx = climax_start
            end_idx = num_scenes
        else:  # "anywhere"
            start_idx = 0
            end_idx = num_scenes

        # Apply flexibility to widen the range
        if beat.flexibility == "flexible":
            # Allow some overlap with adjacent ranges (±10%)
            overlap = max(1, int(num_scenes * 0.10))
            start_idx = max(0, start_idx - overlap)
            end_idx = min(num_scenes, end_idx + overlap)
        elif beat.flexibility == "very-flexible":
            # Allow significant overlap (±20%)
            overlap = max(1, int(num_scenes * 0.20))
            start_idx = max(0, start_idx - overlap)
            end_idx = min(num_scenes, end_idx + overlap)
        # "fixed" uses the exact range without modification

        # Ensure we have at least one scene to choose from
        if start_idx >= end_idx:
            end_idx = start_idx + 1

        # Ensure end_idx doesn't exceed num_scenes
        end_idx = min(end_idx, num_scenes)

        # Randomly select a scene from the valid range
        scene_index = rng.randint(start_idx, end_idx - 1)
        scene_id = scene_ids[scene_index]

        # Create assignment
        assignment = BeatAssignment(beat_type=beat.type, scene_id=scene_id)
        assignments.append(assignment)

    return assignments


# Default filler beat kinds to use when no variation is provided
DEFAULT_FILLER_BEAT_KINDS = (
    "bridge",
    "complication",
    "reaction",
    "escalation",
    "turn",
    "setup",
)


def build_beat_templates_with_variation(
    scene_ids: list[str],
    beats_per_scene: list[int],
    beat_assignments: list[BeatAssignment],
    scene_variations: list[SceneVariation] | None = None,
    selected_variation_points: list[SelectedVariationPoint] | None = None,
    rng: random.Random | None = None,
) -> dict[str, SceneBeatTemplate]:
    """Build beat templates incorporating variation decisions and shape variation points.

    Constructs beat templates for each scene by:
    1. Getting the beat count for each scene from beats_per_scene
    2. Finding required beats assigned to this scene from beat_assignments
    3. Finding variation points assigned to this scene from selected_variation_points
    4. Finding variation decisions for this scene from scene_variations (if provided)
    5. Placing required beats at spread positions throughout the template
    6. Adding variation point beats with their descriptions
    7. Including complication beats where variation decided (has_complication=True)
    8. Including character moment beats where variation decided (has_character_moment=True)
    9. Filling remaining slots with filler beats (from scene_variation.filler_beats if available,
       otherwise random from DEFAULT_FILLER_BEAT_KINDS)

    Args:
        scene_ids: List of scene IDs in narrative order
        beats_per_scene: List of beat counts for each scene (same length as scene_ids)
        beat_assignments: List of BeatAssignment objects mapping required beats to scenes
        scene_variations: Optional list of SceneVariation objects with variation decisions
        selected_variation_points: Optional list of variation points selected from story shape
        rng: Optional random number generator for reproducibility

    Returns:
        Dictionary mapping scene_id to SceneBeatTemplate

    Raises:
        ValueError: If scene_ids and beats_per_scene have different lengths
    """
    from fabulae.features.create.schemas import BeatTemplateItem, SceneBeatTemplate
    from fabulae.features.create.variation import (
        SceneVariation as SceneVariationType,
    )
    from fabulae.features.create.variation import (
        SelectedVariationPoint as SelectedVariationPointType,
    )

    if len(scene_ids) != len(beats_per_scene):
        raise ValueError(
            f"scene_ids and beats_per_scene must have same length: {len(scene_ids)} vs {len(beats_per_scene)}"
        )

    if rng is None:
        rng = random.Random()

    # Build lookup for beat assignments by scene
    scene_beat_assignments: dict[str, list[BeatAssignment]] = {scene_id: [] for scene_id in scene_ids}
    for assignment in beat_assignments:
        if assignment.scene_id in scene_beat_assignments:
            scene_beat_assignments[assignment.scene_id].append(assignment)

    # Build lookup for variation points by scene_id
    scene_variation_points_map: dict[str, list[SelectedVariationPointType]] = {scene_id: [] for scene_id in scene_ids}
    if selected_variation_points:
        for vp in selected_variation_points:
            if vp.assigned_scene_id and vp.assigned_scene_id in scene_variation_points_map:
                scene_variation_points_map[vp.assigned_scene_id].append(vp)

    # Build lookup for scene variations by scene_id
    scene_variation_map: dict[str, SceneVariationType] = {}
    if scene_variations:
        for scene_var in scene_variations:
            scene_variation_map[scene_var.scene_id] = scene_var

    templates: dict[str, SceneBeatTemplate] = {}

    for scene_index, scene_id in enumerate(scene_ids):
        beat_count = beats_per_scene[scene_index]
        required_beats = scene_beat_assignments[scene_id]
        variation_points = scene_variation_points_map[scene_id]
        variation: SceneVariationType | None = scene_variation_map.get(scene_id)

        # Calculate total beats needed: required + variation points + complication + character moment
        num_required = len(required_beats)
        num_complication = 1 if variation and variation.has_complication else 0
        num_character_moment = 1 if variation and variation.has_character_moment else 0

        # Determine filler beat kinds to use
        if variation and variation.filler_beats:
            # Use filler beats from variation
            filler_pool = variation.filler_beats
        else:
            # Use default filler beats
            filler_pool = list(DEFAULT_FILLER_BEAT_KINDS)

        # Calculate positions for required beats (spread them evenly)
        required_positions: list[int] = []
        if num_required > 0:
            # Spread required beats across the template
            if num_required == 1:
                # Single required beat: place in the middle
                required_positions = [beat_count // 2]
            else:
                # Multiple required beats: spread evenly
                step = beat_count / (num_required + 1)
                required_positions = [int((i + 1) * step) for i in range(num_required)]

        # Create beat template items for the entire template
        all_beats: list[BeatTemplateItem | None] = [None] * beat_count

        # Place required beats at their positions
        for i, assignment in enumerate(required_beats):
            if i < len(required_positions):
                pos = required_positions[i]
                # Ensure position is valid
                if 0 <= pos < beat_count:
                    all_beats[pos] = BeatTemplateItem(
                        kind=assignment.beat_type,
                        required=True,
                        plot_pattern_beat=assignment.beat_type,
                        notes=None,
                    )

        # Find available positions for variation points
        available_positions_for_vp = [i for i in range(beat_count) if all_beats[i] is None]

        # Add variation point beats (optional enhancements from story shape)
        for vp in variation_points:
            if available_positions_for_vp:
                # Place variation point beat
                pos = rng.choice(available_positions_for_vp)
                # Normalize the description (remove excess whitespace from YAML)
                desc = " ".join(vp.description.strip().split()) if vp.description else None
                all_beats[pos] = BeatTemplateItem(
                    kind=vp.type,
                    required=False,
                    plot_pattern_beat=vp.type,
                    notes=None,
                    variation_point_description=desc,
                )
                available_positions_for_vp.remove(pos)

        # Find positions for complication and character moment beats
        # Place them in unfilled positions, preferring middle to late positions
        available_positions = [i for i in range(beat_count) if all_beats[i] is None]

        # Add complication beat if needed
        if num_complication > 0 and available_positions and variation:
            # Prefer positions in the middle to late part of the scene
            mid_point = len(available_positions) // 2
            preferred_positions = available_positions[mid_point:]
            pos = rng.choice(preferred_positions) if preferred_positions else rng.choice(available_positions)

            all_beats[pos] = BeatTemplateItem(
                kind="complication",
                required=False,
                plot_pattern_beat=None,
                notes=f"complication: {variation.complication_type}" if variation.complication_type else None,
            )
            available_positions.remove(pos)

        # Add character moment beat if needed
        if num_character_moment > 0 and available_positions and variation:
            # Can go anywhere in available positions
            pos = rng.choice(available_positions)
            all_beats[pos] = BeatTemplateItem(
                kind="character-moment",
                required=False,
                plot_pattern_beat=None,
                notes=f"focus: {variation.character_focus}" if variation.character_focus else None,
            )
            available_positions.remove(pos)

        # Fill remaining positions with filler beats
        for pos in available_positions:
            if pos < beat_count and all_beats[pos] is None:
                filler_kind = rng.choice(filler_pool)
                all_beats[pos] = BeatTemplateItem(
                    kind=filler_kind,
                    required=False,
                    plot_pattern_beat=None,
                    notes=None,
                )

        # Collect all beats (filter out any remaining None values, though there shouldn't be any)
        final_beats = [beat for beat in all_beats if beat is not None]

        # Create the scene beat template
        template = SceneBeatTemplate(
            scene_id=scene_id,
            beat_count=beat_count,
            beats=final_beats,
        )
        templates[scene_id] = template

    return templates
