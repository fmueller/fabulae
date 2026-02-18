"""Prompts for building narrative prose from project structures."""

from __future__ import annotations

from fabulae.models import Beat, Character, Fragment, LiteratureFormat, Scene, Stanza, Style, WorldFact
from fabulae.prompts import build_language_guard_prompt, build_system_prompt, format_sections, serialize_for_prompt

# Default words-per-beat when a beat has no explicit target_words.
# Values are rough midpoints for each format's typical prose density.
DEFAULT_BEAT_WORDS: dict[LiteratureFormat, int] = {
    "novel": 400,
    "novella": 250,
    "short-story": 150,
    # micro-prose and poem don't use beats
    "micro-prose": 50,
    "poem": 0,
}


def _compute_scene_word_target(beats: list[Beat], fmt: LiteratureFormat | None) -> int | None:
    """Compute the total word-count target for a scene.

    Sums explicit beat.target_words values; uses the format default for beats
    that omit it.  Returns ``None`` only when there are no beats AND no format
    default (i.e. poetry / micro-prose).
    """
    if not beats:
        return None

    effective_fmt = fmt or "novel"
    default = DEFAULT_BEAT_WORDS.get(effective_fmt, 0)

    # Don't produce a target for formats where it doesn't apply
    if default == 0:
        return None

    total = sum(beat.target_words or default for beat in beats)
    return total if total > 0 else None


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


def _format_characters(characters: list[Character], detailed: bool = False) -> str:
    """Format character information for prompts.

    Args:
        characters: List of characters to format.
        detailed: If True, include desire, need, flaw for dialog/inner monologue guidance.
    """
    if not characters:
        return "No characters specified."

    parts: list[str] = []
    for char in characters:
        info = [f"- {char.name}"]
        if char.role:
            info.append(f"  Role: {char.role}")
        if char.traits:
            info.append(f"  Traits: {', '.join(char.traits)}")
        if detailed:
            if char.desire:
                info.append(f"  Desire: {char.desire}")
            if char.need:
                info.append(f"  Need: {char.need}")
            if char.flaw:
                info.append(f"  Flaw: {char.flaw}")
        parts.append("\n".join(info))

    return "\n".join(parts)


def _format_location(location: WorldFact | None, detailed: bool = False) -> str:
    """Format location information for prompts.

    Args:
        location: The location world fact.
        detailed: If True, format facts as sensory details for environment descriptions.
    """
    if not location:
        return "No specific location."

    parts = [f"Name: {location.name}"]
    if location.facts:
        if detailed:
            parts.append("Sensory details for environment description:")
            for fact in location.facts:
                parts.append(f"  - {fact}")
        else:
            parts.append(f"Details: {', '.join(location.facts)}")

    return "\n".join(parts)


def _format_beats(
    beats: list[Beat],
    enhanced: bool = False,
    fmt: LiteratureFormat | None = None,
) -> str:
    """Format beat sequence for scene generation.

    Args:
        beats: List of beats to format.
        enhanced: If True, include beat IDs and additional guidance for structured output.
        fmt: Literature format, used to supply a default word target when a beat omits one.
    """
    if not beats:
        return "No specific beats defined. Write a cohesive scene."

    effective_fmt = fmt or "novel"
    default_words = DEFAULT_BEAT_WORDS.get(effective_fmt, 0)

    parts: list[str] = []
    for i, beat in enumerate(beats, 1):
        info = [f"{i}. [{beat.id}] {beat.kind}"] if enhanced else [f"{i}. {beat.kind}"]
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
        # Show explicit target or format default
        target = beat.target_words or default_words
        if target:
            info.append(f"   Target words: ~{target}")
        if enhanced and beat.constraints:
            info.append(f"   Constraints: {', '.join(beat.constraints)}")
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
        # Word count
        "Aim for the word-count targets given per beat and for the scene total"
        " — treat them as approximate goals, not hard limits",
        # Prose craft
        "Show, don't tell: convey emotions through physical sensation, gesture, and action"
        " — 'her hands trembled' not 'she was nervous'",
        "Prefer concrete nouns and strong verbs over adjective and adverb chains"
        " — cut words that don't earn their place",
        "Vary sentence length: short sentences and fragments for tension, longer ones for reflection",
        "Ground abstract ideas in specific, tangible details the reader can see, hear, or touch",
        "Enter scenes late and leave early — skip throat-clearing preamble",
        # Dialogue craft
        "Write dialogue that reveals character personality, desire, and conflict — not just information",
        "Start a new paragraph for each speaker change",
        "Vary dialogue attribution: use action beats, untagged lines, and occasional said/asked",
        "Aim for a healthy mix of dialogue, action, and interiority — avoid long stretches of pure narration",
        # Output format
        "Return only the content field with the complete scene prose",
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
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
    fmt: LiteratureFormat | None = None,
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

    sections["Characters Present"] = _format_characters(characters, detailed=True)
    sections["Location"] = _format_location(location)

    if world_facts:
        facts_text = "\n".join(f"- {fact.name}: {', '.join(fact.facts)}" for fact in world_facts)
        sections["Relevant World Facts"] = facts_text

    sections["Beat Sequence"] = _format_beats(scene.beats, fmt=fmt)

    # Scene-level word count target
    scene_target = _compute_scene_word_target(scene.beats, fmt)
    if scene_target:
        sections["Word Count Target"] = (
            f"Aim for approximately {scene_target} words total for this scene. "
            "This is a guideline, not a hard limit — prioritize narrative quality, "
            "but stay in the neighborhood of the target."
        )

    sections["Style Guidelines"] = _format_style(style)

    sections["Instructions"] = (
        "Write the complete scene prose, expanding each beat into vivid narrative. "
        "Include natural dialogue when characters interact — let their desires, flaws, and conflicts "
        "drive what they say. Start a new paragraph for each speaker. "
        "Also provide a short scene title (2-5 words, evocative, not a full sentence). "
        'Return ONLY: {"title": "Short Title", "content": "..."}'
    )

    return format_sections(sections)


def build_continuity_system_prompt() -> str:
    """Build system prompt for continuity summary generation."""
    return build_system_prompt(
        purpose=(
            "Generate a structured continuity summary of a scene "
            "that preserves plot, dialogue threads, and character emotional states."
        ),
        guidelines=[
            "Summarize the key events that occurred in 2-3 sentences",
            "Note any significant character development or revelations",
            "Highlight any plot points that might be referenced later",
            # Dialogue thread preservation
            "Identify open dialogue threads: promises made, unanswered questions, "
            "unfinished arguments, topics left hanging, or agreements/disagreements that may resurface",
            "If no dialogue threads are open, return an empty list for open_threads",
            # Character emotional state tracking
            "Note each character's emotional state at the END of the scene — "
            "include their name and a brief description (e.g. 'Elena — determined but hiding guilt')",
            "Focus on emotional shifts: if a character entered happy and left angry, capture the ending state",
            # Output
            "Return all three fields: summary, open_threads, emotional_states",
            "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
        ],
    )


def build_continuity_prompt(scene_content: str) -> str:
    """Build user prompt for continuity summary."""
    return format_sections(
        {
            "Scene Content": scene_content,
            "Instructions": (
                "Analyze this scene and return a structured continuity summary with:\n"
                '1. "summary": 2-3 sentences covering key events and plot developments\n'
                '2. "open_threads": list of unresolved dialogue threads '
                "(promises, unanswered questions, unfinished arguments, hanging topics)\n"
                '3. "emotional_states": list of character emotional states at scene end '
                "(e.g. 'Marcus — frustrated, doubting his allies')"
            ),
        }
    )


def build_fragment_system_prompt(style: Style | None) -> str:
    """Build system prompt for micro-prose fragment generation."""
    guidelines = [
        "Write polished, evocative prose for this flash fiction fragment",
        "Create a complete micro-narrative with emotional resonance",
        "Use precise, carefully chosen language",
        "Maintain the style and tone specified",
        # Prose craft
        "Show, don't tell: convey emotions through physical sensation and action rather than naming them",
        "Every word must earn its place — prefer concrete, specific language over ornate description",
        "Vary sentence rhythm to control pacing",
        # Output format
        "Return only the content field with the prose",
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
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
        'Write the complete prose for this fragment, expanding on the content seed. Return ONLY: {"content": "..."}'
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
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
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
        'Write the lines for this stanza following the specified form. Return ONLY: {"lines": ["..."]}'
    )

    return format_sections(sections)


def build_poem_system_prompt(style: Style | None) -> str:
    """Build system prompt for complete poem generation (for simple line-based poems)."""
    guidelines = [
        "Write a complete poem following the specified form and style",
        "Maintain consistent meter and rhyme scheme if specified",
        "Create imagery that supports the theme",
        "Return the content field with the complete poem text",
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
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
        'Write the complete poem, using the line seeds as inspiration if provided. Return ONLY: {"content": "..."}'
    )

    return format_sections(sections)


# --- Enhanced prompt builders for hooks and beat-level tracking ---


HOOK_TYPES = ["question", "action", "dialog", "image", "tension"]


def _format_prior_hooks(prior_hooks: list[str], limit: int = 3) -> str:
    """Format previous hooks to encourage diversity."""
    if not prior_hooks:
        return "No previous hooks."
    recent = prior_hooks[-limit:]
    return "\n".join(f"- {hook}" for hook in recent)


def build_enhanced_scene_system_prompt(style: Style | None) -> str:
    """Build system prompt for enhanced scene generation with hooks and beat tracking."""
    guidelines = [
        "Write vivid, engaging prose that brings the scene to life",
        "Expand each beat into fully-realized narrative",
        "Show character emotions through action, dialogue, and inner thought",
        "Use sensory details to ground the reader (visual, auditory, tactile, olfactory)",
        "Maintain consistent POV and tense throughout",
        "Create natural transitions between beats",
        # Word count
        "Aim for the word-count targets given per beat and for the scene total"
        " — treat them as approximate goals, not hard limits",
        # Enhanced narrative elements
        "Start with a compelling hook that draws the reader in immediately",
        "Vary hook types (action, dialogue, image, question, tension) from previous scenes",
        "Show character inner thoughts and reactions when POV allows",
        "Describe the environment to establish mood and atmosphere",
        # Prose craft
        "Show, don't tell: convey emotions through physical sensation, gesture, and action"
        " — 'her hands trembled' not 'she was nervous'",
        "Prefer concrete nouns and strong verbs over adjective and adverb chains"
        " — cut words that don't earn their place",
        "Vary sentence length: short sentences and fragments for tension, longer ones for reflection",
        "Ground abstract ideas in specific, tangible details the reader can see, hear, or touch",
        "Enter scenes late and leave early — skip throat-clearing preamble",
        # Dialogue craft
        "Write dialogue that reveals character personality, desire, and conflict — not just information",
        "Let each character's desire, need, and flaw shape what they say and how they say it",
        "Start a new paragraph for each speaker change",
        "Vary dialogue attribution: use action beats, untagged lines, and occasional said/asked",
        "Balance dialogue with action and interiority — avoid long stretches of pure narration or pure dialogue",
        # Output format
        "Return JSON with 'hook' object and 'beats' array as specified",
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
    ]

    if style and style.language:
        guidelines.append(build_language_guard_prompt(style.language))

    return build_system_prompt(
        purpose="Generate enhanced prose for a narrative scene with opening hook and beat-level tracking.",
        guidelines=guidelines,
    )


def build_enhanced_scene_prompt(
    scene: Scene,
    characters: list[Character],
    location: WorldFact | None,
    world_facts: list[WorldFact],
    style: Style | None,
    prior_context: str,
    premise: str,
    prior_hooks: list[str] | None = None,
    fmt: LiteratureFormat | None = None,
) -> str:
    """Build user prompt for enhanced scene generation with hooks and beat tracking.

    Args:
        scene: The scene to generate prose for.
        characters: Characters present in the scene.
        location: The scene's location.
        world_facts: Relevant world facts.
        style: Style guidance.
        prior_context: Summary of previous scenes.
        premise: Story premise.
        prior_hooks: Previous scene hooks for diversity.
        fmt: Literature format for word-count defaults.

    Returns:
        User prompt string.
    """
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

    # Use detailed character formatting for enhanced prompts
    sections["Characters Present"] = _format_characters(characters, detailed=True)
    sections["Location"] = _format_location(location, detailed=True)

    if world_facts:
        facts_text = "\n".join(f"- {fact.name}: {', '.join(fact.facts)}" for fact in world_facts)
        sections["Relevant World Facts"] = facts_text

    # Include beat IDs for tracking
    sections["Beat Sequence"] = _format_beats(scene.beats, enhanced=True, fmt=fmt)

    # Scene-level word count target
    scene_target = _compute_scene_word_target(scene.beats, fmt)
    if scene_target:
        sections["Word Count Target"] = (
            f"Aim for approximately {scene_target} words total for this scene. "
            "This is a guideline, not a hard limit — prioritize narrative quality, "
            "but stay in the neighborhood of the target."
        )

    sections["Style Guidelines"] = _format_style(style)

    # Hook diversity guidance
    if prior_hooks:
        sections["Previous Hooks (for diversity)"] = _format_prior_hooks(prior_hooks)

    hook_types_str = ", ".join(HOOK_TYPES)
    instructions = f"""Generate an enhanced scene with:

1. A short scene TITLE (2-5 words, evocative, not a full sentence)

2. An opening HOOK that immediately engages the reader
   - Choose a hook_type from: {hook_types_str}
   - Vary from previous hooks if possible
   - Make it compelling and draw the reader in

3. Each BEAT expanded into vivid prose
   - Use the exact beat IDs provided (e.g., "{scene.beats[0].id if scene.beats else "beat-01"}")
   - Include natural dialogue when characters interact — let their desires, flaws, and conflicts drive what they say
   - Start a new paragraph for each speaker change
   - Vary dialogue attribution: action beats, untagged lines, occasional said/asked
   - Show inner thoughts when POV allows
   - Use sensory environment details
   - Calculate word_count for each beat's prose

Return JSON in this exact format:
{{
  "title": "Short Evocative Title",
  "hook": {{"hook_type": "action|dialog|image|question|tension", "content": "The hook text..."}},
  "beats": [
    {{"beat_id": "beat-id", "prose": "The expanded prose...", "word_count": 150}},
    ...
  ]
}}"""

    sections["Instructions"] = instructions

    return format_sections(sections)


def build_enhanced_fragment_system_prompt(style: Style | None) -> str:
    """Build system prompt for enhanced micro-prose fragment generation."""
    guidelines = [
        "Write polished, evocative prose for this flash fiction fragment",
        "Create a complete micro-narrative with emotional resonance",
        "Use precise, carefully chosen language",
        "Maintain the style and tone specified",
        # Enhanced elements
        "Start with a compelling hook that draws the reader in",
        "Vary hook types from previous fragments",
        # Prose craft
        "Show, don't tell: convey emotions through physical sensation and action rather than naming them",
        "Every word must earn its place — prefer concrete, specific language over ornate description",
        "Vary sentence rhythm to control pacing",
        # Output format
        "Return JSON with 'hook' object and 'content' field",
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
    ]

    if style and style.language:
        guidelines.append(build_language_guard_prompt(style.language))

    return build_system_prompt(
        purpose="Generate enhanced prose for a micro-prose fragment with opening hook.",
        guidelines=guidelines,
    )


def build_enhanced_fragment_prompt(
    fragment: Fragment,
    style: Style | None,
    prior_fragments: list[str],
    premise: str,
    prior_hooks: list[str] | None = None,
) -> str:
    """Build user prompt for enhanced fragment generation.

    Args:
        fragment: The fragment to generate.
        style: Style guidance.
        prior_fragments: Previous fragment contents.
        premise: Story premise.
        prior_hooks: Previous hooks for diversity.

    Returns:
        User prompt string.
    """
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

    if prior_hooks:
        sections["Previous Hooks (for diversity)"] = _format_prior_hooks(prior_hooks)

    hook_types_str = ", ".join(HOOK_TYPES)
    instructions = f"""Generate an enhanced fragment with:

1. An opening HOOK that immediately engages
   - Choose a hook_type from: {hook_types_str}
   - Vary from previous hooks if possible

2. The complete prose CONTENT expanding on the content seed

Return JSON in this exact format:
{{
  "hook": {{"hook_type": "action|dialog|image|question|tension", "content": "The hook text..."}},
  "content": "The complete fragment prose..."
}}"""

    sections["Instructions"] = instructions

    return format_sections(sections)


def build_enhanced_stanza_system_prompt(style: Style | None) -> str:
    """Build system prompt for enhanced poem stanza generation."""
    guidelines = [
        "Write poetry following the specified meter and rhyme scheme if provided",
        "Create lines with appropriate rhythm and flow",
        "Maintain thematic consistency with previous stanzas",
        "Use imagery and language appropriate to the style",
        # Enhanced elements
        "Consider including an opening hook line that captures attention",
        # Output format
        "Return JSON with optional 'hook' object and 'lines' array",
        "CRITICAL: Return ONLY valid JSON. No markdown code blocks, no explanatory text",
    ]

    if style and style.language:
        guidelines.append(build_language_guard_prompt(style.language))

    return build_system_prompt(
        purpose="Generate enhanced lines for a poem stanza with optional opening hook.",
        guidelines=guidelines,
    )


def build_enhanced_stanza_prompt(
    stanza: Stanza,
    style: Style | None,
    prior_stanzas: list[list[str]],
    premise: str,
    poem_form: str | None,
    poem_meter: str | None,
    poem_rhyme_scheme: str | None,
    prior_hooks: list[str] | None = None,
) -> str:
    """Build user prompt for enhanced stanza generation.

    Args:
        stanza: The stanza to generate.
        style: Style guidance.
        prior_stanzas: Lines from previous stanzas.
        premise: Poem theme/premise.
        poem_form: Poem form (sonnet, haiku, etc.).
        poem_meter: Poem meter.
        poem_rhyme_scheme: Poem rhyme scheme.
        prior_hooks: Previous hooks for diversity.

    Returns:
        User prompt string.
    """
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

    if prior_hooks:
        sections["Previous Hooks (for diversity)"] = _format_prior_hooks(prior_hooks)

    hook_types_str = ", ".join(HOOK_TYPES)
    instructions = f"""Generate an enhanced stanza with:

1. An optional opening HOOK (for the first line that captures attention)
   - Only include if the stanza is meant to start strongly
   - Choose a hook_type from: {hook_types_str}

2. The stanza LINES following the specified form

Return JSON in this exact format:
{{
  "hook": {{"hook_type": "image|tension|question", "content": "The hook opening line..."}} or null,
  "lines": ["Line 1", "Line 2", ...]
}}"""

    sections["Instructions"] = instructions

    return format_sections(sections)


__all__ = [
    "DEFAULT_BEAT_WORDS",
    "HOOK_TYPES",
    "build_continuity_prompt",
    "build_continuity_system_prompt",
    "build_enhanced_fragment_prompt",
    "build_enhanced_fragment_system_prompt",
    "build_enhanced_scene_prompt",
    "build_enhanced_scene_system_prompt",
    "build_enhanced_stanza_prompt",
    "build_enhanced_stanza_system_prompt",
    "build_fragment_prompt",
    "build_fragment_system_prompt",
    "build_poem_prompt",
    "build_poem_system_prompt",
    "build_scene_prompt",
    "build_scene_system_prompt",
    "build_stanza_prompt",
    "build_stanza_system_prompt",
]
