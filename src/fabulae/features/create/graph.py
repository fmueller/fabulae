"""Plot graph data structures for deterministic narrative structure generation.

The PlotGraph represents the complete structure of a narrative before any LLM content
generation. This allows structure decisions (how many chapters, scenes, beats) to be
made deterministically with RNG, while content generation uses focused per-unit prompts.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BeatSlot:
    """A slot for a beat in a scene.

    Attributes:
        id: Pre-allocated beat ID (e.g., 'scene-01-beat-01')
        kind: Beat type (action, dialogue, revelation, etc.)
        required: Whether this beat is required by the story shape
        shape_beat_type: If from story shape, the RequiredBeat.type that generated this
    """

    id: str
    kind: str
    required: bool = False
    shape_beat_type: str | None = None


@dataclass
class SceneSlot:
    """A slot for a scene in the plot graph.

    Attributes:
        id: Pre-allocated scene ID (e.g., 'scene-01')
        chapter_id: The chapter this scene belongs to (if any)
        beat_slots: Beats to generate for this scene
        character_ids: Character IDs assigned to this scene
        location_id: Location ID for this scene (if any)
        time: Time of day or period (if any)
        position: Order within chapter (0-indexed)
        position_label: Position descriptor ('early', 'middle', 'late', 'climax')
    """

    id: str
    chapter_id: str | None = None
    beat_slots: list[BeatSlot] = field(default_factory=list)
    character_ids: list[str] = field(default_factory=list)
    location_id: str | None = None
    time: str | None = None
    position: int = 0
    position_label: str = "middle"


@dataclass
class ChapterSlot:
    """A slot for a chapter in the plot graph.

    Attributes:
        id: Pre-allocated chapter ID (e.g., 'chapter-01')
        scene_ids: Scene IDs belonging to this chapter
        position: Order within the narrative (0-indexed)
    """

    id: str
    scene_ids: list[str] = field(default_factory=list)
    position: int = 0


@dataclass
class CharacterSlot:
    """A slot for a character in the narrative.

    Attributes:
        id: Pre-allocated character ID (e.g., 'character-01')
        role: Character role (protagonist, antagonist, supporting, etc.)
        shape_slot_id: If from story shape, the CharacterSlot.slot that generated this
        needs: What this character needs to provide (from shape slot)
    """

    id: str
    role: str
    shape_slot_id: str | None = None
    needs: str | None = None


@dataclass
class LocationSlot:
    """A slot for a location in the narrative.

    Attributes:
        id: Pre-allocated location ID (e.g., 'location-01')
        shape_setting_id: If from story shape, the SettingSlot.slot that generated this
        needs: What this location needs to provide (from shape slot)
    """

    id: str
    shape_setting_id: str | None = None
    needs: str | None = None


@dataclass
class WorldFactSlot:
    """A slot for a world fact (non-location) in the narrative.

    Attributes:
        id: Pre-allocated world fact ID (e.g., 'world-fact-01')
        fact_type: Type of world fact (culture, history, rule, object)
    """

    id: str
    fact_type: str = "culture"


@dataclass
class FragmentSlot:
    """A slot for a fragment in micro-prose.

    Attributes:
        id: Pre-allocated fragment ID (e.g., 'fragment-01')
        position: Order within the narrative (0-indexed)
        mood: Optional mood hint for the fragment
    """

    id: str
    position: int = 0
    mood: str | None = None


@dataclass
class StanzaSlot:
    """A slot for a stanza in a poem.

    Attributes:
        id: Pre-allocated stanza ID (e.g., 'stanza-01')
        position: Order within the poem (0-indexed)
        line_count: Target number of lines for this stanza
        intent: Optional thematic intent for the stanza
    """

    id: str
    position: int = 0
    line_count: int = 4
    intent: str | None = None


@dataclass
class PlotGraph:
    """Complete structure of the narrative before content generation.

    The PlotGraph is generated deterministically using RNG before any LLM calls.
    It defines all structural elements (chapters, scenes, beats) and pre-assigns
    all entity IDs, allowing content generation to happen one unit at a time
    with minimal context.

    Attributes:
        format: Narrative format (novel, novella, short-story, etc.)
        chapters: Chapter slots in order
        scenes: Scene slots in order
        characters: Character slots to fill
        locations: Location slots to fill
        world_facts: Additional world fact slots
        seed: RNG seed used to generate this graph (for reproducibility)
    """

    format: str
    chapters: list[ChapterSlot] = field(default_factory=list)
    scenes: list[SceneSlot] = field(default_factory=list)
    characters: list[CharacterSlot] = field(default_factory=list)
    locations: list[LocationSlot] = field(default_factory=list)
    world_facts: list[WorldFactSlot] = field(default_factory=list)
    seed: int | None = None

    def get_scene(self, scene_id: str) -> SceneSlot | None:
        """Get a scene slot by ID."""
        return next((s for s in self.scenes if s.id == scene_id), None)

    def get_chapter(self, chapter_id: str) -> ChapterSlot | None:
        """Get a chapter slot by ID."""
        return next((c for c in self.chapters if c.id == chapter_id), None)

    def get_chapter_scenes(self, chapter_id: str) -> list[SceneSlot]:
        """Get all scene slots belonging to a chapter."""
        return [s for s in self.scenes if s.chapter_id == chapter_id]

    def get_scene_characters(self, scene_id: str) -> list[str]:
        """Get character IDs assigned to a scene."""
        scene = self.get_scene(scene_id)
        return scene.character_ids if scene else []

    def get_scene_position(self, scene_id: str) -> int:
        """Get the global position of a scene (0-indexed)."""
        for i, scene in enumerate(self.scenes):
            if scene.id == scene_id:
                return i
        return -1

    def get_previous_scene(self, scene_id: str) -> SceneSlot | None:
        """Get the scene immediately before the given scene."""
        pos = self.get_scene_position(scene_id)
        if pos > 0:
            return self.scenes[pos - 1]
        return None

    def get_character(self, character_id: str) -> CharacterSlot | None:
        """Get a character slot by ID."""
        return next((c for c in self.characters if c.id == character_id), None)

    def get_location(self, location_id: str) -> LocationSlot | None:
        """Get a location slot by ID."""
        return next((loc for loc in self.locations if loc.id == location_id), None)

    def total_beats(self) -> int:
        """Get total number of beats across all scenes."""
        return sum(len(scene.beat_slots) for scene in self.scenes)

    def to_summary(self) -> str:
        """Generate a human-readable summary of the graph structure."""
        lines = [
            f"PlotGraph ({self.format})",
            f"  Chapters: {len(self.chapters)}",
            f"  Scenes: {len(self.scenes)}",
            f"  Total beats: {self.total_beats()}",
            f"  Characters: {len(self.characters)}",
            f"  Locations: {len(self.locations)}",
            f"  World facts: {len(self.world_facts)}",
        ]
        if self.seed is not None:
            lines.append(f"  Seed: {self.seed}")
        return "\n".join(lines)


@dataclass
class MicroProseGraph:
    """Complete structure for micro-prose before content generation.

    Similar to PlotGraph but for flash fiction with fragments instead of scenes.

    Attributes:
        fragment_slots: Fragment slots in order
        seed: RNG seed used to generate this graph (for reproducibility)
    """

    fragment_slots: list[FragmentSlot] = field(default_factory=list)
    seed: int | None = None

    def total_fragments(self) -> int:
        """Get total number of fragments."""
        return len(self.fragment_slots)

    def get_fragment(self, fragment_id: str) -> FragmentSlot | None:
        """Get a fragment slot by ID."""
        return next((f for f in self.fragment_slots if f.id == fragment_id), None)

    def get_fragment_position(self, fragment_id: str) -> int:
        """Get the position of a fragment (0-indexed)."""
        for i, fragment in enumerate(self.fragment_slots):
            if fragment.id == fragment_id:
                return i
        return -1

    def to_summary(self) -> str:
        """Generate a human-readable summary of the graph structure."""
        lines = [
            "MicroProseGraph",
            f"  Fragments: {len(self.fragment_slots)}",
        ]
        if self.seed is not None:
            lines.append(f"  Seed: {self.seed}")
        return "\n".join(lines)


@dataclass
class PoemGraph:
    """Complete structure for poem before content generation.

    Similar to PlotGraph but for poetry with stanzas instead of scenes.

    Attributes:
        stanza_slots: Stanza slots in order
        poem_form: Optional poem form (sonnet, haiku, free-verse, etc.)
        seed: RNG seed used to generate this graph (for reproducibility)
    """

    stanza_slots: list[StanzaSlot] = field(default_factory=list)
    poem_form: str | None = None
    seed: int | None = None

    def total_stanzas(self) -> int:
        """Get total number of stanzas."""
        return len(self.stanza_slots)

    def total_lines(self) -> int:
        """Get total expected lines across all stanzas."""
        return sum(s.line_count for s in self.stanza_slots)

    def get_stanza(self, stanza_id: str) -> StanzaSlot | None:
        """Get a stanza slot by ID."""
        return next((s for s in self.stanza_slots if s.id == stanza_id), None)

    def get_stanza_position(self, stanza_id: str) -> int:
        """Get the position of a stanza (0-indexed)."""
        for i, stanza in enumerate(self.stanza_slots):
            if stanza.id == stanza_id:
                return i
        return -1

    def to_summary(self) -> str:
        """Generate a human-readable summary of the graph structure."""
        lines = [
            "PoemGraph",
            f"  Stanzas: {len(self.stanza_slots)}",
            f"  Total lines: {self.total_lines()}",
        ]
        if self.poem_form:
            lines.append(f"  Form: {self.poem_form}")
        if self.seed is not None:
            lines.append(f"  Seed: {self.seed}")
        return "\n".join(lines)
