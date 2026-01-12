"""Prompt builders for create-from-idea generation."""

from __future__ import annotations

from fabulae.prompts import build_system_prompt, format_sections


def _format_guidelines() -> list[str]:
    return [
        "Return valid JSON only (no markdown, no extra text).",
        "Match the schema exactly; omit fields you do not use.",
        "Use lowercase, hyphenated ASCII IDs (a-z, 0-9, hyphen) for all entities.",
        "Ensure IDs are unique within each list.",
        "Keep outputs concise and aligned to the requested format.",
    ]


def _format_example(title: str, example: str) -> str:
    return format_sections({title: example.strip()})


def _format_count_range(label: str, count_range: tuple[int, int]) -> str:
    return f"{label} (target): {count_range[0]}-{count_range[1]}"


def build_style_prompt(format_name: str) -> str:
    purpose = (
        "Define narrative style guidance for a Fabulae project. "
        "Provide language as an ISO 639-1 code when possible."
    )
    schema = (
        '{\n'
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


def build_character_plan_prompt(
    format_name: str,
    style_hint: str | None,
    count_range: tuple[int, int],
) -> str:
    purpose = (
        "Generate a cast list with minimal details. "
        "Use the count range to decide how many characters to include."
    )
    schema = (
        '{\n'
        '  "characters": [\n'
        '    {"id": "hero", "name": "Ari", "role": "protagonist", "purpose": "drives the investigation"}\n'
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
) -> str:
    purpose = (
        "Expand a single character into the full schema. "
        "Do not repeat traits or roles already used."
    )
    schema = (
        '{\n'
        '  "id": "hero",\n'
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
        "Draft world metadata and a list of world facts. "
        "Include at least one location if scenes will need locations."
    )
    schema = (
        '{\n'
        '  "setting": "Coastal research town",\n'
        '  "time_period": "near future",\n'
        '  "tone": "moody",\n'
        '  "motifs": ["fog", "radio static"],\n'
        '  "facts": [\n'
        '    {"id": "harbor-lab", "type": "location", "name": "Harbor Lab", "purpose": "main lab hub"}\n'
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
) -> str:
    purpose = (
        "Expand a single world fact into the full schema. "
        "Use concise, non-repetitive facts."
    )
    schema = (
        '{\n'
        '  "id": "harbor-lab",\n'
        '  "type": "location",\n'
        '  "name": "Harbor Lab",\n'
        '  "facts": ["restricted access", "scent of ozone"]\n'
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
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
        '{\n'
        f'  "format": "{format_name}",\n'
        '  "title": "Working Title",\n'
        '  "premise": "A concise premise.",\n'
        '  "themes": ["trust", "perception"],\n'
        '  "hook": {"line": "A hook line."},\n'
        '  "stakes": {"external": "External stakes", "internal": "Internal stakes"},\n'
        '  "chapters": [{"id": "chapter-01", "title": "Opening", "scene_ids": ["scene-01"]}],\n'
        '  "scenes": [\n'
        '    {\n'
        '      "id": "scene-01",\n'
        '      "chapter": "chapter-01",\n'
        '      "summary": "Opening scene summary.",\n'
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
        "Notes": (
            "Scene beat_count drives later beat generation; keep it within the range. "
            "Plot patterns (if provided) are structural constraints; align the outline to them. "
            "Narrative patterns (if provided) are optional guidance for voice and tone, not requirements. "
            "Use narrative pattern tone/motifs/roles to shape chapter and scene summaries when present. "
            "Do not invent new pattern IDs."
        ),
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
) -> str:
    purpose = (
        "Expand a single scene into full details and beats. "
        "Use only the provided IDs for characters and locations."
    )
    schema = (
        '{\n'
        '  "id": "scene-01",\n'
        '  "chapter": "chapter-01",\n'
        '  "location": "harbor-lab",\n'
        '  "time": "night",\n'
        '  "characters": ["hero"],\n'
        '  "world_fact_ids": ["harbor-lab"],\n'
        '  "summary": "Expanded scene summary.",\n'
        '  "goal": "Scene goal",\n'
        '  "conflict": "Scene conflict",\n'
        '  "outcome": "Scene outcome",\n'
        '  "beats": [\n'
        '    {"id": "beat-01", "kind": "setup", "summary": "Beat summary"},\n'
        '    {"id": "beat-02", "kind": "turn", "summary": "Beat summary"}\n'
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Available Characters": available_characters or "None",
        "Available Locations": available_locations or "None",
        "Existing Scene Summaries": existing_summaries or "None yet.",
        "Notes": (
            "Use the beat_count from the Scene Outline; output exactly that many beats. "
            "If a Beat Template is provided, keep required beat kinds in the same positions. "
            "Plot patterns (if provided) are structural constraints; align plot_pattern/plot_pattern_beat to them. "
            "Narrative patterns (if provided) are optional guidance for voice and tone, not requirements. "
            "Reflect narrative pattern tone and roles in scene summary/goal/conflict when present. "
            "Do not invent new pattern IDs."
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


def build_fragment_plan_prompt(
    format_name: str,
    style_hint: str | None,
    count_range: tuple[int, int],
) -> str:
    purpose = "Outline micro-prose fragments with IDs and intent."
    schema = (
        '{\n'
        '  "title": "Working Title",\n'
        '  "premise": "A concise premise.",\n'
        '  "themes": ["memory", "loss"],\n'
        '  "fragments": [\n'
        '    {"id": "frag-01", "target_words": 120, "intent": "evoke the core memory"}\n'
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


def build_plot_patterns_prompt(
    format_name: str,
    style_hint: str | None,
    count_range: tuple[int, int],
) -> str:
    purpose = (
        "Draft a small set of plot patterns for the story format. "
        "Each pattern should list required beats with lowercase, hyphenated beat types."
    )
    schema = (
        '{\n'
        '  "plot_patterns": [\n'
        '    {\n'
        '      "id": "three-act",\n'
        '      "name": "Three-Act Arc",\n'
        '      "description": "A classic rise-fall structure.",\n'
        '      "roles": [\n'
        '        {"id": "protagonist", "description": "drives the central goal", "required": true}\n'
        "      ],\n"
        '      "required_beats": [\n'
        '        {"type": "inciting-incident", "description": "disrupts the status quo"}\n'
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Count Range": _format_count_range("Plot patterns", count_range),
        "Output Schema (JSON)": schema,
        "Notes": (
            "Use concise descriptions; beat types must be lowercase hyphenated IDs. "
            "Beat descriptions are used later as guidance. "
            "If a beat description references a role, use role:<id> that matches roles."
        ),
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


def build_narrative_patterns_prompt(
    format_name: str,
    style_hint: str | None,
    count_range: tuple[int, int],
) -> str:
    purpose = (
        "Draft narrative patterns as optional creative scaffolding. "
        "These are non-canonical exploration aids that bundle voice, themes, and world cues. "
        "They may reference plot patterns but are not structural requirements."
    )
    schema = (
        '{\n'
        '  "narrative_patterns": [\n'
        '    {\n'
        '      "id": "close-third",\n'
        '      "name": "Close Third",\n'
        '      "description": "A tight third-person lens with selective access.",\n'
        '      "plot_pattern": "three-act",\n'
        '      "roles": [\n'
        '        {"id": "observer", "description": "filters the emotional tone", "required": true}\n'
        "      ],\n"
        '      "themes": ["identity"],\n'
        '      "motifs": ["mirrors"],\n'
        '      "setting": "dense city",\n'
        '      "time_period": "near future",\n'
        '      "tone": "noir",\n'
        '      "notes": ["narration tracks subtle shifts in belief"]\n'
        "    }\n"
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Count Range": _format_count_range("Narrative patterns", count_range),
        "Output Schema (JSON)": schema,
        "Notes": (
            "Narrative patterns are optional creative bundles, not canonical constraints. "
            "If plot_pattern is set, it must match an available plot pattern ID. "
            "Patterns may suggest POV, tense, voice, and tone but are not binding."
        ),
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


def build_plot_pattern_assignment_prompt(
    format_name: str,
    style_hint: str | None,
) -> str:
    purpose = (
        "Select a plot pattern and map each required beat type to a scene. "
        "Use only the provided scene IDs and beat types."
    )
    schema = (
        '{\n'
        '  "plot_pattern": "three-act",\n'
        '  "plot_pattern_beats": [\n'
        '    {"type": "inciting-incident", "scene": "scene-01"}\n'
        "  ]\n"
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Output Schema (JSON)": schema,
        "Notes": (
            "Assign every required beat exactly once; omit scene_beat. "
            "Keep plot_pattern_beats in the same order as required_beats. "
            "Do not assign more required beats to a scene than its beat_count."
        ),
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
) -> str:
    purpose = "Write a single micro-prose fragment matching the intent."
    schema = (
        '{\n'
        '  "id": "frag-01",\n'
        '  "content": "A concise fragment.",\n'
        '  "target_words": 120,\n'
        '  "notes": "Optional notes."\n'
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
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
        '{\n'
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
) -> str:
    purpose = "Write a single stanza with the requested number of lines."
    schema = (
        '{\n'
        '  "id": "stanza-01",\n'
        '  "lines": ["Line one.", "Line two.", "Line three.", "Line four."],\n'
        '  "meter": null,\n'
        '  "rhyme_scheme": null\n'
        "}"
    )
    sections: dict[str, str] = {
        "Format": format_name,
        "Existing Stanzas": existing_summary or "None yet.",
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


__all__ = [
    "build_character_plan_prompt",
    "build_character_prompt",
    "build_fragment_plan_prompt",
    "build_fragment_prompt",
    "build_narrative_patterns_prompt",
    "build_plot_pattern_assignment_prompt",
    "build_plot_patterns_prompt",
    "build_plot_outline_prompt",
    "build_poem_plan_prompt",
    "build_scene_prompt",
    "build_stanza_prompt",
    "build_style_prompt",
    "build_world_fact_prompt",
    "build_world_plan_prompt",
]
