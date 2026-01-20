"""Prompt builders for create-from-idea generation."""

from __future__ import annotations

from fabulae.features.create.schemas import (
    OutlineContentOutput,
    StyleOutput,
)
from fabulae.features.create.variation import ProjectVariation
from fabulae.models import Character, StoryShape, World
from fabulae.prompts import build_system_prompt, format_sections, serialize_for_prompt


def _format_guidelines() -> list[str]:
    """Format standard guidelines for LLM prompts.

    These guidelines are designed to be clear and actionable,
    especially for smaller LLMs that may struggle with implicit requirements.
    """
    return [
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text before or after.",
        "CRITICAL: When an 'Assigned ID' is provided, use that EXACT ID in your output. Do not modify it.",
        "Match the schema exactly; omit optional fields you do not use, but include all required fields.",
        "IDs must be lowercase ASCII with hyphens only (a-z, 0-9, hyphen). Example: 'character-01', 'scene-02'.",
        "Ensure IDs are unique within each list.",
        "When counts are specified (beat_count, line_count), your output MUST have exactly that many items.",
        "Keep outputs concise and aligned to the requested format.",
    ]


def _format_example(title: str, example: str) -> str:
    return format_sections({title: example.strip()})


def _format_count_range(label: str, count_range: tuple[int, int]) -> str:
    return f"{label} (target): {count_range[0]}-{count_range[1]}"


def build_style_prompt(format_name: str) -> str:
    purpose = (
        "Define narrative style guidance for a Fabulae project. Provide language as an ISO 639-1 code when possible."
    )
    schema = (
        "{\n"
        '  "language": "en",\n'
        '  "pov": "third",\n'
        '  "tense": "past",\n'
        '  "voice": "observant",\n'
        '  "register": "literary",\n'
        '  "constraints": ["avoid purple prose"]\n'
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Notes": "Focus on voice, POV, tense, and register that fit the format.",
        "Output Schema (JSON)": schema,
    }
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_premise_expansion_prompt(format_name: str, expected_language: str | None = None) -> str:
    """Build a prompt for expanding a simple idea into a richer narrative premise.

    Args:
        format_name: The narrative format (novel, novella, short-story, etc.).
        expected_language: Optional ISO 639-1 language code for the expected output language.

    Returns:
        The system prompt for premise expansion.
    """
    purpose = (
        "Expand a simple story idea into a compelling narrative premise with a title. "
        "The premise should be 2-4 sentences that capture the core conflict, setting, and emotional hook."
    )
    schema = (
        "{\n"
        '  "title": "A compelling, evocative title for the story.",\n'
        '  "premise": "A 2-4 sentence narrative premise that expands the original idea. '
        "Captures the core conflict, the setting, and what's emotionally at stake for the main character.\""
        "\n}"
    )
    notes_lines = [
        "Create a title that captures the essence or mood of the story.",
        "The premise should feel more developed than the original idea.",
        "Focus on: What happens? Who is affected? What's at stake?",
        "Avoid spoiling the ending or over-explaining the plot.",
        "Keep it concise but evocative - aim for 2-4 sentences.",
    ]

    sections: dict[str, str] = {
        "Format": format_name,
        "Notes": "\n".join(notes_lines),
        "Output Schema (JSON)": schema,
    }

    if expected_language:
        sections["Expected Language"] = f"ISO 639-1: {expected_language}"

    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_character_plan_prompt(
    format_name: str,
    style_hint: str | None,
    count_range: tuple[int, int],
) -> str:
    purpose = "Generate a cast list with minimal details. Use the count range to decide how many characters to include."
    schema = (
        "{\n"
        '  "characters": [\n'
        '    {"id": "character-01", "name": "Ari", "role": "protagonist", "purpose": "drives the investigation"}\n'
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Count Range": _format_count_range("Characters", count_range),
        "Output Schema (JSON)": schema,
        "Notes": "Keep purpose short; avoid full biographies.",
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_character_prompt(
    format_name: str,
    style_hint: str | None,
    existing_summary: str,
    assigned_id: str,
) -> str:
    purpose = "Expand a single character into the full schema. Do not repeat traits or roles already used."
    schema = (
        "{\n"
        '  "id": "character-01",\n'
        '  "name": "Ari",\n'
        '  "role": "protagonist",\n'
        '  "desire": "solve the mystery",\n'
        '  "need": "trust others",\n'
        '  "flaw": "impatient",\n'
        '  "secret": "hiding their past",\n'
        '  "traits": ["curious", "sharp"]\n'
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Assigned ID": (
            f'"{assigned_id}" - Use this ID exactly in your output. Do not change or generate a different ID.'
        ),
        "Existing Characters": existing_summary or "None yet.",
        "Output Schema (JSON)": schema,
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_world_plan_prompt(
    format_name: str,
    style_hint: str | None,
    count_range: tuple[int, int],
) -> str:
    purpose = (
        "Draft world metadata and a list of world facts. Include at least one location if scenes will need locations."
    )
    schema = (
        "{\n"
        '  "setting": "Coastal research town",\n'
        '  "time_period": "near future",\n'
        '  "tone": "moody",\n'
        '  "motifs": ["fog", "radio static"],\n'
        '  "facts": [\n'
        '    {"id": "location-01", "type": "location", "name": "Harbor Lab", "purpose": "main lab hub"}\n'
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Count Range": _format_count_range("World facts", count_range),
        "Output Schema (JSON)": schema,
        "Notes": "Keep each purpose short; do not list full fact bullets yet.",
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_world_fact_prompt(
    format_name: str,
    style_hint: str | None,
    existing_summary: str,
    assigned_id: str,
) -> str:
    purpose = "Expand a single world fact into the full schema. Use concise, non-repetitive facts."
    schema = (
        "{\n"
        '  "id": "location-01",\n'
        '  "type": "location",\n'
        '  "name": "Harbor Lab",\n'
        '  "facts": ["restricted access", "scent of ozone"]\n'
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Assigned ID": (
            f'"{assigned_id}" - Use this ID exactly in your output. Do not change or generate a different ID.'
        ),
        "Existing World Facts": existing_summary or "None yet.",
        "Output Schema (JSON)": schema,
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_plot_outline_prompt(
    format_name: str,
    style_hint: str | None,
    count_ranges: dict[str, tuple[int, int]],
    beats_per_scene: tuple[int, int],
) -> str:
    purpose = (
        "Generate a structured plot outline with chapters, scenes, and beat counts. "
        "Keep scene summaries tight and ensure chapter/scene IDs align."
    )
    schema = (
        "{\n"
        f'  "format": "{format_name}",\n'
        '  "title": "Working Title",\n'
        '  "premise": "A concise premise.",\n'
        '  "themes": ["trust", "perception"],\n'
        '  "hook": {"line": "A hook line."},\n'
        '  "stakes": {"external": "External stakes", "internal": "Internal stakes"},\n'
        '  "chapters": [{"id": "chapter-01", "title": "Opening", "scene_ids": ["scene-01", "scene-02"]}],\n'
        '  "scenes": [\n'
        "    {\n"
        '      "id": "scene-01",\n'
        '      "summary": "Opening scene summary.",\n'
        '      "goal": "Scene goal",\n'
        '      "conflict": "Scene conflict",\n'
        '      "outcome": "Scene outcome",\n'
        '      "beat_count": 3\n'
        "    },\n"
        "    {\n"
        '      "id": "scene-02",\n'
        '      "summary": "Second scene summary.",\n'
        '      "goal": "Scene goal",\n'
        '      "conflict": "Scene conflict",\n'
        '      "outcome": "Scene outcome",\n'
        '      "beat_count": 3\n'
        "    }\n"
        "  ],\n"
        '  "scene_ids": null\n'
        "}"
    )
    count_lines = [
        _format_count_range("Chapters", count_ranges["chapters"]),
        _format_count_range("Scenes", count_ranges["scenes"]),
        _format_count_range("Total beats", count_ranges["beats"]),
        _format_count_range("Beats per scene", beats_per_scene),
    ]
    sections: dict[str, str] = {
        "Format": format_name,
        "Count Targets": "\n".join(count_lines),
        "Output Schema (JSON)": schema,
        "Notes": "Scene beat_count drives later beat generation; keep it within the range.",
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_scene_prompt(
    format_name: str,
    style_hint: str | None,
    available_characters: str,
    available_locations: str,
    existing_summaries: str,
    assigned_id: str,
) -> str:
    purpose = (
        "Expand a single scene into full details and beats. Use only the provided IDs for characters and locations."
    )
    schema = (
        "{\n"
        '  "id": "scene-01",\n'
        '  "location": "location-01",\n'
        '  "time": "night",\n'
        '  "characters": ["character-01"],\n'
        '  "world_fact_ids": ["location-01"],\n'
        '  "summary": "Expanded scene summary.",\n'
        '  "goal": "Scene goal",\n'
        '  "conflict": "Scene conflict",\n'
        '  "outcome": "Scene outcome",\n'
        '  "beats": [\n'
        '    {"id": "scene-01-beat-01", "kind": "setup", "summary": "Beat summary"},\n'
        '    {"id": "scene-01-beat-02", "kind": "turn", "summary": "Beat summary"}\n'
        "  ]\n"
        "}"
    )
    # Build notes with explicit beat guidance
    notes_lines = [
        "CRITICAL: The number of beats MUST equal the beat_count from the Scene Outline.",
        "Beat IDs format: {scene_id}-beat-{nn} (e.g., 'scene-01-beat-01', 'scene-01-beat-02').",
        "Valid beat kinds: setup, turn, escalation, resolution, bridge, complication, reaction.",
        "If a Beat Template is provided, keep required beat kinds in the same positions.",
        "Only use character/location IDs from the Available lists. Do not invent new IDs.",
    ]

    sections: dict[str, str] = {
        "Format": format_name,
        "Assigned ID": (
            f'"{assigned_id}" - Use this ID exactly in your output. Do not change or generate a different ID.'
        ),
        "Available Characters": available_characters or "None",
        "Available Locations": available_locations or "None",
        "Existing Scene Summaries": existing_summaries or "None yet.",
        "IMPORTANT Notes": "\n".join(notes_lines),
        "Output Schema (JSON)": schema,
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_fragment_plan_prompt(
    format_name: str,
    style_hint: str | None,
    count_range: tuple[int, int],
) -> str:
    purpose = "Outline micro-prose fragments with IDs and intent."
    schema = (
        "{\n"
        '  "title": "Working Title",\n'
        '  "premise": "A concise premise.",\n'
        '  "themes": ["memory", "loss"],\n'
        '  "fragments": [\n'
        '    {"id": "fragment-01", "target_words": 120, "intent": "evoke the core memory"}\n'
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Count Range": _format_count_range("Fragments", count_range),
        "Output Schema (JSON)": schema,
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_fragment_prompt(
    format_name: str,
    style_hint: str | None,
    existing_summary: str,
    assigned_id: str,
) -> str:
    purpose = "Write a single micro-prose fragment matching the intent."
    schema = (
        "{\n"
        '  "id": "fragment-01",\n'
        '  "content": "A concise fragment.",\n'
        '  "target_words": 120,\n'
        '  "notes": "Optional notes."\n'
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Assigned ID": (
            f'"{assigned_id}" - Use this ID exactly in your output. Do not change or generate a different ID.'
        ),
        "Existing Fragments": existing_summary or "None yet.",
        "Output Schema (JSON)": schema,
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_poem_plan_prompt(
    format_name: str,
    style_hint: str | None,
    stanza_range: tuple[int, int],
    line_range: tuple[int, int],
) -> str:
    purpose = "Outline a poem structure with stanza IDs and line counts."
    schema = (
        "{\n"
        '  "title": "Working Title",\n'
        '  "premise": "A concise premise.",\n'
        '  "themes": ["light", "silence"],\n'
        '  "poem_form": "free verse",\n'
        '  "poem_meter": null,\n'
        '  "poem_rhyme_scheme": null,\n'
        '  "stanzas": [\n'
        '    {"id": "stanza-01", "line_count": 4, "intent": "introduce the image"}\n'
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Count Targets": "\n".join(
            [
                _format_count_range("Stanzas", stanza_range),
                _format_count_range("Lines total", line_range),
            ]
        ),
        "Output Schema (JSON)": schema,
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_stanza_prompt(
    format_name: str,
    style_hint: str | None,
    existing_summary: str,
    assigned_id: str,
) -> str:
    purpose = "Write a single stanza with the requested number of lines."
    schema = (
        "{\n"
        '  "id": "stanza-01",\n'
        '  "lines": ["Line one.", "Line two.", "Line three.", "Line four."],\n'
        '  "meter": null,\n'
        '  "rhyme_scheme": null\n'
        "}"
    )
    notes_lines = [
        "CRITICAL: The 'lines' array MUST have exactly the line_count specified in the Stanza Plan.",
        "Each line is a single string in the array.",
        "Use the Assigned ID exactly - do not modify it.",
    ]

    sections: dict[str, str] = {
        "Format": format_name,
        "Assigned ID": (
            f'"{assigned_id}" - Use this ID exactly in your output. Do not change or generate a different ID.'
        ),
        "Existing Stanzas": existing_summary or "None yet.",
        "IMPORTANT Notes": "\n".join(notes_lines),
        "Output Schema (JSON)": schema,
    }
    if style_hint:
        sections["Style"] = style_hint
    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def _format_enrichment_schema() -> str:
    """Format the EnrichmentOutput schema documentation for the prompt."""
    schema = (
        "{\n"
        '  "new_characters": [\n'
        "    {\n"
        '      "id": "character-secondary-01",\n'
        '      "name": "Name",\n'
        '      "role": "supporting",\n'
        '      "traits": ["trait1", "trait2"]\n'
        "    }\n"
        "  ],\n"
        '  "new_locations": [\n'
        "    {\n"
        '      "id": "location-new-01",\n'
        '      "type": "location",\n'
        '      "name": "Location Name",\n'
        '      "facts": ["fact1", "fact2"]\n'
        "    }\n"
        "  ],\n"
        '  "new_world_facts": [\n'
        "    {\n"
        '      "id": "world-fact-01",\n'
        '      "type": "culture",\n'
        '      "name": "Fact Name",\n'
        '      "facts": ["detail1", "detail2"]\n'
        "    }\n"
        "  ],\n"
        '  "subplot_additions": [\n'
        "    {\n"
        '      "description": "A subplot to weave into the narrative.",\n'
        '      "involved_characters": ["character-01", "character-secondary-01"],\n'
        '      "scenes_to_modify": ["scene-01", "scene-03"]\n'
        "    }\n"
        "  ],\n"
        '  "foreshadowing_elements": [\n'
        "    {\n"
        '      "description": "A detail to plant early and pay off later.",\n'
        '      "setup_scene": "scene-01",\n'
        '      "payoff_scene": "scene-05"\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    return schema


def build_enrichment_prompt(
    idea: str,
    format_name: str,
    style: StyleOutput,
    characters: list[Character],
    world: World,
    outline: OutlineContentOutput,
    variation: ProjectVariation | None = None,
    shape: StoryShape | None = None,
) -> str:
    """Build a prompt for the enrichment pass.

    The enrichment pass happens AFTER pass 1 (style, character plan, world plan, plot outline)
    but BEFORE scene expansion. Its purpose is to add depth without changing structure:
    - Add secondary/minor characters that emerged from the outline
    - Add additional world-building elements suggested by the outline
    - Seed subplots based on variation decisions
    - Add foreshadowing elements

    Args:
        idea: The original story idea.
        format_name: The narrative format (novel, novella, short-story, etc.).
        style: The style output from pass 1.
        characters: The existing characters from pass 1.
        world: The world data from pass 1.
        outline: The plot outline with chapters and scenes.
        variation: Optional variation decisions that may contain subplot seeds.
        shape: Optional story shape for additional guidance.

    Returns:
        The enrichment prompt string.
    """
    purpose = (
        "Analyze the narrative outline and suggest enrichments that add depth without "
        "changing the existing structure. Focus on secondary characters, additional "
        "locations, and foreshadowing opportunities implied by the outline."
    )

    guidelines = _format_guidelines() + [
        "Do NOT change the existing structure (chapter count, scene count, beat count).",
        "Focus on adding depth, not changing the plot.",
        "New characters should support existing scenes, not create new ones.",
        "Foreshadowing must reference existing scene IDs from the outline.",
        "All new entity IDs must be lowercase-hyphenated and unique from existing IDs.",
    ]

    # Build context sections
    context_parts: dict[str, str] = {
        "Original Idea": idea,
        "Format": format_name,
    }

    # Style context
    style_dict = style.model_dump(exclude_none=True, by_alias=True)
    if style_dict:
        context_parts["Style"] = serialize_for_prompt(style_dict)

    # Existing characters
    if characters:
        chars_data = [char.model_dump(exclude_none=True) for char in characters]
        context_parts["Existing Characters"] = serialize_for_prompt(chars_data)
    else:
        context_parts["Existing Characters"] = "None yet."

    # Existing world/locations
    if world:
        world_data = world.model_dump(exclude_none=True)
        context_parts["Existing World"] = serialize_for_prompt(world_data)
    else:
        context_parts["Existing World"] = "None yet."

    # Plot outline
    outline_data = outline.model_dump(exclude_none=True)
    context_parts["Plot Outline"] = serialize_for_prompt(outline_data)

    # Variation subplot seeds if provided
    if variation and variation.subplot_seeds:
        context_parts["Subplot Seeds from Variation"] = serialize_for_prompt(variation.subplot_seeds)
        context_parts["Subplot Seed Instructions"] = (
            "Develop the provided subplot seeds into concrete subplot additions. "
            "Each seed should become a subplot with involved characters and target scenes."
        )

    # Story shape guidance if provided
    if shape:
        shape_data = {
            "id": shape.id,
            "name": shape.name,
            "themes": shape.themes,
            "motifs": shape.motifs,
            "tone": shape.tone,
        }
        context_parts["Story Shape Guidance"] = serialize_for_prompt({k: v for k, v in shape_data.items() if v})

    # Instructions section
    instructions = (
        "Analyze the outline for:\n"
        "1. Implicit secondary characters mentioned but not yet defined as entities.\n"
        "2. Locations or settings implied by scenes but not yet created as world facts.\n"
        "3. Opportunities to add foreshadowing elements that connect early and late scenes.\n"
        "4. Additional world-building elements that would enrich the narrative.\n"
    )
    if variation and variation.subplot_seeds:
        instructions += "5. Transform the subplot seeds into concrete subplot additions.\n"

    context_parts["Instructions"] = instructions

    # Output schema
    schema = _format_enrichment_schema()

    sections: dict[str, str] = {
        "Context": format_sections(context_parts),
        "Output Schema (JSON)": schema,
        "Constraints": (
            "- Return valid JSON only (no markdown, no extra text).\n"
            "- Do NOT change existing structure (chapter count, scene count).\n"
            "- New characters must have unique IDs not matching existing characters.\n"
            "- New locations/facts must have unique IDs not matching existing world facts.\n"
            "- Foreshadowing setup_scene and payoff_scene must be valid scene IDs from outline.\n"
            "- Subplot scenes_to_modify must reference valid scene IDs from outline."
        ),
    }

    return (
        build_system_prompt(purpose, guidelines)
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


def build_outline_only_prompt(
    format_name: str,
    style: StyleOutput,
    count_ranges: dict[str, tuple[int, int]],
) -> str:
    """Build prompt for outline-only generation (no --full flag).

    This generates a high-level story outline with:
    - Title and expanded premise
    - Chapter structure with titles and summaries
    - Scene sketches with titles, summaries, and character assignments
    - Character sketches with name, role, and brief description
    - Location list (names only)

    Does NOT generate:
    - Detailed character attributes (desire, need, flaw, secret, traits)
    - Beats for scenes
    - Detailed world facts

    Args:
        format_name: The narrative format (novel, novella, short-story).
        style: The style output for voice and tone guidance.
        count_ranges: Dictionary with count ranges for chapters, scenes, characters, locations.

    Returns:
        The system prompt for outline-only generation.
    """
    purpose = (
        "Create a story outline from the idea provided. This is an OUTLINE only - "
        "generate high-level structure without detailed beats, character backstories, or world facts. "
        "Keep it structural and concise."
    )

    schema = (
        "{\n"
        '  "title": "Story Title",\n'
        '  "premise": "A 2-4 sentence narrative premise expanding on the original idea.",\n'
        '  "chapters": [\n'
        "    {\n"
        '      "id": "chapter-01",\n'
        '      "title": "Chapter Title",\n'
        '      "summary": "2-3 sentence summary.",\n'
        '      "scene_ids": ["scene-01", "scene-02"]\n'
        "    }\n"
        "  ],\n"
        '  "scenes": [\n'
        "    {\n"
        '      "id": "scene-01",\n'
        '      "title": "Scene Title",\n'
        '      "summary": "1-2 sentence summary.",\n'
        '      "character_ids": ["character-01"]\n'
        "    }\n"
        "  ],\n"
        '  "characters": [\n'
        "    {\n"
        '      "id": "character-01",\n'
        '      "name": "Character Name",\n'
        '      "role": "protagonist",\n'
        '      "description": "One-line description."\n'
        "    }\n"
        "  ],\n"
        '  "locations": [\n'
        '    {"id": "location-01", "name": "Location Name"}\n'
        "  ]\n"
        "}"
    )

    # Build count target lines
    count_lines = []
    if "chapters" in count_ranges:
        count_lines.append(_format_count_range("Chapters", count_ranges["chapters"]))
    if "scenes" in count_ranges:
        count_lines.append(_format_count_range("Scenes", count_ranges["scenes"]))
    if "characters" in count_ranges:
        count_lines.append(_format_count_range("Characters", count_ranges["characters"]))
    if "locations" in count_ranges:
        count_lines.append(_format_count_range("Locations", count_ranges["locations"]))

    # Build style hint
    style_parts = []
    if style.pov:
        style_parts.append(f"POV: {style.pov}")
    if style.tense:
        style_parts.append(f"Tense: {style.tense}")
    if style.voice:
        style_parts.append(f"Voice: {style.voice}")
    if style.register_:
        style_parts.append(f"Register: {style.register_}")
    if style.language:
        style_parts.append(f"Language: {style.language}")
    style_hint = "; ".join(style_parts) if style_parts else "Not specified"

    notes_lines = [
        "This is an OUTLINE only - do not generate detailed beats or character backstories.",
        "Keep scene summaries to 1-2 sentences each.",
        "Keep character descriptions to one line each.",
        "Every scene must be assigned to exactly one chapter via scene_ids.",
        "Every scene must list at least one character in character_ids.",
        "All IDs must be lowercase-hyphenated and unique.",
    ]

    sections: dict[str, str] = {
        "Format": format_name,
        "Style": style_hint,
        "Count Targets": "\n".join(count_lines),
        "Notes": "\n".join(notes_lines),
        "Output Schema (JSON)": schema,
    }

    return (
        build_system_prompt(purpose, _format_guidelines())
        + "\n\n"
        + format_sections(sections)
        + "\n\n"
        + _format_example("Example Output", schema)
    )


__all__ = [
    "build_character_plan_prompt",
    "build_character_prompt",
    "build_enrichment_prompt",
    "build_fragment_plan_prompt",
    "build_fragment_prompt",
    "build_outline_only_prompt",
    "build_plot_outline_prompt",
    "build_poem_plan_prompt",
    "build_premise_expansion_prompt",
    "build_scene_prompt",
    "build_stanza_prompt",
    "build_style_prompt",
    "build_world_fact_prompt",
    "build_world_plan_prompt",
]
