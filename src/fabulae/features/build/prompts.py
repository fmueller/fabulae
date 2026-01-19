"""Prompts for building narrative prose from project structures."""

from __future__ import annotations

from fabulae.models import Beat, Character, Fragment, Scene, Stanza, Style, WorldFact
from fabulae.prompts import build_language_guard_prompt, build_system_prompt, format_sections, serialize_for_prompt


def _format_style(style: Style | None) -> str:
    """Format style guidance for prompts."""
    if not style:
        return "No specific style guidance."

    parts: list[str] = []
    if style.pov:
        parts.append(f"POV: {style.pov}")
    if style.tense:
        parts.append(f"Tense: {style.tense}")
    if style.voice:
        parts.append(f"Voice: {style.voice}")
    if style.register_:
        parts.append(f"Register: {style.register_}")
    if style.constraints:
        parts.append(f"Constraints: {', '.join(style.constraints)}")

    return "\n".join(parts) if parts else "No specific style guidance."


def _format_characters(characters: list[Character]) -> str:
    """Format character information for prompts."""
    if not characters:
        return "No characters specified."

    parts: list[str] = []
    for char in characters:
        info = [f"- {char.name}"]
        if char.role:
            info.append(f"  Role: {char.role}")
        if char.traits:
            info.append(f"  Traits: {', '.join(char.traits)}")
        parts.append("\n".join(info))

    return "\n".join(parts)


def _format_location(location: WorldFact | None) -> str:
    """Format location information for prompts."""
    if not location:
        return "No specific location."

    parts = [f"Name: {location.name}"]
    if location.facts:
        parts.append(f"Details: {', '.join(location.facts)}")

    return "\n".join(parts)


def _format_beats(beats: list[Beat]) -> str:
    """Format beat sequence for scene generation."""
    if not beats:
        return "No specific beats defined. Write a cohesive scene."

    parts: list[str] = []
    for i, beat in enumerate(beats, 1):
        info = [f"{i}. {beat.kind}"]
        if beat.summary:
            info.append(f"   Summary: {beat.summary}")
        if beat.goal:
            info.append(f"   Goal: {beat.goal}")
        if beat.conflict:
            info.append(f"   Conflict: {beat.conflict}")
        if beat.outcome:
            info.append(f"   Outcome: {beat.outcome}")
        if beat.pace:
            info.append(f"   Pace: {beat.pace}")
        if beat.target_words:
            info.append(f"   Target words: ~{beat.target_words}")
        parts.append("\n".join(info))

    return "\n\n".join(parts)


def build_scene_system_prompt(style: Style | None) -> str:
    """Build system prompt for scene generation."""
    guidelines = [
        "Write vivid, engaging prose that brings the scene to life",
        "Expand each beat into fully-realized narrative",
        "Show character emotions and reactions through action and dialogue",
        "Maintain consistent POV and tense throughout",
        "Create natural transitions between beats",
        "Use sensory details to ground the reader in the setting",
        "Return only the content field with the complete scene prose",
    ]

    if style and style.language:
        guidelines.append(build_language_guard_prompt(style.language))

    return build_system_prompt(
        purpose="Generate prose for a narrative scene based on its structural elements.",
        guidelines=guidelines,
    )


def build_scene_prompt(
    scene: Scene,
    characters: list[Character],
    location: WorldFact | None,
    world_facts: list[WorldFact],
    style: Style | None,
    prior_context: str,
    premise: str,
) -> str:
    """Build user prompt for scene generation."""
    sections: dict[str, str] = {}

    sections["Story Premise"] = premise

    if prior_context:
        sections["Previous Context"] = prior_context

    sections["Scene Overview"] = serialize_for_prompt(
        {
            "id": scene.id,
            "summary": scene.summary or "Not specified",
            "goal": scene.goal or "Not specified",
            "conflict": scene.conflict or "Not specified",
            "outcome": scene.outcome or "Not specified",
            "time": scene.time or "Not specified",
        }
    )

    sections["Characters Present"] = _format_characters(characters)
    sections["Location"] = _format_location(location)

    if world_facts:
        facts_text = "\n".join(f"- {fact.name}: {', '.join(fact.facts)}" for fact in world_facts)
        sections["Relevant World Facts"] = facts_text

    sections["Beat Sequence"] = _format_beats(scene.beats)
    sections["Style Guidelines"] = _format_style(style)

    sections["Instructions"] = (
        "Write the complete scene prose, expanding each beat into vivid narrative. "
        "Return your response as a JSON object with a 'content' field containing the prose."
    )

    return format_sections(sections)


def build_continuity_system_prompt() -> str:
    """Build system prompt for continuity summary generation."""
    return build_system_prompt(
        purpose="Generate a brief summary of a scene for continuity tracking.",
        guidelines=[
            "Summarize the key events that occurred",
            "Note any significant character development or revelations",
            "Highlight any plot points that might be referenced later",
            "Keep the summary concise (2-3 sentences)",
            "Return only the summary field",
        ],
    )


def build_continuity_prompt(scene_content: str) -> str:
    """Build user prompt for continuity summary."""
    return format_sections(
        {
            "Scene Content": scene_content,
            "Instructions": "Summarize this scene in 2-3 sentences for continuity tracking.",
        }
    )


def build_fragment_system_prompt(style: Style | None) -> str:
    """Build system prompt for micro-prose fragment generation."""
    guidelines = [
        "Write polished, evocative prose for this flash fiction fragment",
        "Create a complete micro-narrative with emotional resonance",
        "Use precise, carefully chosen language",
        "Maintain the style and tone specified",
        "Return only the content field with the prose",
    ]

    if style and style.language:
        guidelines.append(build_language_guard_prompt(style.language))

    return build_system_prompt(
        purpose="Generate prose for a micro-prose fragment.",
        guidelines=guidelines,
    )


def build_fragment_prompt(
    fragment: Fragment,
    style: Style | None,
    prior_fragments: list[str],
    premise: str,
) -> str:
    """Build user prompt for fragment generation."""
    sections: dict[str, str] = {}

    sections["Story Premise"] = premise

    if prior_fragments:
        sections["Previous Fragments"] = "\n\n---\n\n".join(prior_fragments[-3:])

    sections["Fragment Details"] = serialize_for_prompt(
        {
            "id": fragment.id,
            "content_seed": fragment.content,
            "target_words": fragment.target_words or "Not specified",
            "notes": fragment.notes or "Not specified",
        }
    )

    sections["Style Guidelines"] = _format_style(style)

    sections["Instructions"] = (
        "Write the complete prose for this fragment, expanding on the content seed. "
        "Return your response as a JSON object with a 'content' field containing the prose."
    )

    return format_sections(sections)


def build_stanza_system_prompt(style: Style | None) -> str:
    """Build system prompt for poem stanza generation."""
    guidelines = [
        "Write poetry following the specified meter and rhyme scheme if provided",
        "Create lines with appropriate rhythm and flow",
        "Maintain thematic consistency with previous stanzas",
        "Use imagery and language appropriate to the style",
        "Return the lines field as a list of strings",
    ]

    if style and style.language:
        guidelines.append(build_language_guard_prompt(style.language))

    return build_system_prompt(
        purpose="Generate lines for a poem stanza.",
        guidelines=guidelines,
    )


def build_stanza_prompt(
    stanza: Stanza,
    style: Style | None,
    prior_stanzas: list[list[str]],
    premise: str,
    poem_form: str | None,
    poem_meter: str | None,
    poem_rhyme_scheme: str | None,
) -> str:
    """Build user prompt for stanza generation."""
    sections: dict[str, str] = {}

    sections["Poem Theme"] = premise

    if prior_stanzas:
        prior_text = "\n\n".join("\n".join(lines) for lines in prior_stanzas[-3:])
        sections["Previous Stanzas"] = prior_text

    stanza_info: dict[str, str | None] = {
        "id": stanza.id,
        "meter": stanza.meter or poem_meter or "Not specified",
        "rhyme_scheme": stanza.rhyme_scheme or poem_rhyme_scheme or "Not specified",
    }
    if poem_form:
        stanza_info["poem_form"] = poem_form

    sections["Stanza Details"] = serialize_for_prompt(stanza_info)

    if stanza.lines:
        sections["Existing Lines"] = "\n".join(stanza.lines)

    sections["Style Guidelines"] = _format_style(style)

    sections["Instructions"] = (
        "Write the lines for this stanza following the specified form. "
        "Return your response as a JSON object with a 'lines' field containing a list of strings."
    )

    return format_sections(sections)


def build_poem_system_prompt(style: Style | None) -> str:
    """Build system prompt for complete poem generation (for simple line-based poems)."""
    guidelines = [
        "Write a complete poem following the specified form and style",
        "Maintain consistent meter and rhyme scheme if specified",
        "Create imagery that supports the theme",
        "Return the content field with the complete poem text",
    ]

    if style and style.language:
        guidelines.append(build_language_guard_prompt(style.language))

    return build_system_prompt(
        purpose="Generate a complete poem from the given structure.",
        guidelines=guidelines,
    )


def build_poem_prompt(
    lines: list[str],
    style: Style | None,
    premise: str,
    poem_form: str | None,
    poem_meter: str | None,
    poem_rhyme_scheme: str | None,
) -> str:
    """Build user prompt for complete poem generation."""
    sections: dict[str, str] = {}

    sections["Poem Theme"] = premise

    poem_info: dict[str, str | None] = {
        "form": poem_form or "free verse",
        "meter": poem_meter or "Not specified",
        "rhyme_scheme": poem_rhyme_scheme or "Not specified",
    }
    sections["Poem Structure"] = serialize_for_prompt(poem_info)

    if lines:
        sections["Line Seeds"] = "\n".join(lines)

    sections["Style Guidelines"] = _format_style(style)

    sections["Instructions"] = (
        "Write the complete poem, using the line seeds as inspiration if provided. "
        "Return your response as a JSON object with a 'content' field containing the poem."
    )

    return format_sections(sections)


__all__ = [
    "build_continuity_prompt",
    "build_continuity_system_prompt",
    "build_fragment_prompt",
    "build_fragment_system_prompt",
    "build_poem_prompt",
    "build_poem_system_prompt",
    "build_scene_prompt",
    "build_scene_system_prompt",
    "build_stanza_prompt",
    "build_stanza_system_prompt",
]
