"""Tests for context builder."""

from __future__ import annotations

from fabulae.features.create.context import (
    ChapterContext,
    CharacterContext,
    LocationContext,
    ProjectState,
    SceneContext,
    build_character_context,
    build_location_context,
    build_scene_context,
)
from fabulae.features.create.graph import (
    BeatSlot,
    ChapterSlot,
    CharacterSlot,
    LocationSlot,
    PlotGraph,
    SceneSlot,
)
from fabulae.features.create.schemas import CreateOptions, StyleOutput
from fabulae.models import Chapter, Character, Scene, WorldFact


class TestProjectState:
    """Test ProjectState dataclass and methods."""

    def test_project_state_empty(self) -> None:
        """Test empty ProjectState."""
        state = ProjectState()

        assert state.characters == []
        assert state.locations == []
        assert state.world_facts == []
        assert state.chapters == []
        assert state.scenes == []

    def test_project_state_with_content(self) -> None:
        """Test ProjectState with content."""
        characters = [Character(id="character-01", name="Alice", role="protagonist")]
        locations = [WorldFact(id="location-01", type="location", name="Castle")]

        state = ProjectState(characters=characters, locations=locations)

        assert len(state.characters) == 1
        assert len(state.locations) == 1

    def test_get_character_found(self) -> None:
        """Test get_character returns character when found."""
        characters = [
            Character(id="character-01", name="Alice", role="protagonist"),
            Character(id="character-02", name="Bob", role="antagonist"),
        ]
        state = ProjectState(characters=characters)

        char = state.get_character("character-01")
        assert char is not None
        assert char.name == "Alice"

    def test_get_character_not_found(self) -> None:
        """Test get_character returns None when not found."""
        state = ProjectState()
        char = state.get_character("character-99")
        assert char is None

    def test_get_location_found(self) -> None:
        """Test get_location returns location when found."""
        locations = [WorldFact(id="location-01", type="location", name="Castle")]
        state = ProjectState(locations=locations)

        loc = state.get_location("location-01")
        assert loc is not None
        assert loc.name == "Castle"

    def test_get_location_not_found(self) -> None:
        """Test get_location returns None when not found."""
        state = ProjectState()
        loc = state.get_location("location-99")
        assert loc is None

    def test_get_world_fact_includes_locations(self) -> None:
        """Test get_world_fact searches both locations and world_facts."""
        locations = [WorldFact(id="location-01", type="location", name="Castle")]
        world_facts = [WorldFact(id="world-fact-01", type="culture", name="Magic System")]
        state = ProjectState(locations=locations, world_facts=world_facts)

        # Should find location
        fact = state.get_world_fact("location-01")
        assert fact is not None
        assert fact.name == "Castle"

        # Should find world fact
        fact = state.get_world_fact("world-fact-01")
        assert fact is not None
        assert fact.name == "Magic System"

    def test_get_chapter_found(self) -> None:
        """Test get_chapter returns chapter when found."""
        chapters = [Chapter(id="chapter-01", title="Opening")]
        state = ProjectState(chapters=chapters)

        chapter = state.get_chapter("chapter-01")
        assert chapter is not None
        assert chapter.title == "Opening"

    def test_get_scene_found(self) -> None:
        """Test get_scene returns scene when found."""
        scenes = [Scene(id="scene-01", summary="Opening scene")]
        state = ProjectState(scenes=scenes)

        scene = state.get_scene("scene-01")
        assert scene is not None
        assert scene.summary == "Opening scene"

    def test_get_scene_summary(self) -> None:
        """Test get_scene_summary returns summary."""
        scenes = [Scene(id="scene-01", summary="Opening scene")]
        state = ProjectState(scenes=scenes)

        summary = state.get_scene_summary("scene-01")
        assert summary == "Opening scene"

        summary = state.get_scene_summary("scene-99")
        assert summary is None


class TestBuildSceneContext:
    """Test build_scene_context function."""

    def _create_test_graph(self) -> PlotGraph:
        """Create a test graph for context building."""
        chapters = [ChapterSlot(id="chapter-01", scene_ids=["scene-01", "scene-02"])]
        scenes = [
            SceneSlot(
                id="scene-01",
                chapter_id="chapter-01",
                character_ids=["character-01"],
                location_id="location-01",
                position=0,
                position_label="early",
                beat_slots=[
                    BeatSlot(id="scene-01-beat-01", kind="setup"),
                    BeatSlot(id="scene-01-beat-02", kind="turn"),
                ],
            ),
            SceneSlot(
                id="scene-02",
                chapter_id="chapter-01",
                character_ids=["character-01", "character-02"],
                location_id="location-01",
                position=1,
                position_label="climax",
                beat_slots=[
                    BeatSlot(id="scene-02-beat-01", kind="escalation"),
                ],
            ),
        ]
        characters = [
            CharacterSlot(id="character-01", role="protagonist"),
            CharacterSlot(id="character-02", role="antagonist"),
        ]
        locations = [LocationSlot(id="location-01")]

        return PlotGraph(
            format="short-story",
            chapters=chapters,
            scenes=scenes,
            characters=characters,
            locations=locations,
        )

    def _create_test_state(self) -> ProjectState:
        """Create a test project state."""
        characters = [
            Character(id="character-01", name="Alice", role="protagonist"),
            Character(id="character-02", name="Bob", role="antagonist"),
        ]
        locations = [WorldFact(id="location-01", type="location", name="Castle")]
        chapters = [Chapter(id="chapter-01", title="Opening", summary="The beginning")]
        scenes = [Scene(id="scene-01", summary="Alice enters the castle")]

        return ProjectState(
            characters=characters,
            locations=locations,
            chapters=chapters,
            scenes=scenes,
        )

    def test_build_scene_context_basic(self) -> None:
        """Test building basic scene context."""
        graph = self._create_test_graph()
        state = self._create_test_state()
        options = CreateOptions()

        scene_slot = graph.scenes[0]
        context = build_scene_context(scene_slot, graph, state, options)

        assert context.scene_id == "scene-01"
        assert context.chapter_id == "chapter-01"
        assert context.position_label == "early"

    def test_build_scene_context_filters_characters(self) -> None:
        """Test that context only includes scene characters."""
        graph = self._create_test_graph()
        state = self._create_test_state()
        options = CreateOptions()

        # Scene 1 only has character-01
        scene_slot = graph.scenes[0]
        context = build_scene_context(scene_slot, graph, state, options)

        assert len(context.characters) == 1
        assert context.characters[0].id == "character-01"

        # Scene 2 has both characters
        scene_slot = graph.scenes[1]
        context = build_scene_context(scene_slot, graph, state, options)

        assert len(context.characters) == 2

    def test_build_scene_context_includes_location(self) -> None:
        """Test that context includes the scene location."""
        graph = self._create_test_graph()
        state = self._create_test_state()
        options = CreateOptions()

        scene_slot = graph.scenes[0]
        context = build_scene_context(scene_slot, graph, state, options)

        assert context.location is not None
        assert context.location.id == "location-01"

    def test_build_scene_context_includes_beat_slots(self) -> None:
        """Test that context includes beat slots."""
        graph = self._create_test_graph()
        state = self._create_test_state()
        options = CreateOptions()

        scene_slot = graph.scenes[0]
        context = build_scene_context(scene_slot, graph, state, options)

        assert len(context.beat_slots) == 2
        assert context.beat_slots[0].id == "scene-01-beat-01"
        assert context.beat_slots[0].kind == "setup"

    def test_build_scene_context_includes_chapter_info(self) -> None:
        """Test that context includes chapter information."""
        graph = self._create_test_graph()
        state = self._create_test_state()
        options = CreateOptions()

        scene_slot = graph.scenes[0]
        context = build_scene_context(scene_slot, graph, state, options)

        assert context.chapter_title == "Opening"
        assert context.chapter_summary == "The beginning"
        assert context.position_in_chapter == 0
        assert context.total_scenes_in_chapter == 2

    def test_build_scene_context_previous_summaries(self) -> None:
        """Test that context includes previous scene summaries."""
        graph = self._create_test_graph()
        state = self._create_test_state()
        options = CreateOptions()

        # First scene has no previous summaries
        context = build_scene_context(graph.scenes[0], graph, state, options)
        assert len(context.previous_scene_summaries) == 0

        # Second scene has one previous summary
        context = build_scene_context(graph.scenes[1], graph, state, options)
        assert len(context.previous_scene_summaries) == 1
        assert "Alice enters the castle" in context.previous_scene_summaries[0]

    def test_build_scene_context_sliding_window(self) -> None:
        """Test that sliding window limits previous summaries."""
        # Create graph with more scenes
        scenes = [SceneSlot(id=f"scene-{i:02d}", position=i - 1) for i in range(1, 11)]
        graph = PlotGraph(format="short-story", scenes=scenes)

        # Create state with scene summaries
        state_scenes = [Scene(id=f"scene-{i:02d}", summary=f"Summary {i}") for i in range(1, 10)]
        state = ProjectState(scenes=state_scenes)

        # Test with sliding window of 3
        options = CreateOptions(sliding_window_scenes=3)
        context = build_scene_context(graph.scenes[9], graph, state, options)

        # Should only include last 3 summaries
        assert len(context.previous_scene_summaries) <= 3

    def test_build_scene_context_global_position(self) -> None:
        """Test that context includes global position info."""
        graph = self._create_test_graph()
        state = self._create_test_state()
        options = CreateOptions()

        context = build_scene_context(graph.scenes[0], graph, state, options)
        assert context.position_in_story == 0
        assert context.total_scenes == 2

        context = build_scene_context(graph.scenes[1], graph, state, options)
        assert context.position_in_story == 1
        assert context.total_scenes == 2


class TestBuildCharacterContext:
    """Test build_character_context function."""

    def test_build_character_context_basic(self) -> None:
        """Test building basic character context."""
        slot = CharacterSlot(id="character-01", role="protagonist")
        style = StyleOutput(pov="third", tense="past")
        state = ProjectState()

        context = build_character_context(slot, "A story premise", style, state)

        assert context.character_slot.id == "character-01"
        assert context.character_slot.role == "protagonist"
        assert context.premise == "A story premise"
        assert context.style == style
        assert context.existing_character_names == []

    def test_build_character_context_with_existing_characters(self) -> None:
        """Test that context includes existing character names."""
        slot = CharacterSlot(id="character-02", role="antagonist")
        style = StyleOutput()
        characters = [
            Character(id="character-01", name="Alice"),
        ]
        state = ProjectState(characters=characters)

        context = build_character_context(slot, "A story premise", style, state)

        assert context.existing_character_names == ["Alice"]

    def test_build_character_context_with_shape_info(self) -> None:
        """Test that context includes shape slot information."""
        slot = CharacterSlot(
            id="character-01",
            role="mentor",
            shape_slot_id="wise-guide",
            needs="Someone who provides wisdom",
        )
        style = StyleOutput()
        state = ProjectState()

        context = build_character_context(slot, "A story premise", style, state)

        assert context.character_slot.shape_slot_id == "wise-guide"
        assert context.character_slot.needs == "Someone who provides wisdom"


class TestBuildLocationContext:
    """Test build_location_context function."""

    def test_build_location_context_basic(self) -> None:
        """Test building basic location context."""
        slot = LocationSlot(id="location-01")
        style = StyleOutput(pov="third", tense="past")
        state = ProjectState()

        context = build_location_context(slot, "A story premise", style, state)

        assert context.location_slot.id == "location-01"
        assert context.premise == "A story premise"
        assert context.style == style
        assert context.existing_location_names == []

    def test_build_location_context_with_existing_locations(self) -> None:
        """Test that context includes existing location names."""
        slot = LocationSlot(id="location-02")
        style = StyleOutput()
        locations = [
            WorldFact(id="location-01", type="location", name="Castle"),
        ]
        state = ProjectState(locations=locations)

        context = build_location_context(slot, "A story premise", style, state)

        assert context.existing_location_names == ["Castle"]


class TestSceneContext:
    """Test SceneContext dataclass."""

    def test_scene_context_instantiation(self) -> None:
        """Test SceneContext can be instantiated."""
        scene_slot = SceneSlot(id="scene-01")
        context = SceneContext(
            scene_id="scene-01",
            scene_slot=scene_slot,
            chapter_id="chapter-01",
            chapter_title="Opening",
            chapter_summary="The beginning",
            position_in_chapter=0,
            total_scenes_in_chapter=3,
            characters=[],
            location=None,
            relevant_world_facts=[],
            beat_slots=[],
            previous_scene_summaries=[],
            position_in_story=0,
            total_scenes=5,
            position_label="early",
        )

        assert context.scene_id == "scene-01"
        assert context.chapter_id == "chapter-01"
        assert context.chapter_title == "Opening"


class TestCharacterContext:
    """Test CharacterContext dataclass."""

    def test_character_context_instantiation(self) -> None:
        """Test CharacterContext can be instantiated."""
        slot = CharacterSlot(id="character-01", role="protagonist")
        style = StyleOutput()
        context = CharacterContext(
            character_slot=slot,
            premise="A story premise",
            style=style,
            existing_character_names=["Alice", "Bob"],
        )

        assert context.character_slot.id == "character-01"
        assert context.premise == "A story premise"
        assert context.existing_character_names == ["Alice", "Bob"]


class TestLocationContext:
    """Test LocationContext dataclass."""

    def test_location_context_instantiation(self) -> None:
        """Test LocationContext can be instantiated."""
        slot = LocationSlot(id="location-01")
        style = StyleOutput()
        context = LocationContext(
            location_slot=slot,
            premise="A story premise",
            style=style,
            existing_location_names=["Castle"],
        )

        assert context.location_slot.id == "location-01"
        assert context.premise == "A story premise"
        assert context.existing_location_names == ["Castle"]


class TestChapterContext:
    """Test ChapterContext dataclass."""

    def test_chapter_context_instantiation(self) -> None:
        """Test ChapterContext can be instantiated."""
        style = StyleOutput()
        context = ChapterContext(
            chapter_id="chapter-01",
            position=0,
            total_chapters=5,
            scene_count=3,
            premise="A story premise",
            style=style,
            previous_chapter_summaries=["Previous chapter summary"],
        )

        assert context.chapter_id == "chapter-01"
        assert context.position == 0
        assert context.total_chapters == 5
        assert context.scene_count == 3
        assert context.previous_chapter_summaries == ["Previous chapter summary"]
