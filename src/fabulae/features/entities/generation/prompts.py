"""Shared prompt builders for entity generation.

These prompts are used by both CRUD suggest commands and the create pipeline.
They support two modes:
- Full context mode (CRUD): Pass a project for comprehensive context
- Minimal context mode (Create): Pass individual parameters for focused generation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from fabulae.prompts import build_system_prompt, format_sections

if TYPE_CHECKING:
    from fabulae.features.create.schemas import StyleOutput
    from fabulae.models import Beat, Chapter, Character, Fragment, Scene, Stanza, WorldFact


# =============================================================================
# Beat Slot for Create Pipeline
# =============================================================================


@dataclass
class BeatSlotInfo:
    """Beat slot information for create pipeline scene generation.

    This is a simplified representation of BeatSlot from create/graph.py,
    allowing the generation module to work with beat slots without importing
    the full create module.
    """

    id: str
    kind: str
    required: bool = False
    notes: str | None = None


def _format_guidelines() -> list[str]:
    """Standard guidelines for all generation prompts."""
    return [
        "CRITICAL: Return ONLY valid JSON. No markdown, no extra text.",
        "Match the schema exactly. Omit optional fields you don't use.",
        "IDs must be lowercase ASCII with hyphens (a-z, 0-9, hyphen).",
        "Keep outputs concise and focused.",
    ]


def _format_language_instruction(language: str | None) -> str:
    """Format language instruction for prompt."""
    if language:
        return (
            f"\nIMPORTANT: All text content MUST be written in {language}. "
            f"Generate names and descriptions in this language.\n"
        )
    return ""


def _format_style_hint(style: StyleOutput | None) -> str:
    """Format StyleOutput as a compact hint for prompts.

    This provides the LLM with narrative style context from the create pipeline.
    """
    if not style:
        return ""

    parts: list[str] = []
    if style.pov:
        parts.append(f"POV: {style.pov}")
    if style.tense:
        parts.append(f"Tense: {style.tense}")
    if style.voice:
        parts.append(f"Voice: {style.voice}")
    if style.register_:
        parts.append(f"Register: {style.register_}")

    return ", ".join(parts) if parts else ""


def _format_existing_characters(characters: list[Character]) -> str:
    """Format existing characters for prompt context."""
    if not characters:
        return "No existing characters."
    lines = []
    for c in characters:
        line = f"- {c.name} ({c.id}): {c.role or 'supporting'}"
        if c.desire:
            line += f" - wants: {c.desire}"
        lines.append(line)
    return "\n".join(lines)


def _format_existing_world_facts(facts: list[WorldFact]) -> str:
    """Format existing world facts for prompt context."""
    if not facts:
        return "No world facts defined."
    lines = []
    for f in facts:
        fact_preview = ", ".join(f.facts[:2]) if f.facts else "No details"
        lines.append(f"- {f.id} [{f.type}]: {f.name} - {fact_preview}")
    return "\n".join(lines)


def _format_existing_scenes(scenes: list[Scene]) -> str:
    """Format existing scenes for prompt context."""
    if not scenes:
        return "No existing scenes."
    return "\n".join([f"- {s.id}: {s.summary[:50] if s.summary else 'No summary'}" for s in scenes])


def _format_existing_beats(beats: list[Beat]) -> str:
    """Format existing beats for prompt context."""
    if not beats:
        return "No beats yet."
    return "\n".join([f"- {b.id}: [{b.kind}] {b.summary}" for b in beats])


def _format_existing_fragments(fragments: list[Fragment]) -> str:
    """Format existing fragments for prompt context."""
    if not fragments:
        return "No fragments yet."
    lines = []
    for f in fragments:
        content_preview = f.content[:50] + "..." if len(f.content) > 50 else f.content
        lines.append(f"- {f.id}: {content_preview}")
    return "\n".join(lines)


def _format_existing_stanzas(stanzas: list[Stanza]) -> str:
    """Format existing stanzas for prompt context."""
    if not stanzas:
        return "No stanzas yet."
    lines = []
    for s in stanzas:
        first_line = s.lines[0] if s.lines else "No lines"
        line_preview = first_line[:40] + "..." if len(first_line) > 40 else first_line
        lines.append(f'- {s.id}: "{line_preview}"')
    return "\n".join(lines)


def _format_existing_chapters(chapters: list[Chapter]) -> str:
    """Format existing chapters for prompt context."""
    if not chapters:
        return "No chapters yet."
    lines = []
    for c in chapters:
        summary_preview = c.summary[:50] + "..." if c.summary and len(c.summary) > 50 else (c.summary or "No summary")
        lines.append(f"- {c.id}: {c.title or 'Untitled'} - {summary_preview}")
    return "\n".join(lines)


# =============================================================================
# Character Prompt
# =============================================================================


def build_character_prompt(
    premise: str | None = None,
    existing_characters: list[Character] | None = None,
    role_hint: str | None = None,
    name_hint: str | None = None,
    needs_hint: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    style: StyleOutput | None = None,
) -> str:
    """Build prompt for character generation.

    This prompt is used by both CRUD suggest and create pipeline.

    Args:
        premise: Story premise for context
        existing_characters: Characters already in project (to avoid duplicates)
        role_hint: Suggested role (protagonist, antagonist, supporting)
        name_hint: Suggested name (from shape slot)
        needs_hint: What this character should provide to the story
        guidance: User-provided guidance text
        language: Language code for content generation
        assigned_id: Pre-assigned ID to use (for create pipeline)
        style: StyleOutput for narrative style context (from create pipeline)

    Returns:
        System prompt for character generation
    """
    purpose = "Create a character for a story."
    if role_hint:
        purpose += f" The character should fill the role of {role_hint}."

    # Build schema with optional assigned ID
    id_line = f'  "id": "{assigned_id}",' if assigned_id else '  "id": "lowercase-with-hyphens",'

    schema = (
        "{\n"
        f"{id_line}\n"
        '  "name": "Character Name",\n'
        '  "role": "protagonist | antagonist | supporting",\n'
        '  "desire": "What they consciously want (1 sentence)",\n'
        '  "need": "What they actually need (1 sentence)",\n'
        '  "flaw": "Key weakness (1-3 words)",\n'
        '  "secret": "Something hidden (1 sentence, optional)",\n'
        '  "traits": ["trait1", "trait2"]\n'
        "}"
    )

    sections: dict[str, str] = {}

    if assigned_id:
        sections["Assigned ID"] = f'"{assigned_id}" - Use this exact ID in your output.'

    if language:
        sections["Language"] = f"Generate all text content in {language}."

    if premise:
        sections["Story Premise"] = premise

    # Add style hint if provided (from create pipeline)
    style_hint = _format_style_hint(style)
    if style_hint:
        sections["Style"] = style_hint

    if role_hint:
        sections["Role"] = role_hint

    if needs_hint:
        sections["Character Needs"] = f"This character should: {needs_hint}"

    if name_hint:
        sections["Suggested Name"] = name_hint

    if guidance:
        sections["User Guidance"] = guidance

    existing = existing_characters or []
    if existing:
        sections["Existing Characters (avoid duplicating)"] = _format_existing_characters(existing)
        existing_names = [c.name for c in existing]
        sections["Names Already Used"] = ", ".join(existing_names)

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Generate a unique character that complements the existing cast. "
        "Keep desire/need/flaw distinct - they should create internal conflict. "
        "Traits should be personality characteristics, not plot points."
    )

    guidelines = _format_guidelines()
    if assigned_id:
        guidelines.insert(1, "CRITICAL: Use the Assigned ID exactly - do not modify it.")

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


# =============================================================================
# World Fact / Location Prompt
# =============================================================================


def build_world_fact_prompt(
    premise: str | None = None,
    existing_facts: list[WorldFact] | None = None,
    fact_type: str | None = None,
    needs_hint: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    style: StyleOutput | None = None,
) -> str:
    """Build prompt for world fact generation.

    Args:
        premise: Story premise for context
        existing_facts: World facts already in project (to avoid duplicates)
        fact_type: Required type (location, culture, history, rule, object)
        needs_hint: What this world fact should provide
        guidance: User-provided guidance text
        language: Language code for content generation
        assigned_id: Pre-assigned ID to use (for create pipeline)
        style: StyleOutput for narrative style context (from create pipeline)

    Returns:
        System prompt for world fact generation
    """
    purpose = "Create a world-building element for a story."
    if fact_type:
        purpose += f" Generate a {fact_type}."

    # Build schema
    id_line = f'  "id": "{assigned_id}",' if assigned_id else '  "id": "lowercase-with-hyphens",'

    if fact_type:
        type_line = f'  "type": "{fact_type}",'
    else:
        type_line = '  "type": "location | culture | history | rule | object",'

    schema = (
        "{\n"
        f"{id_line}\n"
        f"{type_line}\n"
        '  "name": "Name of location or concept",\n'
        '  "facts": ["sensory detail 1", "atmosphere/mood", "distinctive feature"]\n'
        "}"
    )

    sections: dict[str, str] = {}

    if assigned_id:
        sections["Assigned ID"] = f'"{assigned_id}" - Use this exact ID in your output.'

    if language:
        sections["Language"] = f"Generate all text content in {language}."

    if premise:
        sections["Story Premise"] = premise

    # Add style hint if provided (from create pipeline)
    style_hint = _format_style_hint(style)
    if style_hint:
        sections["Style"] = style_hint

    if fact_type:
        sections["Required Type"] = fact_type

    if needs_hint:
        sections["Location Needs"] = f"This element should: {needs_hint}"

    if guidance:
        sections["User Guidance"] = guidance

    existing = existing_facts or []
    if existing:
        sections["Existing World Facts (avoid duplicating)"] = _format_existing_world_facts(existing)
        existing_names = [f.name for f in existing]
        sections["Names Already Used"] = ", ".join(existing_names)

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Generate a world element that enriches the story's setting. "
        "Facts should be concrete, sensory details (sounds, smells, visuals, textures). "
        "Include 2-4 facts that make this element distinctive."
    )

    guidelines = _format_guidelines()
    if assigned_id:
        guidelines.insert(1, "CRITICAL: Use the Assigned ID exactly - do not modify it.")

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


# =============================================================================
# Scene Prompt
# =============================================================================


def build_scene_prompt(
    premise: str | None = None,
    available_characters: list[Character] | None = None,
    available_locations: list[WorldFact] | None = None,
    existing_scenes: list[Scene] | None = None,
    chapter_context: str | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    include_beats: bool = False,
    beat_count: int = 0,
    style: StyleOutput | None = None,
    beat_slots: list[BeatSlotInfo] | None = None,
    previous_scene_summaries: list[str] | None = None,
    position_in_story: int | None = None,
    total_scenes: int | None = None,
    position_label: str | None = None,
) -> str:
    """Build prompt for scene generation.

    This prompt supports two modes:
    - CRUD mode: beat_slots=None, optionally include_beats=True with beat_count
    - Create mode: beat_slots=[...] for pre-assigned beat IDs

    Args:
        premise: Story premise for context
        available_characters: Characters that can appear in scene
        available_locations: Locations that can be used
        existing_scenes: Scenes already in project
        chapter_context: Information about the target chapter
        guidance: User-provided guidance text
        language: Language code for content generation
        assigned_id: Pre-assigned ID to use
        include_beats: Whether to include beats in output (CRUD mode)
        beat_count: Number of beats to generate (CRUD mode, if include_beats)
        style: StyleOutput for narrative style context (from create pipeline)
        beat_slots: Pre-assigned beat slots (create pipeline mode)
        previous_scene_summaries: Recent scene summaries for continuity
        position_in_story: Scene position in narrative (0-indexed)
        total_scenes: Total scenes in narrative
        position_label: Position descriptor ('early', 'middle', 'late', 'climax')

    Returns:
        System prompt for scene generation
    """
    # Determine if we're in create mode (beat_slots provided)
    use_beat_slots = beat_slots is not None and len(beat_slots) > 0
    effective_beat_count = len(beat_slots) if beat_slots else beat_count
    effective_include_beats = use_beat_slots or include_beats

    purpose = "Create a scene for a story."
    if effective_include_beats:
        purpose += f" Include {effective_beat_count} beats."

    # Build schema
    id_line = f'  "id": "{assigned_id}",' if assigned_id else '  "id": "lowercase-with-hyphens",'

    # Build characters list for schema
    chars = available_characters or []
    char_ids_example = ", ".join(f'"{c.id}"' for c in chars[:2]) if chars else '"character-id"'

    # Build location example
    locs = available_locations or []
    location_ids = [loc.id for loc in locs if loc.type == "location"]
    location_example = location_ids[0] if location_ids else "location-id"

    schema_lines = [
        "{",
        f"{id_line}",
        '  "summary": "2-3 sentences describing what happens",',
        '  "goal": "What protagonist wants to achieve",',
        '  "conflict": "Obstacle or tension",',
        '  "outcome": "How scene resolves",',
        f'  "characters": [{char_ids_example}],',
        f'  "location": "{location_example}",',
        '  "time": "time of day"',
    ]

    if use_beat_slots and beat_slots:
        # Build beat examples from actual beat slots
        beat_examples = ",\n    ".join(
            f'{{"id": "{b.id}", "kind": "{b.kind}", "summary": "Beat action summary"}}'
            for b in beat_slots[:2]
        )
        if len(beat_slots) > 2:
            beat_examples += ",\n    ..."
        schema_lines.append(f'  "beats": [\n    {beat_examples}\n  ]')
    elif include_beats:
        schema_lines.append('  "beats": [{"id": "beat-id", "kind": "action", "summary": "..."}]')

    schema_lines.append("}")
    schema = "\n".join(schema_lines)

    sections: dict[str, str] = {}

    if assigned_id:
        sections["Assigned ID"] = f'"{assigned_id}" - Use this exact ID in your output.'

    if language:
        sections["Language"] = f"Generate all text content in {language}."

    if premise:
        sections["Story Premise"] = premise

    if chapter_context:
        sections["Chapter Context"] = chapter_context

    # Add position context (for create pipeline)
    if position_in_story is not None and total_scenes:
        label = position_label or "middle"
        sections["Story Position"] = f"Scene {position_in_story + 1} of {total_scenes} ({label})"

    # Add previous scene summaries for continuity
    if previous_scene_summaries:
        recent = previous_scene_summaries[-3:]  # Last 3 for context
        sections["Previous Scenes"] = "\n".join(f"- {s}" for s in recent)

    # Add style hint if provided (from create pipeline)
    style_hint = _format_style_hint(style)
    if style_hint:
        sections["Style"] = style_hint

    if chars:
        sections["Available Characters"] = _format_existing_characters(chars)
        valid_char_ids = ", ".join(c.id for c in chars)
        sections["Valid Character IDs"] = valid_char_ids

    if locs:
        sections["Available World Facts"] = _format_existing_world_facts(locs)
        if location_ids:
            sections["Valid Location IDs"] = ", ".join(location_ids)

    existing = existing_scenes or []
    if existing and not previous_scene_summaries:
        # Only show existing scenes if we don't have previous summaries
        sections["Existing Scenes (avoid duplicating)"] = _format_existing_scenes(existing)

    # Add beat slots list (for create pipeline)
    if use_beat_slots and beat_slots:
        beat_list = "\n".join(
            f"- {b.id}: {b.kind}" + (" [REQUIRED]" if b.required else "")
            for b in beat_slots
        )
        sections["Required Beats"] = beat_list

    if guidance:
        sections["User Guidance"] = guidance

    sections["Output Schema (JSON)"] = schema

    # Build notes based on mode
    notes_lines = [
        "Create a scene that advances the plot or develops characters.",
        "Use ONLY valid character and location IDs from above.",
    ]
    if use_beat_slots and beat_slots:
        notes_lines.append(f"Generate EXACTLY {len(beat_slots)} beats with the IDs listed above.")
        notes_lines.append("Use the exact beat IDs provided - do not modify them.")
    elif include_beats:
        notes_lines.append(f"Generate exactly {beat_count} beats.")

    sections["Notes"] = " ".join(notes_lines)

    guidelines = _format_guidelines()
    if assigned_id:
        guidelines.insert(1, "CRITICAL: Use the Assigned ID exactly - do not modify it.")
    if use_beat_slots:
        guidelines.insert(2, "CRITICAL: Use the exact beat IDs provided - do not modify them.")

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


# =============================================================================
# Beat Prompt
# =============================================================================


def build_beat_prompt(
    scene_id: str,
    scene_summary: str | None = None,
    scene_characters: list[Character] | None = None,
    existing_beats: list[Beat] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
) -> str:
    """Build prompt for beat generation.

    Args:
        scene_id: ID of the parent scene
        scene_summary: Summary of the scene
        scene_characters: Characters in this scene
        existing_beats: Beats already in the scene
        guidance: User-provided guidance text
        language: Language code for content generation
        assigned_id: Pre-assigned ID to use

    Returns:
        System prompt for beat generation
    """
    purpose = f"Create a beat (story moment) for scene '{scene_id}'."

    # Build schema
    id_line = f'  "id": "{assigned_id}",' if assigned_id else '  "id": "lowercase-with-hyphens",'

    schema = (
        "{\n"
        f"{id_line}\n"
        '  "kind": "action | dialogue | revelation | decision | transition | setup | turn | '
        'escalation | resolution | bridge | complication",\n'
        '  "summary": "1-2 sentences describing what happens",\n'
        '  "goal": "What POV character wants (optional)",\n'
        '  "conflict": "Obstacle or tension (optional)",\n'
        '  "outcome": "How beat resolves (optional)"\n'
        "}"
    )

    sections: dict[str, str] = {}

    if assigned_id:
        sections["Assigned ID"] = f'"{assigned_id}" - Use this exact ID in your output.'

    if language:
        sections["Language"] = f"Generate all text content in {language}."

    sections["Scene"] = scene_id
    if scene_summary:
        sections["Scene Summary"] = scene_summary

    chars = scene_characters or []
    if chars:
        sections["Characters in Scene"] = _format_existing_characters(chars)

    existing = existing_beats or []
    if existing:
        sections["Existing Beats (don't duplicate)"] = _format_existing_beats(existing)

    if guidance:
        sections["User Guidance"] = guidance

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Create a beat that advances the scene's narrative. "
        "Involves the characters present. "
        "Keep summary to 1-2 sentences of concrete action."
    )

    guidelines = _format_guidelines()
    if assigned_id:
        guidelines.insert(1, "CRITICAL: Use the Assigned ID exactly - do not modify it.")

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


# =============================================================================
# Fragment Prompt (Micro-prose)
# =============================================================================


def build_fragment_prompt(
    premise: str | None = None,
    existing_fragments: list[Fragment] | None = None,
    position: int | None = None,
    total_fragments: int | None = None,
    previous_content: list[str] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    style: StyleOutput | None = None,
) -> str:
    """Build prompt for fragment generation (micro-prose format).

    Args:
        premise: Story premise for context
        existing_fragments: Fragments already in project
        position: Position in sequence (0-indexed)
        total_fragments: Total number of fragments
        previous_content: Content of previous fragments for continuity
        guidance: User-provided guidance text
        language: Language code for content generation
        assigned_id: Pre-assigned ID to use
        style: StyleOutput for narrative style context (from create pipeline)

    Returns:
        System prompt for fragment generation
    """
    purpose = "Create a flash fiction fragment."
    if position is not None and total_fragments:
        purpose = f"Generate fragment {position + 1} of {total_fragments}."

    # Build schema
    id_line = f'  "id": "{assigned_id}",' if assigned_id else '  "id": "lowercase-with-hyphens",'

    schema = (
        "{\n"
        f"{id_line}\n"
        '  "content": "The prose content (1-3 paragraphs)",\n'
        '  "target_words": 100,\n'
        '  "notes": "Optional notes about this fragment"\n'
        "}"
    )

    sections: dict[str, str] = {}

    if assigned_id:
        sections["Assigned ID"] = f'"{assigned_id}" - Use this exact ID in your output.'

    if language:
        sections["Language"] = f"Generate all text content in {language}."

    if premise:
        sections["Premise"] = premise

    # Add style hint if provided (from create pipeline)
    style_hint = _format_style_hint(style)
    if style_hint:
        sections["Style"] = style_hint

    if position is not None and total_fragments:
        sections["Position"] = f"Fragment {position + 1} of {total_fragments}"

    if previous_content:
        sections["Previous Fragments"] = "\n".join(f"- {c}" for c in previous_content[-3:])

    existing = existing_fragments or []
    if existing and not previous_content:
        sections["Existing Fragments"] = _format_existing_fragments(existing)

    if guidance:
        sections["User Guidance"] = guidance

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Create evocative flash fiction. "
        "Each fragment should stand alone yet connect to the whole. "
        "Keep prose atmospheric and focused."
    )

    guidelines = _format_guidelines()
    if assigned_id:
        guidelines.insert(1, "CRITICAL: Use the Assigned ID exactly - do not modify it.")

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


# =============================================================================
# Stanza Prompt (Poem)
# =============================================================================


def build_stanza_prompt(
    premise: str | None = None,
    existing_stanzas: list[Stanza] | None = None,
    position: int | None = None,
    total_stanzas: int | None = None,
    target_line_count: int = 4,
    poem_form: str | None = None,
    previous_stanza_texts: list[str] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    style: StyleOutput | None = None,
) -> str:
    """Build prompt for stanza generation (poem format).

    Args:
        premise: Poem premise/theme for context
        existing_stanzas: Stanzas already in poem
        position: Position in sequence (0-indexed)
        total_stanzas: Total number of stanzas
        target_line_count: Number of lines for this stanza
        poem_form: Form of the poem (sonnet, haiku, etc.)
        previous_stanza_texts: Text of previous stanzas for continuity
        guidance: User-provided guidance text
        language: Language code for content generation
        assigned_id: Pre-assigned ID to use
        style: StyleOutput for narrative style context (from create pipeline)

    Returns:
        System prompt for stanza generation
    """
    purpose = "Create a stanza for a poem."
    if position is not None and total_stanzas:
        purpose = f"Generate stanza {position + 1} of {total_stanzas}."
    purpose += f" Create exactly {target_line_count} lines."

    # Build schema
    id_line = f'  "id": "{assigned_id}",' if assigned_id else '  "id": "lowercase-with-hyphens",'

    schema = (
        "{\n"
        f"{id_line}\n"
        f'  "lines": ["line 1", "line 2", ...],  // Exactly {target_line_count} lines\n'
        '  "meter": "optional meter description",\n'
        '  "rhyme_scheme": "optional rhyme pattern"\n'
        "}"
    )

    sections: dict[str, str] = {}

    if assigned_id:
        sections["Assigned ID"] = f'"{assigned_id}" - Use this exact ID in your output.'

    if language:
        sections["Language"] = f"Generate all text content in {language}."

    if premise:
        sections["Premise"] = premise

    # Add style hint if provided (from create pipeline)
    style_hint = _format_style_hint(style)
    if style_hint:
        sections["Style"] = style_hint

    if position is not None and total_stanzas:
        sections["Position"] = f"Stanza {position + 1} of {total_stanzas}"

    sections["Line Count"] = f"Exactly {target_line_count} lines required"

    if poem_form:
        sections["Poem Form"] = poem_form

    if previous_stanza_texts:
        sections["Previous Stanzas"] = "\n---\n".join(previous_stanza_texts[-3:])

    existing = existing_stanzas or []
    if existing and not previous_stanza_texts:
        sections["Existing Stanzas"] = _format_existing_stanzas(existing)

    if guidance:
        sections["User Guidance"] = guidance

    sections["Output Schema (JSON)"] = schema
    sections["CRITICAL Notes"] = (
        f"- Generate EXACTLY {target_line_count} lines in the 'lines' array\n"
        "- Each line should be a complete poetic line\n"
        "- Maintain consistent voice and rhythm"
    )

    guidelines = _format_guidelines()
    if assigned_id:
        guidelines.insert(1, "CRITICAL: Use the Assigned ID exactly - do not modify it.")

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


# =============================================================================
# Chapter Prompt
# =============================================================================


def build_chapter_prompt(
    premise: str | None = None,
    existing_chapters: list[Chapter] | None = None,
    existing_scenes: list[Scene] | None = None,
    guidance: str | None = None,
    language: str | None = None,
    assigned_id: str | None = None,
    style: StyleOutput | None = None,
    chapter_index: int | None = None,
    total_chapters: int | None = None,
    scene_count: int | None = None,
    previous_chapter_summaries: list[str] | None = None,
    title_requirement_str: str | None = None,
) -> str:
    """Build prompt for chapter generation.

    This prompt supports two modes:
    - CRUD mode: Basic chapter generation without title diversity
    - Create mode: Chapter generation with title diversity requirements

    Args:
        premise: Story premise for context
        existing_chapters: Chapters already in project (to avoid duplicates)
        existing_scenes: Scenes in project (for context)
        guidance: User-provided guidance text
        language: Language code for content generation
        assigned_id: Pre-assigned ID to use (for create pipeline)
        style: StyleOutput for narrative style context (from create pipeline)
        chapter_index: 0-based chapter position (create pipeline)
        total_chapters: Total number of chapters (create pipeline)
        scene_count: Number of scenes in this chapter (create pipeline)
        previous_chapter_summaries: Recent chapter summaries for continuity
        title_requirement_str: Formatted title requirement (from TitleRequirement.format_for_prompt)

    Returns:
        System prompt for chapter generation
    """
    # Build purpose with position context if available
    if chapter_index is not None and total_chapters:
        purpose = f"Create a summary for chapter {chapter_index + 1} of {total_chapters}. "
        purpose += "Generate a title and brief summary that establishes this chapter's role in the narrative."
    else:
        purpose = "Create a chapter for a story."

    # Build schema
    id_line = f'  "id": "{assigned_id}",' if assigned_id else '  "id": "lowercase-with-hyphens",'

    schema = (
        "{\n"
        f"{id_line}\n"
        '  "title": "Short evocative chapter title",\n'
        '  "summary": "2-3 sentences describing the chapter\'s arc"\n'
        "}"
    )

    sections: dict[str, str] = {}

    if assigned_id:
        sections["Assigned ID"] = f'"{assigned_id}" - Use this exact ID in your output.'

    if language:
        sections["Language"] = f"Generate all text content in {language}."

    # Add position context for create pipeline
    if chapter_index is not None and total_chapters:
        # Determine chapter position description
        if chapter_index == 0:
            position_desc = "Opening chapter - establishes setting, introduces conflict"
        elif chapter_index == total_chapters - 1:
            position_desc = "Final chapter - resolution and denouement"
        elif chapter_index < total_chapters // 3:
            position_desc = "Early chapter - building tension, developing characters"
        elif chapter_index < 2 * total_chapters // 3:
            position_desc = "Middle chapter - complications, escalation"
        else:
            position_desc = "Late chapter - crisis, climax approaching"

        sections["Chapter Position"] = f"{chapter_index + 1} of {total_chapters} ({position_desc})"

    if scene_count is not None:
        sections["Scenes in Chapter"] = f"{scene_count} scenes planned"

    if premise:
        sections["Story Premise"] = premise

    # Add style hint if provided (from create pipeline)
    style_hint = _format_style_hint(style)
    if style_hint:
        sections["Style"] = style_hint

    # Add previous chapter summaries for continuity
    if previous_chapter_summaries:
        recent = previous_chapter_summaries[-3:]
        sections["Previous Chapters"] = "\n".join(f"- {summary}" for summary in recent)

    existing = existing_chapters or []
    if existing and not previous_chapter_summaries:
        # Only show existing chapters if we don't have previous summaries
        sections["Existing Chapters (avoid duplicating)"] = _format_existing_chapters(existing)

    scenes = existing_scenes or []
    if scenes:
        sections["Available Scenes"] = _format_existing_scenes(scenes)

    # Add title requirement for create pipeline
    if title_requirement_str:
        sections["Title Requirements"] = title_requirement_str

    if guidance:
        sections["User Guidance"] = guidance

    sections["Output Schema (JSON)"] = schema

    # Build notes
    notes_lines = [
        "Create a chapter that advances the overall plot arc.",
        "The chapter should fit naturally after existing chapters.",
        "Do NOT include scene_ids - scenes are assigned separately.",
    ]
    if title_requirement_str:
        notes_lines.append("CRITICAL: Your title MUST follow the Required Structure above exactly.")

    sections["Notes"] = " ".join(notes_lines)

    guidelines = _format_guidelines()
    if assigned_id:
        guidelines.insert(1, "CRITICAL: Use the Assigned ID exactly - do not modify it.")
    if title_requirement_str:
        guidelines.insert(2, "CRITICAL: Follow the Title Requirements exactly - failure to do so will be rejected.")

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


__all__ = [
    "BeatSlotInfo",
    "build_character_prompt",
    "build_world_fact_prompt",
    "build_scene_prompt",
    "build_beat_prompt",
    "build_fragment_prompt",
    "build_stanza_prompt",
    "build_chapter_prompt",
]
