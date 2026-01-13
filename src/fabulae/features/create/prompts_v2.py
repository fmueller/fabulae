"""Focused per-unit prompts for sequential generation.

These prompts are designed for generating one unit at a time with minimal context,
reducing LLM divergence and errors compared to batch generation.
"""

from __future__ import annotations

from fabulae.features.create.context import (
    ChapterContext,
    CharacterContext,
    FragmentContext,
    LocationContext,
    SceneContext,
    StanzaContext,
)
from fabulae.features.create.schemas import StyleOutput
from fabulae.prompts import build_system_prompt, format_sections


def _format_guidelines() -> list[str]:
    """Standard guidelines for all sequential prompts."""
    return [
        "CRITICAL: Return ONLY valid JSON. No markdown, no extra text.",
        "CRITICAL: Use the Assigned ID exactly - do not modify it.",
        "Match the schema exactly. Omit optional fields you don't use.",
        "IDs must be lowercase ASCII with hyphens (a-z, 0-9, hyphen).",
        "Keep outputs concise and focused on this single unit.",
    ]


def _format_style_hint(style: StyleOutput) -> str:
    """Format style information as a compact hint."""
    parts: list[str] = []
    if style.pov:
        parts.append(f"POV: {style.pov}")
    if style.tense:
        parts.append(f"Tense: {style.tense}")
    if style.voice:
        parts.append(f"Voice: {style.voice}")
    if style.register_:
        parts.append(f"Register: {style.register_}")
    return ", ".join(parts) if parts else "No specific style constraints."


def build_character_prompt_v2(context: CharacterContext) -> str:
    """Build a focused prompt for generating a single character.

    The prompt includes only:
    - Character slot requirements (role, needs)
    - Story premise for context
    - Style for tone guidance
    - Existing character names (to avoid duplicates)

    Args:
        context: CharacterContext with minimal required information

    Returns:
        Prompt string for generating one character
    """
    purpose = (
        f"Create a character for the role: {context.character_slot.role}. "
        "Generate a complete character that fits the story premise and fills the specified role."
    )

    schema = (
        "{\n"
        f'  "id": "{context.character_slot.id}",\n'
        '  "name": "Character Name",\n'
        f'  "role": "{context.character_slot.role}",\n'
        '  "desire": "What they consciously want (1 sentence)",\n'
        '  "need": "What they actually need (1 sentence)",\n'
        '  "flaw": "Key weakness (1-3 words)",\n'
        '  "secret": "Something hidden (1 sentence, optional)",\n'
        '  "traits": ["trait1", "trait2"]\n'
        "}"
    )

    sections: dict[str, str] = {
        "Assigned ID": (f'"{context.character_slot.id}" - Use this exact ID in your output.'),
        "Role": context.character_slot.role,
        "Story Premise": context.premise,
        "Style": _format_style_hint(context.style),
    }

    if context.character_slot.needs:
        sections["Character Needs"] = f"This character should: {context.character_slot.needs}"

    if context.existing_character_names:
        sections["Existing Characters"] = (
            f"Names already used (avoid these): {', '.join(context.existing_character_names)}"
        )

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Generate ONLY this character. "
        "Keep desire/need/flaw distinct - they should create internal conflict. "
        "Traits should be personality characteristics, not plot points."
    )

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


def build_location_prompt_v2(context: LocationContext) -> str:
    """Build a focused prompt for generating a single location.

    Args:
        context: LocationContext with minimal required information

    Returns:
        Prompt string for generating one location
    """
    purpose = (
        "Create a location/setting for the story. "
        "Generate a complete world fact of type 'location' with vivid, specific details."
    )

    schema = (
        "{\n"
        f'  "id": "{context.location_slot.id}",\n'
        '  "type": "location",\n'
        '  "name": "Location Name",\n'
        '  "facts": ["sensory detail 1", "atmosphere/mood", "distinctive feature"]\n'
        "}"
    )

    sections: dict[str, str] = {
        "Assigned ID": (f'"{context.location_slot.id}" - Use this exact ID in your output.'),
        "Story Premise": context.premise,
        "Style": _format_style_hint(context.style),
    }

    if context.location_slot.needs:
        sections["Location Needs"] = f"This location should: {context.location_slot.needs}"

    if context.existing_location_names:
        sections["Existing Locations"] = (
            f"Names already used (avoid these): {', '.join(context.existing_location_names)}"
        )

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Generate ONLY this location. "
        "Facts should be concrete, sensory details (sounds, smells, visuals, textures). "
        "Include 2-4 facts that make this place distinctive."
    )

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


def build_chapter_prompt_v2(context: ChapterContext) -> str:
    """Build a focused prompt for generating a single chapter summary.

    Args:
        context: ChapterContext with minimal required information

    Returns:
        Prompt string for generating one chapter summary
    """
    purpose = (
        f"Create a summary for chapter {context.position + 1} of {context.total_chapters}. "
        "Generate a title and brief summary that establishes this chapter's role in the narrative."
    )

    schema = (
        "{\n"
        f'  "id": "{context.chapter_id}",\n'
        '  "title": "Chapter Title",\n'
        '  "summary": "2-3 sentence summary of chapter purpose and arc"\n'
        "}"
    )

    # Determine chapter position description
    if context.position == 0:
        position_desc = "Opening chapter - establishes setting, introduces conflict"
    elif context.position == context.total_chapters - 1:
        position_desc = "Final chapter - resolution and denouement"
    elif context.position < context.total_chapters // 3:
        position_desc = "Early chapter - building tension, developing characters"
    elif context.position < 2 * context.total_chapters // 3:
        position_desc = "Middle chapter - complications, escalation"
    else:
        position_desc = "Late chapter - crisis, climax approaching"

    sections: dict[str, str] = {
        "Assigned ID": (f'"{context.chapter_id}" - Use this exact ID in your output.'),
        "Chapter Position": f"{context.position + 1} of {context.total_chapters} ({position_desc})",
        "Scenes in Chapter": f"{context.scene_count} scenes planned",
        "Story Premise": context.premise,
        "Style": _format_style_hint(context.style),
    }

    if context.previous_chapter_summaries:
        recent = context.previous_chapter_summaries[-3:]  # Last 3 chapters
        sections["Previous Chapters"] = "\n".join(f"- {summary}" for summary in recent)

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Generate ONLY this chapter's title and summary. "
        "Title should be evocative but not spoilery. "
        "Summary should hint at the chapter's arc without full details."
    )

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


def build_scene_prompt_v2(context: SceneContext, style: StyleOutput) -> str:
    """Build a focused prompt for generating a single scene.

    This is the most important prompt for the sequential pipeline. It provides
    only the context needed for this specific scene:
    - Characters present in this scene only
    - Location for this scene only
    - Beat slots to fill
    - Previous scene summary for continuity
    - Chapter context for narrative arc

    Args:
        context: SceneContext with filtered, minimal information
        style: StyleOutput for tone guidance

    Returns:
        Prompt string for generating one scene with beats
    """
    purpose = (
        f"Generate content for scene {context.scene_id}. "
        "Create a complete scene with title, summary, and beats for the characters present."
    )

    # Build character list
    if context.characters:
        character_list = "\n".join(
            f"- {c.id}: {c.name} ({c.role or 'supporting'})" + (f" - wants: {c.desire}" if c.desire else "")
            for c in context.characters
        )
    else:
        character_list = "No specific characters assigned - use implied characters."

    # Build location info
    if context.location:
        location_info = f"{context.location.id}: {context.location.name}"
        if context.location.facts:
            location_info += f" ({', '.join(context.location.facts[:2])})"
    else:
        location_info = "No specific location - use implied setting."

    # Build beat list with required IDs
    beat_list = "\n".join(
        f"- {b.id}: {b.kind}" + (" [REQUIRED - from story shape]" if b.required else "") for b in context.beat_slots
    )

    # Build the output schema with actual beat IDs
    beat_examples = ",\n    ".join(
        f'{{"id": "{b.id}", "kind": "{b.kind}", "summary": "Beat action summary"}}' for b in context.beat_slots[:2]
    )
    if len(context.beat_slots) > 2:
        beat_examples += ",\n    ..."

    # Build characters list for schema
    char_ids_json = ", ".join(f'"{c.id}"' for c in context.characters)

    schema = (
        "{\n"
        f'  "id": "{context.scene_id}",\n'
        + (f'  "location": "{context.location.id}",\n' if context.location else "")
        + '  "time": "time of day/period",\n'
        + f'  "characters": [{char_ids_json}],\n'
        + '  "summary": "Scene summary (2-3 sentences)",\n'
        + '  "goal": "What protagonist wants in this scene",\n'
        + '  "conflict": "What opposes the goal",\n'
        + '  "outcome": "How the scene resolves",\n'
        + f'  "beats": [\n    {beat_examples}\n  ]\n'
        + "}"
    )

    sections: dict[str, str] = {
        "Assigned ID": f'"{context.scene_id}" - Use this exact ID in your output.',
    }

    # Chapter context
    if context.chapter_id:
        chapter_info = f"Chapter {context.chapter_id}"
        if context.chapter_title:
            chapter_info += f': "{context.chapter_title}"'
        chapter_info += f" (scene {context.position_in_chapter + 1} of {context.total_scenes_in_chapter})"
        sections["Chapter"] = chapter_info

    # Position context
    sections["Story Position"] = (
        f"Scene {context.position_in_story + 1} of {context.total_scenes} ({context.position_label})"
    )

    # Continuity context
    if context.previous_scene_summaries:
        # Most recent first, but display in chronological order
        recent = list(reversed(context.previous_scene_summaries[:3]))
        sections["Previous Scenes"] = "\n".join(f"- {s}" for s in recent)
    else:
        sections["Previous Scenes"] = "This is the first scene."

    sections["Characters in Scene"] = character_list
    sections["Location"] = location_info
    sections["Style"] = _format_style_hint(style)
    sections["Required Beats"] = beat_list
    sections["Output Schema (JSON)"] = schema

    # Critical notes
    notes_lines = [
        f"Generate EXACTLY {len(context.beat_slots)} beats with the IDs listed above.",
        "Use ONLY the character IDs from 'Characters in Scene'.",
        "Use the location ID from 'Location' (if provided).",
        "Beat summaries should be 1-2 sentences of concrete action.",
        "Scene summary should capture the emotional arc, not just events.",
    ]
    sections["CRITICAL Notes"] = "\n".join(f"- {note}" for note in notes_lines)

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


def build_style_prompt_v2(format_name: str, idea: str) -> str:
    """Build a focused prompt for generating narrative style.

    Args:
        format_name: The narrative format
        idea: The story idea for context

    Returns:
        Prompt string for generating style
    """
    purpose = (
        f"Define narrative style for a {format_name}. "
        "Determine the POV, tense, voice, and register that best fit the story idea."
    )

    schema = (
        "{\n"
        '  "language": "en",\n'
        '  "pov": "third",\n'
        '  "tense": "past",\n'
        '  "voice": "observant",\n'
        '  "register": "literary",\n'
        '  "constraints": []\n'
        "}"
    )

    sections: dict[str, str] = {
        "Format": format_name,
        "Story Idea": idea,
        "Output Schema (JSON)": schema,
        "Notes": (
            "- language: ISO 639-1 code (e.g., 'en', 'de', 'fr')\n"
            "- pov: 'first', 'third', 'third-omniscient'\n"
            "- tense: 'past', 'present'\n"
            "- voice: narrative voice quality (e.g., 'intimate', 'detached', 'wry')\n"
            "- register: 'formal', 'literary', 'informal', 'colloquial'\n"
            "- constraints: optional writing constraints (avoid certain techniques, etc.)"
        ),
    }

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


def build_premise_prompt_v2(format_name: str, idea: str, style: StyleOutput) -> str:
    """Build a focused prompt for expanding idea into premise.

    Args:
        format_name: The narrative format
        idea: The original story idea
        style: Generated style for tone guidance

    Returns:
        Prompt string for generating expanded premise
    """
    purpose = (
        "Expand a simple story idea into a compelling narrative premise. "
        "The premise should be 2-4 sentences capturing the core conflict, setting, and stakes."
    )

    schema = '{\n  "premise": "2-4 sentences capturing conflict, setting, and emotional stakes."\n}'

    sections: dict[str, str] = {
        "Format": format_name,
        "Original Idea": idea,
        "Style": _format_style_hint(style),
        "Output Schema (JSON)": schema,
        "Notes": (
            "The premise should feel more developed than the original idea.\n"
            "Focus on: What happens? Who is affected? What's at stake?\n"
            "Avoid spoiling the ending or over-explaining the plot.\n"
            "Keep it evocative and emotionally resonant."
        ),
    }

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


def build_fragment_prompt_v2(context: FragmentContext) -> str:
    """Build a focused prompt for generating a single fragment.

    For micro-prose sequential generation. Each fragment is a standalone
    piece of flash fiction that continues the narrative.

    Args:
        context: FragmentContext with minimal required information

    Returns:
        Prompt string for generating one fragment
    """
    purpose = (
        f"Generate fragment {context.position + 1} of {context.total_fragments}. "
        "Create a complete flash fiction fragment that continues the narrative."
    )

    schema = f'{{\n  "id": "{context.fragment_id}",\n  "content": "The fragment prose (1-3 paragraphs)"\n}}'

    sections: dict[str, str] = {
        "Assigned ID": f'"{context.fragment_id}" - Use this exact ID in your output.',
        "Position": f"Fragment {context.position + 1} of {context.total_fragments}",
        "Premise": context.premise,
        "Style": _format_style_hint(context.style),
    }

    if context.previous_fragment_summaries:
        sections["Previous Fragments"] = "\n".join(f"- {s}" for s in context.previous_fragment_summaries)
    else:
        sections["Previous Fragments"] = "This is the first fragment."

    sections["Output Schema (JSON)"] = schema
    sections["Notes"] = (
        "Generate ONLY this fragment. "
        "Keep prose evocative and atmospheric. "
        "Each fragment should stand alone yet connect to the whole. "
        "Text should be 1-3 paragraphs of complete prose."
    )

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


def build_stanza_prompt_v2(context: StanzaContext) -> str:
    """Build a focused prompt for generating a single stanza.

    For poem sequential generation. Each stanza is a set of lines
    that must match the target line count.

    Args:
        context: StanzaContext with minimal required information

    Returns:
        Prompt string for generating one stanza
    """
    purpose = (
        f"Generate stanza {context.position + 1} of {context.total_stanzas}. "
        f"Create exactly {context.target_line_count} lines of poetry."
    )

    schema = (
        "{\n"
        f'  "id": "{context.stanza_id}",\n'
        f'  "lines": ["line 1", "line 2", ...],  // Exactly {context.target_line_count} lines\n'
        '  "meter": "optional meter description",\n'
        '  "rhyme_scheme": "optional rhyme pattern"\n'
        "}"
    )

    sections: dict[str, str] = {
        "Assigned ID": f'"{context.stanza_id}" - Use this exact ID in your output.',
        "Position": f"Stanza {context.position + 1} of {context.total_stanzas}",
        "Line Count": f"Exactly {context.target_line_count} lines required",
        "Premise": context.premise,
        "Style": _format_style_hint(context.style),
    }

    if context.poem_form:
        sections["Poem Form"] = context.poem_form

    if context.previous_stanza_texts:
        # Show last few stanzas for rhythm/rhyme continuity
        sections["Previous Stanzas"] = "\n---\n".join(context.previous_stanza_texts)
    else:
        sections["Previous Stanzas"] = "This is the first stanza."

    sections["Output Schema (JSON)"] = schema
    sections["CRITICAL Notes"] = (
        f"- Generate EXACTLY {context.target_line_count} lines in the 'lines' array\n"
        "- Each line should be a complete poetic line\n"
        "- Maintain consistent voice and rhythm\n"
        "- Use the exact stanza ID provided"
    )

    return build_system_prompt(purpose, _format_guidelines()) + "\n\n" + format_sections(sections)


__all__ = [
    "build_character_prompt_v2",
    "build_chapter_prompt_v2",
    "build_fragment_prompt_v2",
    "build_location_prompt_v2",
    "build_premise_prompt_v2",
    "build_scene_prompt_v2",
    "build_stanza_prompt_v2",
    "build_style_prompt_v2",
]
