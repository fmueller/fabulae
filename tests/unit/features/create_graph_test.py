"""Tests for plot graph data structures."""

from __future__ import annotations

from fabulae.features.create.graph import (
    BeatSlot,
    ChapterSlot,
    CharacterSlot,
    LocationSlot,
    PlotGraph,
    SceneSlot,
    WorldFactSlot,
)


class TestBeatSlot:
    """Test BeatSlot dataclass."""

    def test_beat_slot_basic_instantiation(self) -> None:
        """Test BeatSlot with minimal required fields."""
        beat = BeatSlot(id="scene-01-beat-01", kind="action")

        assert beat.id == "scene-01-beat-01"
        assert beat.kind == "action"
        assert beat.required is False
        assert beat.shape_beat_type is None

    def test_beat_slot_full_instantiation(self) -> None:
        """Test BeatSlot with all fields populated."""
        beat = BeatSlot(
            id="scene-01-beat-02",
            kind="revelation",
            required=True,
            shape_beat_type="discovery",
        )

        assert beat.id == "scene-01-beat-02"
        assert beat.kind == "revelation"
        assert beat.required is True
        assert beat.shape_beat_type == "discovery"


class TestSceneSlot:
    """Test SceneSlot dataclass."""

    def test_scene_slot_basic_instantiation(self) -> None:
        """Test SceneSlot with minimal required fields."""
        scene = SceneSlot(id="scene-01")

        assert scene.id == "scene-01"
        assert scene.chapter_id is None
        assert scene.beat_slots == []
        assert scene.character_ids == []
        assert scene.location_id is None
        assert scene.time is None
        assert scene.position == 0
        assert scene.position_label == "middle"

    def test_scene_slot_full_instantiation(self) -> None:
        """Test SceneSlot with all fields populated."""
        beat_slots = [
            BeatSlot(id="scene-01-beat-01", kind="setup"),
            BeatSlot(id="scene-01-beat-02", kind="turn"),
        ]
        scene = SceneSlot(
            id="scene-03",
            chapter_id="chapter-01",
            beat_slots=beat_slots,
            character_ids=["character-01", "character-02"],
            location_id="location-01",
            time="night",
            position=2,
            position_label="climax",
        )

        assert scene.id == "scene-03"
        assert scene.chapter_id == "chapter-01"
        assert len(scene.beat_slots) == 2
        assert scene.character_ids == ["character-01", "character-02"]
        assert scene.location_id == "location-01"
        assert scene.time == "night"
        assert scene.position == 2
        assert scene.position_label == "climax"


class TestChapterSlot:
    """Test ChapterSlot dataclass."""

    def test_chapter_slot_basic_instantiation(self) -> None:
        """Test ChapterSlot with minimal required fields."""
        chapter = ChapterSlot(id="chapter-01")

        assert chapter.id == "chapter-01"
        assert chapter.scene_ids == []
        assert chapter.position == 0

    def test_chapter_slot_with_scenes(self) -> None:
        """Test ChapterSlot with scene IDs."""
        chapter = ChapterSlot(
            id="chapter-02",
            scene_ids=["scene-03", "scene-04", "scene-05"],
            position=1,
        )

        assert chapter.id == "chapter-02"
        assert chapter.scene_ids == ["scene-03", "scene-04", "scene-05"]
        assert chapter.position == 1


class TestCharacterSlot:
    """Test CharacterSlot dataclass."""

    def test_character_slot_basic_instantiation(self) -> None:
        """Test CharacterSlot with minimal required fields."""
        char = CharacterSlot(id="character-01", role="protagonist")

        assert char.id == "character-01"
        assert char.role == "protagonist"
        assert char.shape_slot_id is None
        assert char.needs is None

    def test_character_slot_from_shape(self) -> None:
        """Test CharacterSlot derived from story shape."""
        char = CharacterSlot(
            id="character-02",
            role="mentor",
            shape_slot_id="wise-guide",
            needs="Someone who provides guidance to the hero",
        )

        assert char.id == "character-02"
        assert char.role == "mentor"
        assert char.shape_slot_id == "wise-guide"
        assert char.needs == "Someone who provides guidance to the hero"


class TestLocationSlot:
    """Test LocationSlot dataclass."""

    def test_location_slot_basic_instantiation(self) -> None:
        """Test LocationSlot with minimal required fields."""
        loc = LocationSlot(id="location-01")

        assert loc.id == "location-01"
        assert loc.shape_setting_id is None
        assert loc.needs is None

    def test_location_slot_from_shape(self) -> None:
        """Test LocationSlot derived from story shape."""
        loc = LocationSlot(
            id="location-02",
            shape_setting_id="sanctuary",
            needs="A safe place for refuge and recovery",
        )

        assert loc.id == "location-02"
        assert loc.shape_setting_id == "sanctuary"
        assert loc.needs == "A safe place for refuge and recovery"


class TestWorldFactSlot:
    """Test WorldFactSlot dataclass."""

    def test_world_fact_slot_default_type(self) -> None:
        """Test WorldFactSlot with default fact type."""
        fact = WorldFactSlot(id="world-fact-01")

        assert fact.id == "world-fact-01"
        assert fact.fact_type == "culture"

    def test_world_fact_slot_custom_type(self) -> None:
        """Test WorldFactSlot with custom fact type."""
        fact = WorldFactSlot(id="world-fact-02", fact_type="history")

        assert fact.id == "world-fact-02"
        assert fact.fact_type == "history"


class TestPlotGraph:
    """Test PlotGraph dataclass and methods."""

    def test_plot_graph_empty_instantiation(self) -> None:
        """Test PlotGraph with no content."""
        graph = PlotGraph(format="short-story")

        assert graph.format == "short-story"
        assert graph.chapters == []
        assert graph.scenes == []
        assert graph.characters == []
        assert graph.locations == []
        assert graph.world_facts == []
        assert graph.seed is None

    def test_plot_graph_full_instantiation(self) -> None:
        """Test PlotGraph with all content."""
        chapters = [
            ChapterSlot(id="chapter-01", scene_ids=["scene-01", "scene-02"]),
            ChapterSlot(id="chapter-02", scene_ids=["scene-03"]),
        ]
        scenes = [
            SceneSlot(id="scene-01", chapter_id="chapter-01"),
            SceneSlot(id="scene-02", chapter_id="chapter-01"),
            SceneSlot(id="scene-03", chapter_id="chapter-02"),
        ]
        characters = [
            CharacterSlot(id="character-01", role="protagonist"),
            CharacterSlot(id="character-02", role="antagonist"),
        ]
        locations = [LocationSlot(id="location-01")]

        graph = PlotGraph(
            format="novella",
            chapters=chapters,
            scenes=scenes,
            characters=characters,
            locations=locations,
            seed=42,
        )

        assert graph.format == "novella"
        assert len(graph.chapters) == 2
        assert len(graph.scenes) == 3
        assert len(graph.characters) == 2
        assert len(graph.locations) == 1
        assert graph.seed == 42

    def test_get_scene_found(self) -> None:
        """Test get_scene returns scene when found."""
        scenes = [
            SceneSlot(id="scene-01"),
            SceneSlot(id="scene-02"),
            SceneSlot(id="scene-03"),
        ]
        graph = PlotGraph(format="short-story", scenes=scenes)

        scene = graph.get_scene("scene-02")
        assert scene is not None
        assert scene.id == "scene-02"

    def test_get_scene_not_found(self) -> None:
        """Test get_scene returns None when not found."""
        scenes = [SceneSlot(id="scene-01")]
        graph = PlotGraph(format="short-story", scenes=scenes)

        scene = graph.get_scene("scene-99")
        assert scene is None

    def test_get_chapter_found(self) -> None:
        """Test get_chapter returns chapter when found."""
        chapters = [
            ChapterSlot(id="chapter-01"),
            ChapterSlot(id="chapter-02"),
        ]
        graph = PlotGraph(format="novella", chapters=chapters)

        chapter = graph.get_chapter("chapter-01")
        assert chapter is not None
        assert chapter.id == "chapter-01"

    def test_get_chapter_not_found(self) -> None:
        """Test get_chapter returns None when not found."""
        chapters = [ChapterSlot(id="chapter-01")]
        graph = PlotGraph(format="novella", chapters=chapters)

        chapter = graph.get_chapter("chapter-99")
        assert chapter is None

    def test_get_chapter_scenes(self) -> None:
        """Test get_chapter_scenes returns correct scenes."""
        scenes = [
            SceneSlot(id="scene-01", chapter_id="chapter-01"),
            SceneSlot(id="scene-02", chapter_id="chapter-01"),
            SceneSlot(id="scene-03", chapter_id="chapter-02"),
            SceneSlot(id="scene-04", chapter_id="chapter-02"),
            SceneSlot(id="scene-05", chapter_id="chapter-02"),
        ]
        graph = PlotGraph(format="novella", scenes=scenes)

        chapter_1_scenes = graph.get_chapter_scenes("chapter-01")
        chapter_2_scenes = graph.get_chapter_scenes("chapter-02")

        assert len(chapter_1_scenes) == 2
        assert chapter_1_scenes[0].id == "scene-01"
        assert chapter_1_scenes[1].id == "scene-02"

        assert len(chapter_2_scenes) == 3
        assert chapter_2_scenes[0].id == "scene-03"

    def test_get_scene_characters(self) -> None:
        """Test get_scene_characters returns character IDs."""
        scenes = [
            SceneSlot(id="scene-01", character_ids=["character-01", "character-02"]),
            SceneSlot(id="scene-02", character_ids=["character-01"]),
        ]
        graph = PlotGraph(format="short-story", scenes=scenes)

        chars = graph.get_scene_characters("scene-01")
        assert chars == ["character-01", "character-02"]

        chars = graph.get_scene_characters("scene-02")
        assert chars == ["character-01"]

    def test_get_scene_characters_empty(self) -> None:
        """Test get_scene_characters returns empty list for unknown scene."""
        graph = PlotGraph(format="short-story")

        chars = graph.get_scene_characters("scene-99")
        assert chars == []

    def test_get_scene_position(self) -> None:
        """Test get_scene_position returns correct index."""
        scenes = [
            SceneSlot(id="scene-01"),
            SceneSlot(id="scene-02"),
            SceneSlot(id="scene-03"),
        ]
        graph = PlotGraph(format="short-story", scenes=scenes)

        assert graph.get_scene_position("scene-01") == 0
        assert graph.get_scene_position("scene-02") == 1
        assert graph.get_scene_position("scene-03") == 2
        assert graph.get_scene_position("scene-99") == -1

    def test_get_previous_scene(self) -> None:
        """Test get_previous_scene returns correct scene."""
        scenes = [
            SceneSlot(id="scene-01"),
            SceneSlot(id="scene-02"),
            SceneSlot(id="scene-03"),
        ]
        graph = PlotGraph(format="short-story", scenes=scenes)

        prev = graph.get_previous_scene("scene-01")
        assert prev is None

        prev = graph.get_previous_scene("scene-02")
        assert prev is not None
        assert prev.id == "scene-01"

        prev = graph.get_previous_scene("scene-03")
        assert prev is not None
        assert prev.id == "scene-02"

    def test_get_character(self) -> None:
        """Test get_character returns correct character."""
        characters = [
            CharacterSlot(id="character-01", role="protagonist"),
            CharacterSlot(id="character-02", role="antagonist"),
        ]
        graph = PlotGraph(format="short-story", characters=characters)

        char = graph.get_character("character-01")
        assert char is not None
        assert char.role == "protagonist"

        char = graph.get_character("character-99")
        assert char is None

    def test_get_location(self) -> None:
        """Test get_location returns correct location."""
        locations = [
            LocationSlot(id="location-01", needs="A home base"),
            LocationSlot(id="location-02", needs="A dangerous place"),
        ]
        graph = PlotGraph(format="short-story", locations=locations)

        loc = graph.get_location("location-01")
        assert loc is not None
        assert loc.needs == "A home base"

        loc = graph.get_location("location-99")
        assert loc is None

    def test_total_beats(self) -> None:
        """Test total_beats counts all beats across scenes."""
        scenes = [
            SceneSlot(
                id="scene-01",
                beat_slots=[
                    BeatSlot(id="scene-01-beat-01", kind="setup"),
                    BeatSlot(id="scene-01-beat-02", kind="turn"),
                ],
            ),
            SceneSlot(
                id="scene-02",
                beat_slots=[
                    BeatSlot(id="scene-02-beat-01", kind="escalation"),
                    BeatSlot(id="scene-02-beat-02", kind="resolution"),
                    BeatSlot(id="scene-02-beat-03", kind="bridge"),
                ],
            ),
        ]
        graph = PlotGraph(format="short-story", scenes=scenes)

        assert graph.total_beats() == 5

    def test_total_beats_empty(self) -> None:
        """Test total_beats returns 0 for empty graph."""
        graph = PlotGraph(format="short-story")
        assert graph.total_beats() == 0

    def test_to_summary(self) -> None:
        """Test to_summary generates readable output."""
        chapters = [ChapterSlot(id="chapter-01")]
        scenes = [
            SceneSlot(
                id="scene-01",
                beat_slots=[BeatSlot(id="scene-01-beat-01", kind="setup")],
            ),
        ]
        characters = [CharacterSlot(id="character-01", role="protagonist")]
        locations = [LocationSlot(id="location-01")]

        graph = PlotGraph(
            format="novel",
            chapters=chapters,
            scenes=scenes,
            characters=characters,
            locations=locations,
            seed=42,
        )

        summary = graph.to_summary()

        assert "PlotGraph (novel)" in summary
        assert "Chapters: 1" in summary
        assert "Scenes: 1" in summary
        assert "Total beats: 1" in summary
        assert "Characters: 1" in summary
        assert "Locations: 1" in summary
        assert "Seed: 42" in summary

    def test_to_summary_no_seed(self) -> None:
        """Test to_summary without seed."""
        graph = PlotGraph(format="short-story")
        summary = graph.to_summary()

        assert "Seed" not in summary
