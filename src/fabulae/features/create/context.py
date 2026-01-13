"""Minimal context builder for focused per-unit generation.

This module builds minimal context for each generation unit, including only
the information necessary for that specific generation task. This reduces
LLM divergence and errors by avoiding context overload.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fabulae.features.create.graph import (
    BeatSlot,
    FragmentSlot,
    MicroProseGraph,
    PlotGraph,
    PoemGraph,
    SceneSlot,
    StanzaSlot,
)
from fabulae.features.create.schemas import CreateOptions, StyleOutput
from fabulae.models import Chapter, Character, Fragment, Scene, Stanza, WorldFact

if TYPE_CHECKING:
    from fabulae.features.create.graph import ChapterSlot, CharacterSlot, LocationSlot


@dataclass
class SceneContext:
    """Minimal context for generating a single scene.

    Contains only the information needed to generate one scene:
    - Scene identification and position
    - Characters present in this scene
    - Location for this scene
    - Beat slots to fill
    - Previous scene summary for continuity
    - Filtered world facts relevant to this scene
    """

    scene_id: str
    scene_slot: SceneSlot

    # Chapter context
    chapter_id: str | None
    chapter_title: str | None
    chapter_summary: str | None
    position_in_chapter: int
    total_scenes_in_chapter: int

    # Entity context (filtered to scene)
    characters: list[Character] = field(default_factory=list)
    location: WorldFact | None = None
    relevant_world_facts: list[WorldFact] = field(default_factory=list)

    # Structural context
    beat_slots: list[BeatSlot] = field(default_factory=list)

    # Continuity context (respecting sliding window)
    previous_scene_summaries: list[str] = field(default_factory=list)

    # Global position
    position_in_story: int = 0
    total_scenes: int = 0
    position_label: str = "middle"


@dataclass
class CharacterContext:
    """Minimal context for generating a single character.

    Contains only the information needed to generate one character:
    - Character slot details
    - Premise for story context
    - Style for tone guidance
    """

    character_slot: CharacterSlot
    premise: str
    style: StyleOutput
    existing_character_names: list[str] = field(default_factory=list)


@dataclass
class LocationContext:
    """Minimal context for generating a single location.

    Contains only the information needed to generate one location:
    - Location slot details
    - Premise for story context
    - Style for tone guidance
    """

    location_slot: LocationSlot
    premise: str
    style: StyleOutput
    existing_location_names: list[str] = field(default_factory=list)


@dataclass
class ChapterContext:
    """Minimal context for generating a single chapter summary.

    Contains only the information needed to generate one chapter:
    - Chapter position and ID
    - Scene slots in this chapter
    - Premise for story context
    - Style for tone guidance
    - Previous chapter summaries for continuity
    """

    chapter_id: str
    position: int
    total_chapters: int
    scene_count: int
    premise: str
    style: StyleOutput
    previous_chapter_summaries: list[str] = field(default_factory=list)


@dataclass
class ProjectState:
    """Accumulated state during sequential generation.

    Tracks all generated content so far for context building:
    - Generated characters
    - Generated locations and world facts
    - Generated chapter summaries
    - Generated scene summaries
    """

    characters: list[Character] = field(default_factory=list)
    locations: list[WorldFact] = field(default_factory=list)
    world_facts: list[WorldFact] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)

    def get_character(self, char_id: str) -> Character | None:
        """Get a character by ID."""
        return next((c for c in self.characters if c.id == char_id), None)

    def get_location(self, loc_id: str) -> WorldFact | None:
        """Get a location by ID."""
        return next((loc for loc in self.locations if loc.id == loc_id), None)

    def get_world_fact(self, fact_id: str) -> WorldFact | None:
        """Get a world fact by ID (including locations)."""
        for loc in self.locations:
            if loc.id == fact_id:
                return loc
        return next((f for f in self.world_facts if f.id == fact_id), None)

    def get_chapter(self, chapter_id: str) -> Chapter | None:
        """Get a chapter by ID."""
        return next((c for c in self.chapters if c.id == chapter_id), None)

    def get_scene(self, scene_id: str) -> Scene | None:
        """Get a scene by ID."""
        return next((s for s in self.scenes if s.id == scene_id), None)

    def get_scene_summary(self, scene_id: str) -> str | None:
        """Get a scene's summary by ID."""
        scene = self.get_scene(scene_id)
        return scene.summary if scene else None


def build_scene_context(
    scene_slot: SceneSlot,
    graph: PlotGraph,
    state: ProjectState,
    options: CreateOptions,
) -> SceneContext:
    """Build minimal context for generating a single scene.

    Filters all context to only what's needed for this specific scene:
    - Only characters assigned to this scene
    - Only the scene's location
    - Only relevant world facts
    - Only recent scene summaries (respecting sliding window)

    Args:
        scene_slot: The scene slot to generate content for
        graph: The plot graph structure
        state: Current generation state with accumulated content
        options: Create options (includes sliding window setting)

    Returns:
        SceneContext with filtered, minimal information
    """
    # Get only characters assigned to this scene
    scene_characters = [char for char in state.characters if char.id in scene_slot.character_ids]

    # Get only the scene's location
    location = None
    if scene_slot.location_id:
        location = state.get_location(scene_slot.location_id)

    # Get chapter context
    chapter_id = scene_slot.chapter_id
    chapter_title = None
    chapter_summary = None
    position_in_chapter = 0
    total_scenes_in_chapter = 1

    if chapter_id:
        chapter = state.get_chapter(chapter_id)
        if chapter:
            chapter_title = chapter.title
            chapter_summary = chapter.summary

        chapter_scenes = graph.get_chapter_scenes(chapter_id)
        total_scenes_in_chapter = len(chapter_scenes)
        for i, cs in enumerate(chapter_scenes):
            if cs.id == scene_slot.id:
                position_in_chapter = i
                break

    # Get previous scene summaries (respecting sliding window)
    previous_summaries = _get_previous_scene_summaries(scene_slot, graph, state, options.sliding_window_scenes)

    # Filter world facts to relevant subset
    relevant_facts = _filter_relevant_world_facts(scene_slot, scene_characters, location, state.world_facts)

    # Calculate global position
    position_in_story = graph.get_scene_position(scene_slot.id)

    return SceneContext(
        scene_id=scene_slot.id,
        scene_slot=scene_slot,
        chapter_id=chapter_id,
        chapter_title=chapter_title,
        chapter_summary=chapter_summary,
        position_in_chapter=position_in_chapter,
        total_scenes_in_chapter=total_scenes_in_chapter,
        characters=scene_characters,
        location=location,
        relevant_world_facts=relevant_facts,
        beat_slots=scene_slot.beat_slots,
        previous_scene_summaries=previous_summaries,
        position_in_story=position_in_story,
        total_scenes=len(graph.scenes),
        position_label=scene_slot.position_label,
    )


def build_character_context(
    character_slot: CharacterSlot,
    premise: str,
    style: StyleOutput,
    state: ProjectState,
) -> CharacterContext:
    """Build minimal context for generating a single character.

    Args:
        character_slot: The character slot to fill
        premise: Story premise for context
        style: Style output for tone guidance
        state: Current generation state

    Returns:
        CharacterContext with minimal information
    """
    existing_names = [c.name for c in state.characters]
    return CharacterContext(
        character_slot=character_slot,
        premise=premise,
        style=style,
        existing_character_names=existing_names,
    )


def build_location_context(
    location_slot: LocationSlot,
    premise: str,
    style: StyleOutput,
    state: ProjectState,
) -> LocationContext:
    """Build minimal context for generating a single location.

    Args:
        location_slot: The location slot to fill
        premise: Story premise for context
        style: Style output for tone guidance
        state: Current generation state

    Returns:
        LocationContext with minimal information
    """
    existing_names = [loc.name for loc in state.locations]
    return LocationContext(
        location_slot=location_slot,
        premise=premise,
        style=style,
        existing_location_names=existing_names,
    )


def build_chapter_context(
    chapter_slot: ChapterSlot,
    graph: PlotGraph,
    premise: str,
    style: StyleOutput,
    state: ProjectState,
) -> ChapterContext:
    """Build minimal context for generating a single chapter summary.

    Args:
        chapter_slot: The chapter slot to generate
        graph: The plot graph structure
        premise: Story premise for context
        style: Style output for tone guidance
        state: Current generation state

    Returns:
        ChapterContext with minimal information
    """
    # Import here to avoid circular import
    from fabulae.features.create.graph import ChapterSlot as ChapterSlotType

    if not isinstance(chapter_slot, ChapterSlotType):
        raise TypeError("chapter_slot must be a ChapterSlot")

    previous_summaries = [c.summary for c in state.chapters if c.summary and c.id != chapter_slot.id]

    return ChapterContext(
        chapter_id=chapter_slot.id,
        position=chapter_slot.position,
        total_chapters=len(graph.chapters),
        scene_count=len(chapter_slot.scene_ids),
        premise=premise,
        style=style,
        previous_chapter_summaries=previous_summaries,
    )


def _get_previous_scene_summaries(
    scene_slot: SceneSlot,
    graph: PlotGraph,
    state: ProjectState,
    window_size: int | None,
) -> list[str]:
    """Get summaries of previous scenes, respecting sliding window.

    Args:
        scene_slot: Current scene slot
        graph: The plot graph structure
        state: Current generation state with scene summaries
        window_size: Max number of previous scenes to include (None = unlimited)

    Returns:
        List of previous scene summaries, most recent first
    """
    summaries: list[str] = []
    scene_pos = graph.get_scene_position(scene_slot.id)

    if scene_pos <= 0:
        return summaries

    # Get previous scenes in reverse order (most recent first)
    start_pos = 0 if window_size is None else max(0, scene_pos - window_size)

    for i in range(scene_pos - 1, start_pos - 1, -1):
        prev_scene = graph.scenes[i]
        summary = state.get_scene_summary(prev_scene.id)
        if summary:
            summaries.append(summary)

    return summaries


def _filter_relevant_world_facts(
    scene_slot: SceneSlot,
    scene_characters: list[Character],
    location: WorldFact | None,
    all_facts: list[WorldFact],
) -> list[WorldFact]:
    """Filter world facts to those relevant to this scene.

    Relevance heuristics:
    - Facts of type 'rule' are always relevant
    - Facts mentioned in character descriptions are relevant
    - Keep only a small subset to avoid context bloat

    Args:
        scene_slot: Current scene slot
        scene_characters: Characters in this scene
        location: Location for this scene (excluded - already in context)
        all_facts: All non-location world facts

    Returns:
        Filtered list of relevant world facts
    """
    relevant: list[WorldFact] = []
    location_id = location.id if location else None

    # Rules are always relevant
    rules = [f for f in all_facts if f.type == "rule" and f.id != location_id]
    relevant.extend(rules[:2])  # Limit to 2 rules

    # Include facts that might relate to characters
    # This is a simple heuristic - in practice, more sophisticated matching could be used
    character_related: list[WorldFact] = []
    character_text = " ".join(f"{c.name} {c.role or ''} {c.desire or ''}" for c in scene_characters).lower()

    for fact in all_facts:
        if fact.id == location_id or fact in relevant:
            continue
        fact_text = f"{fact.name} {' '.join(fact.facts)}".lower()
        # Simple word overlap check
        if any(word in character_text for word in fact_text.split() if len(word) > 4):
            character_related.append(fact)

    relevant.extend(character_related[:2])  # Limit to 2 character-related facts

    return relevant


# =============================================================================
# Micro-prose context builders
# =============================================================================


@dataclass
class FragmentContext:
    """Minimal context for generating a single fragment.

    Contains only the information needed to generate one fragment:
    - Fragment identification and position
    - Story premise for context
    - Style for tone guidance
    - Previous fragment summaries (with sliding window)
    """

    fragment_id: str
    fragment_slot: FragmentSlot
    position: int
    total_fragments: int

    # Style context
    premise: str
    style: StyleOutput

    # Continuity (with sliding window)
    previous_fragment_summaries: list[str] = field(default_factory=list)


@dataclass
class MicroProseState:
    """Accumulated state during micro-prose sequential generation.

    Tracks all generated fragments so far for context building.
    """

    fragments: list[Fragment] = field(default_factory=list)

    def get_fragment(self, fragment_id: str) -> Fragment | None:
        """Get a fragment by ID."""
        return next((f for f in self.fragments if f.id == fragment_id), None)

    def get_fragment_summary(self, fragment_id: str) -> str | None:
        """Get a fragment's summary (truncated content) by ID."""
        frag = self.get_fragment(fragment_id)
        if not frag:
            return None
        # Truncate for context efficiency
        content = frag.content
        if len(content) > 100:
            return content[:100] + "..."
        return content


def build_fragment_context(
    fragment_slot: FragmentSlot,
    graph: MicroProseGraph,
    state: MicroProseState,
    premise: str,
    style: StyleOutput,
    options: CreateOptions,
) -> FragmentContext:
    """Build minimal context for generating a single fragment.

    Args:
        fragment_slot: The fragment slot to fill
        graph: The micro-prose graph structure
        state: Current generation state with accumulated fragments
        premise: Story premise for context
        style: Style output for tone guidance
        options: Create options (includes sliding window setting)

    Returns:
        FragmentContext with minimal, filtered information
    """
    # Get previous fragment summaries with sliding window
    previous_summaries: list[str] = []
    window_size = options.sliding_window_scenes  # Reuse for fragments

    for i in range(fragment_slot.position):
        if i < len(state.fragments):
            summary = state.get_fragment_summary(state.fragments[i].id)
            if summary:
                previous_summaries.append(summary)

    # Apply sliding window
    if window_size is not None and len(previous_summaries) > window_size:
        previous_summaries = previous_summaries[-window_size:]

    return FragmentContext(
        fragment_id=fragment_slot.id,
        fragment_slot=fragment_slot,
        position=fragment_slot.position,
        total_fragments=graph.total_fragments(),
        premise=premise,
        style=style,
        previous_fragment_summaries=previous_summaries,
    )


# =============================================================================
# Poem context builders
# =============================================================================


@dataclass
class StanzaContext:
    """Minimal context for generating a single stanza.

    Contains only the information needed to generate one stanza:
    - Stanza identification and position
    - Target line count
    - Story premise for context
    - Style for tone guidance
    - Poem form if specified
    - Previous stanza texts (with sliding window)
    """

    stanza_id: str
    stanza_slot: StanzaSlot
    position: int
    total_stanzas: int
    target_line_count: int

    # Style context
    premise: str
    style: StyleOutput
    poem_form: str | None = None

    # Continuity (with sliding window)
    previous_stanza_texts: list[str] = field(default_factory=list)


@dataclass
class PoemState:
    """Accumulated state during poem sequential generation.

    Tracks all generated stanzas so far for context building.
    """

    stanzas: list[Stanza] = field(default_factory=list)

    def get_stanza(self, stanza_id: str) -> Stanza | None:
        """Get a stanza by ID."""
        return next((s for s in self.stanzas if s.id == stanza_id), None)

    def get_stanza_text(self, stanza_id: str) -> str | None:
        """Get a stanza's full text (joined lines) by ID."""
        stanza = self.get_stanza(stanza_id)
        return "\n".join(stanza.lines) if stanza else None


def build_stanza_context(
    stanza_slot: StanzaSlot,
    graph: PoemGraph,
    state: PoemState,
    premise: str,
    style: StyleOutput,
    options: CreateOptions,
) -> StanzaContext:
    """Build minimal context for generating a single stanza.

    Args:
        stanza_slot: The stanza slot to fill
        graph: The poem graph structure
        state: Current generation state with accumulated stanzas
        premise: Story premise for context
        style: Style output for tone guidance
        options: Create options (includes sliding window setting)

    Returns:
        StanzaContext with minimal, filtered information
    """
    # Get previous stanza texts with sliding window
    previous_texts: list[str] = []
    window_size = options.sliding_window_scenes  # Reuse for stanzas

    for i in range(stanza_slot.position):
        if i < len(state.stanzas):
            text = state.get_stanza_text(state.stanzas[i].id)
            if text:
                previous_texts.append(text)

    # Apply sliding window
    if window_size is not None and len(previous_texts) > window_size:
        previous_texts = previous_texts[-window_size:]

    return StanzaContext(
        stanza_id=stanza_slot.id,
        stanza_slot=stanza_slot,
        position=stanza_slot.position,
        total_stanzas=graph.total_stanzas(),
        target_line_count=stanza_slot.line_count,
        premise=premise,
        style=style,
        poem_form=graph.poem_form,
        previous_stanza_texts=previous_texts,
    )
