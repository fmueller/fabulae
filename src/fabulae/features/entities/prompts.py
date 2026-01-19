"""Prompts for entity suggestion commands."""

from fabulae.features.entities.utils import (
    format_existing_characters,
    format_existing_scenes,
    format_existing_world_facts,
)
from fabulae.models import Project, Scene


def build_character_suggest_prompt(
    project: Project,
    guidance: str | None = None,
) -> str:
    """Build prompt for character suggestion."""
    existing = format_existing_characters(project.characters)
    premise = project.plot.premise if project.plot else "Not specified"

    # Get project language for language guard
    language = project.style.language if project.style else None
    language_instruction = ""
    if language:
        language_instruction = (
            f"\nIMPORTANT: All text content MUST be written in {language}. "
            f"Generate names and descriptions in this language.\n"
        )

    guidance_section = ""
    if guidance:
        guidance_section = f"""
USER GUIDANCE:
{guidance}

Use this guidance to shape the character, but ensure they fit the story.
"""

    return f"""You are helping create a character for a story.
{language_instruction}
STORY PREMISE:
{premise}

EXISTING CHARACTERS (do not duplicate these):
{existing}
{guidance_section}
Create a NEW character that:
1. Fills a gap in the current cast (missing archetype, needed role)
2. Has potential for interesting interactions with existing characters
3. Serves the story's needs based on the premise

Generate a character with these fields:
- id: A unique lowercase-with-hyphens identifier (e.g., "detective-chen")
- name: Full character name
- role: One of "protagonist", "antagonist", or "supporting"
- desire: What they consciously want (1 sentence)
- need: What they actually need for growth (1 sentence)
- flaw: Their key weakness (1-3 words)
- secret: Something hidden about them (1 sentence, optional)
- traits: 2-4 personality traits as a list

Output valid JSON matching this schema."""


def build_beat_suggest_prompt(
    scene: Scene,
    project: Project,
    guidance: str | None = None,
) -> str:
    """Build prompt for beat suggestion within a scene."""
    existing_beats = "\n".join([f"- {b.id}: [{b.kind}] {b.summary}" for b in (scene.beats or [])]) or "No beats yet."

    scene_characters = [c for c in project.characters if c.id in (scene.characters or [])]
    char_context = format_existing_characters(scene_characters)

    # Get project language for language guard
    language = project.style.language if project.style else None
    language_instruction = ""
    if language:
        language_instruction = f"\nIMPORTANT: All text content MUST be written in {language}.\n"

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""You are helping add a beat to a scene.
{language_instruction}
SCENE: {scene.id}
Summary: {scene.summary or "Not specified"}

CHARACTERS IN SCENE:
{char_context}

EXISTING BEATS IN THIS SCENE:
{existing_beats}
{guidance_section}
Create a NEW beat that:
1. Advances the scene's narrative
2. Involves the characters present
3. Doesn't duplicate existing beats

Generate a beat with these fields:
- id: Unique lowercase-with-hyphens (e.g., "beat-confrontation")
- kind: One of "action", "dialogue", "revelation", "decision", "transition", "setup",
  "turn", "escalation", "resolution", "bridge", "complication"
- summary: 1-2 sentences describing what happens
- goal: Optional - what the POV character wants to achieve
- conflict: Optional - what obstacle or tension exists
- outcome: Optional - how the beat resolves

Output valid JSON matching this schema."""


def build_scene_suggest_prompt(
    project: Project,
    chapter_id: str | None = None,
    guidance: str | None = None,
) -> str:
    """Build prompt for scene suggestion."""
    existing = format_existing_scenes(project.plot.scenes or [])
    characters = format_existing_characters(project.characters)
    world_facts = format_existing_world_facts(project.world.facts if project.world else [])

    # Get project language for language guard
    language = project.style.language if project.style else None
    language_instruction = ""
    if language:
        language_instruction = f"\nIMPORTANT: All text content MUST be written in {language}.\n"

    chapter_context = ""
    if chapter_id and project.plot.chapters:
        chapter = next((c for c in project.plot.chapters if c.id == chapter_id), None)
        if chapter:
            chapter_context = f"""
TARGET CHAPTER: {chapter.title or chapter.id}
Summary: {chapter.summary or "Not specified"}
"""

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    # Format valid location IDs
    location_ids = []
    if project.world:
        location_ids = [f.id for f in project.world.facts if f.type == "location"]
    valid_locations = ", ".join(location_ids) if location_ids else "No locations defined"

    return f"""You are helping add a scene to a story.
{language_instruction}
PREMISE: {project.plot.premise if project.plot else "Not specified"}
{chapter_context}
EXISTING SCENES:
{existing}

AVAILABLE CHARACTERS:
{characters}

AVAILABLE WORLD FACTS:
{world_facts}

VALID LOCATION IDs: {valid_locations}
{guidance_section}
Create a NEW scene that:
1. Advances the plot or develops characters
2. Doesn't duplicate existing scenes
3. Uses available characters meaningfully
4. Only references existing character IDs and location IDs

Generate a scene with these fields:
- id: Unique lowercase-with-hyphens (e.g., "scene-confrontation")
- summary: 2-3 sentences describing what happens
- goal: Optional - what the protagonist wants to achieve
- conflict: Optional - the obstacle or tension in this scene
- outcome: Optional - how the scene resolves
- characters: List of character IDs who appear (must be valid IDs from above)
- location: Optional location ID from world facts (must be valid)
- time: Optional time indicator

Output valid JSON matching this schema. Do NOT include beats - those are added separately."""


def build_chapter_suggest_prompt(
    project: Project,
    guidance: str | None = None,
) -> str:
    """Build prompt for chapter suggestion."""
    chapter_lines = [f"- {c.id}: {c.title or 'Untitled'} - {c.summary or 'No summary'}" for c in project.plot.chapters]
    existing_chapters = "\n".join(chapter_lines) or "No chapters yet."

    existing_scenes = format_existing_scenes(project.plot.scenes)

    # Get project language for language guard
    language = project.style.language if project.style else None
    language_instruction = ""
    if language:
        language_instruction = f"\nIMPORTANT: All text content MUST be written in {language}.\n"

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""You are helping add a chapter to a story.
{language_instruction}
PREMISE: {project.plot.premise if project.plot else "Not specified"}

EXISTING CHAPTERS:
{existing_chapters}

EXISTING SCENES:
{existing_scenes}
{guidance_section}
Create a NEW chapter that:
1. Advances the overall plot arc
2. Doesn't duplicate existing chapters
3. Fits naturally after existing chapters

Generate a chapter with these fields:
- id: Unique lowercase-with-hyphens (e.g., "chapter-revelation")
- title: Short evocative title
- summary: 2-3 sentences describing the chapter's arc

Output valid JSON matching this schema. Do NOT include scene_ids - scenes are added separately."""


def build_world_suggest_prompt(
    project: Project,
    fact_type: str | None = None,
    guidance: str | None = None,
) -> str:
    """Build prompt for world fact suggestion."""
    existing_facts = format_existing_world_facts(project.world.facts if project.world else [])

    # Get project language for language guard
    language = project.style.language if project.style else None
    language_instruction = ""
    if language:
        language_instruction = f"\nIMPORTANT: All text content MUST be written in {language}.\n"

    type_constraint = ""
    if fact_type:
        type_constraint = f"\nREQUIRED TYPE: {fact_type}\nGenerate only a {fact_type} world fact."

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""You are helping build the world for a story.
{language_instruction}
PREMISE: {project.plot.premise if project.plot else "Not specified"}

EXISTING WORLD FACTS:
{existing_facts}
{type_constraint}
{guidance_section}
Create a NEW world fact that:
1. Enriches the story's setting
2. Could be referenced in scenes
3. Doesn't contradict existing facts

Generate a world fact with these fields:
- id: Unique lowercase-with-hyphens (e.g., "location-tavern" or "culture-elven")
- type: One of "location", "culture", "history", "rule", "object"
- name: Name of the location or concept
- facts: List of 2-4 specific details about this world element

Output valid JSON matching this schema."""


def build_fragment_suggest_prompt(
    project: Project,
    guidance: str | None = None,
) -> str:
    """Build prompt for fragment suggestion (micro-prose format)."""
    # Format existing fragments
    fragment_lines = []
    for f in project.plot.fragments:
        content_preview = f.content[:50] + "..." if len(f.content) > 50 else f.content
        fragment_lines.append(f"- {f.id}: {content_preview}")
    existing_fragments = "\n".join(fragment_lines) or "No fragments yet."

    # Get project language for language guard
    language = project.style.language if project.style else None
    language_instruction = ""
    if language:
        language_instruction = f"\nIMPORTANT: All text content MUST be written in {language}.\n"

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""You are helping add a fragment to a flash fiction story.
{language_instruction}
PREMISE: {project.plot.premise if project.plot else "Not specified"}

EXISTING FRAGMENTS:
{existing_fragments}
{guidance_section}
Create a NEW fragment that:
1. Advances the narrative
2. Flows naturally from existing fragments
3. Maintains consistent tone and style

Generate a fragment with these fields:
- id: Unique lowercase-with-hyphens (e.g., "fragment-03")
- content: The prose content (1-3 paragraphs of evocative micro-prose)
- target_words: Optional target word count (number)
- notes: Optional notes about this fragment's purpose

Output valid JSON matching this schema."""


def build_stanza_suggest_prompt(
    project: Project,
    guidance: str | None = None,
) -> str:
    """Build prompt for stanza suggestion (poem format)."""
    # Format existing stanzas
    stanza_lines = []
    for s in project.plot.stanzas:
        first_line = s.lines[0] if s.lines else "No lines"
        line_preview = first_line[:40] + "..." if len(first_line) > 40 else first_line
        stanza_lines.append(f'- {s.id}: "{line_preview}"')
    existing_stanzas = "\n".join(stanza_lines) or "No stanzas yet."

    # Get project language for language guard
    language = project.style.language if project.style else None
    language_instruction = ""
    if language:
        language_instruction = f"\nIMPORTANT: All text content MUST be written in {language}.\n"

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""You are helping add a stanza to a poem.
{language_instruction}
PREMISE: {project.plot.premise if project.plot else "Not specified"}

EXISTING STANZAS:
{existing_stanzas}
{guidance_section}
Create a NEW stanza that:
1. Continues the poem's themes
2. Maintains consistent meter and rhyme scheme (if established)
3. Advances the poetic narrative

Generate a stanza with these fields:
- id: Unique lowercase-with-hyphens (e.g., "stanza-03")
- lines: List of lines in this stanza
- meter: Optional meter pattern (e.g., "iambic pentameter")
- rhyme_scheme: Optional rhyme scheme (e.g., "ABAB")

Output valid JSON matching this schema."""
