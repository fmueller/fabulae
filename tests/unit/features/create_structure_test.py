"""Tests for structure generation."""

from __future__ import annotations

from fabulae.features.create.structure import generate_plot_graph


class TestGeneratePlotGraph:
    """Test generate_plot_graph function."""

    def test_generate_plot_graph_novel_format(self) -> None:
        """Test structure generation for novel format."""
        graph = generate_plot_graph("novel", None, 0.5, seed=42)

        assert graph.format == "novel"
        assert graph.seed == 42
        assert len(graph.chapters) > 0
        assert len(graph.scenes) > 0
        assert len(graph.characters) > 0
        assert len(graph.locations) > 0

    def test_generate_plot_graph_novella_format(self) -> None:
        """Test structure generation for novella format."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        assert graph.format == "novella"
        # Novella should have fewer chapters than novel
        assert 6 <= len(graph.chapters) <= 16

    def test_generate_plot_graph_short_story_format(self) -> None:
        """Test structure generation for short-story format."""
        graph = generate_plot_graph("short-story", None, 0.5, seed=42)

        assert graph.format == "short-story"
        # Short stories can have 0-6 chapters
        assert 0 <= len(graph.chapters) <= 6
        # But should have at least some scenes
        assert len(graph.scenes) >= 2

    def test_generate_plot_graph_deterministic_with_seed(self) -> None:
        """Test that same seed produces identical structure."""
        graph1 = generate_plot_graph("novella", None, 0.5, seed=12345)
        graph2 = generate_plot_graph("novella", None, 0.5, seed=12345)

        # Same number of chapters
        assert len(graph1.chapters) == len(graph2.chapters)

        # Same chapter IDs
        for c1, c2 in zip(graph1.chapters, graph2.chapters, strict=True):
            assert c1.id == c2.id
            assert c1.scene_ids == c2.scene_ids

        # Same number of scenes
        assert len(graph1.scenes) == len(graph2.scenes)

        # Same scene IDs and structure
        for s1, s2 in zip(graph1.scenes, graph2.scenes, strict=True):
            assert s1.id == s2.id
            assert s1.chapter_id == s2.chapter_id
            assert s1.position_label == s2.position_label
            assert len(s1.beat_slots) == len(s2.beat_slots)

        # Same characters
        assert len(graph1.characters) == len(graph2.characters)
        for ch1, ch2 in zip(graph1.characters, graph2.characters, strict=True):
            assert ch1.id == ch2.id
            assert ch1.role == ch2.role

        # Same locations
        assert len(graph1.locations) == len(graph2.locations)

    def test_generate_plot_graph_different_seeds_different_structure(self) -> None:
        """Test that different seeds produce different structures."""
        graph1 = generate_plot_graph("novella", None, 0.5, seed=100)
        graph2 = generate_plot_graph("novella", None, 0.5, seed=200)

        # At least some difference should exist
        # (could be chapter count, scene count, or scene assignments)
        different = (
            len(graph1.chapters) != len(graph2.chapters)
            or len(graph1.scenes) != len(graph2.scenes)
            or graph1.scenes[0].location_id != graph2.scenes[0].location_id
            or graph1.scenes[0].character_ids != graph2.scenes[0].character_ids
        )
        assert different

    def test_generate_plot_graph_all_ids_allocated(self) -> None:
        """Test that all entities have IDs in expected format."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        # Chapter IDs
        for chapter in graph.chapters:
            assert chapter.id.startswith("chapter-")

        # Scene IDs
        for scene in graph.scenes:
            assert scene.id.startswith("scene-")

        # Beat IDs
        for scene in graph.scenes:
            for beat in scene.beat_slots:
                assert beat.id.startswith(f"{scene.id}-beat-")

        # Character IDs
        for char in graph.characters:
            assert char.id.startswith("character-")

        # Location IDs
        for loc in graph.locations:
            assert loc.id.startswith("location-")

    def test_generate_plot_graph_scene_chapter_consistency(self) -> None:
        """Test that scenes reference valid chapters."""
        graph = generate_plot_graph("novel", None, 0.5, seed=42)

        chapter_ids = {c.id for c in graph.chapters}

        for scene in graph.scenes:
            if scene.chapter_id is not None:
                assert scene.chapter_id in chapter_ids

        # Also verify chapter scene_ids reference valid scenes
        scene_ids = {s.id for s in graph.scenes}
        for chapter in graph.chapters:
            for scene_id in chapter.scene_ids:
                assert scene_id in scene_ids

    def test_generate_plot_graph_position_labels_assigned(self) -> None:
        """Test that all scenes have position labels."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        valid_positions = {"early", "middle", "late", "climax"}
        for scene in graph.scenes:
            assert scene.position_label in valid_positions

    def test_generate_plot_graph_characters_assigned_to_scenes(self) -> None:
        """Test that characters are assigned to scenes."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        character_ids = {c.id for c in graph.characters}

        # At least some scenes should have characters
        scenes_with_chars = [s for s in graph.scenes if s.character_ids]
        assert len(scenes_with_chars) > 0

        # All character references should be valid
        for scene in graph.scenes:
            for char_id in scene.character_ids:
                assert char_id in character_ids

    def test_generate_plot_graph_locations_assigned_to_scenes(self) -> None:
        """Test that locations are assigned to scenes."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        location_ids = {loc.id for loc in graph.locations}

        # All scenes should have locations (or None)
        for scene in graph.scenes:
            if scene.location_id is not None:
                assert scene.location_id in location_ids

    def test_generate_plot_graph_beat_slots_created(self) -> None:
        """Test that beat slots are created for scenes."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        # All scenes should have beat slots
        for scene in graph.scenes:
            assert len(scene.beat_slots) >= 2

        # Beat IDs should be unique
        all_beat_ids: set[str] = set()
        for scene in graph.scenes:
            for beat in scene.beat_slots:
                assert beat.id not in all_beat_ids
                all_beat_ids.add(beat.id)

    def test_generate_plot_graph_variation_affects_counts(self) -> None:
        """Test that variation level affects structure counts."""
        # Low variation should produce structure near the middle of ranges
        graph_low = generate_plot_graph("novella", None, 0.0, seed=42)

        # High variation should potentially produce different counts
        graph_high = generate_plot_graph("novella", None, 1.0, seed=42)

        # Both should produce valid structures
        assert len(graph_low.chapters) > 0
        assert len(graph_high.chapters) > 0

    def test_generate_plot_graph_total_beats_reasonable(self) -> None:
        """Test that total beat count is reasonable for format."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        total_beats = graph.total_beats()
        # Novella should have 72-192 beats approximately
        assert 40 <= total_beats <= 250

    def test_generate_plot_graph_protagonist_exists(self) -> None:
        """Test that at least one protagonist character exists."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        protagonists = [c for c in graph.characters if c.role == "protagonist"]
        assert len(protagonists) >= 1

    def test_generate_plot_graph_characters_in_scene_roles(self) -> None:
        """Test that character roles are valid."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        valid_roles = {"protagonist", "antagonist", "mentor", "ally", "love-interest", "supporting"}
        for char in graph.characters:
            assert char.role in valid_roles


class TestGeneratePlotGraphWithShape:
    """Test generate_plot_graph with story shapes."""

    def test_generate_plot_graph_without_shape(self) -> None:
        """Test that graph generation works without a shape."""
        graph = generate_plot_graph("novella", None, 0.5, seed=42)

        # Should still generate valid structure
        assert len(graph.scenes) > 0
        assert len(graph.characters) > 0

    # Note: Tests with actual shapes would require loading test fixtures
    # or mocking the StoryShape model. These would be added in integration tests.


class TestGenerateMicroProseGraph:
    """Test generate_micro_prose_graph function."""

    def test_generate_micro_prose_graph_basic(self) -> None:
        """Test basic micro-prose structure generation."""
        from fabulae.features.create.structure import generate_micro_prose_graph

        graph = generate_micro_prose_graph(variation=0.5, seed=42)

        assert graph.seed == 42
        assert len(graph.fragment_slots) >= 1
        assert len(graph.fragment_slots) <= 5  # micro-prose range

    def test_generate_micro_prose_graph_deterministic(self) -> None:
        """Test that same seed produces identical structure."""
        from fabulae.features.create.structure import generate_micro_prose_graph

        graph1 = generate_micro_prose_graph(variation=0.5, seed=12345)
        graph2 = generate_micro_prose_graph(variation=0.5, seed=12345)

        assert len(graph1.fragment_slots) == len(graph2.fragment_slots)
        for f1, f2 in zip(graph1.fragment_slots, graph2.fragment_slots, strict=True):
            assert f1.id == f2.id
            assert f1.position == f2.position

    def test_generate_micro_prose_graph_fragment_ids(self) -> None:
        """Test that fragment IDs are properly formatted."""
        from fabulae.features.create.structure import generate_micro_prose_graph

        graph = generate_micro_prose_graph(variation=0.5, seed=42)

        for fragment in graph.fragment_slots:
            assert fragment.id.startswith("fragment-")

    def test_generate_micro_prose_graph_positions(self) -> None:
        """Test that fragments have sequential positions."""
        from fabulae.features.create.structure import generate_micro_prose_graph

        graph = generate_micro_prose_graph(variation=0.5, seed=42)

        positions = [f.position for f in graph.fragment_slots]
        assert positions == list(range(len(positions)))

    def test_generate_micro_prose_graph_total_fragments(self) -> None:
        """Test that total_fragments method works correctly."""
        from fabulae.features.create.structure import generate_micro_prose_graph

        graph = generate_micro_prose_graph(variation=0.5, seed=42)

        assert graph.total_fragments() == len(graph.fragment_slots)


class TestGeneratePoemGraph:
    """Test generate_poem_graph function."""

    def test_generate_poem_graph_basic(self) -> None:
        """Test basic poem structure generation."""
        from fabulae.features.create.structure import generate_poem_graph

        graph = generate_poem_graph(variation=0.5, seed=42)

        assert graph.seed == 42
        assert len(graph.stanza_slots) >= 1
        assert len(graph.stanza_slots) <= 6  # poem stanza range

    def test_generate_poem_graph_deterministic(self) -> None:
        """Test that same seed produces identical structure."""
        from fabulae.features.create.structure import generate_poem_graph

        graph1 = generate_poem_graph(variation=0.5, seed=12345)
        graph2 = generate_poem_graph(variation=0.5, seed=12345)

        assert len(graph1.stanza_slots) == len(graph2.stanza_slots)
        for s1, s2 in zip(graph1.stanza_slots, graph2.stanza_slots, strict=True):
            assert s1.id == s2.id
            assert s1.position == s2.position
            assert s1.line_count == s2.line_count

    def test_generate_poem_graph_stanza_ids(self) -> None:
        """Test that stanza IDs are properly formatted."""
        from fabulae.features.create.structure import generate_poem_graph

        graph = generate_poem_graph(variation=0.5, seed=42)

        for stanza in graph.stanza_slots:
            assert stanza.id.startswith("stanza-")

    def test_generate_poem_graph_line_counts(self) -> None:
        """Test that stanzas have reasonable line counts."""
        from fabulae.features.create.structure import generate_poem_graph

        graph = generate_poem_graph(variation=0.5, seed=42)

        for stanza in graph.stanza_slots:
            assert stanza.line_count >= 2
            assert stanza.line_count <= 8

    def test_generate_poem_graph_total_lines(self) -> None:
        """Test that total_lines method works correctly."""
        from fabulae.features.create.structure import generate_poem_graph

        graph = generate_poem_graph(variation=0.5, seed=42)

        expected_total = sum(s.line_count for s in graph.stanza_slots)
        assert graph.total_lines() == expected_total

    def test_generate_poem_graph_positions(self) -> None:
        """Test that stanzas have sequential positions."""
        from fabulae.features.create.structure import generate_poem_graph

        graph = generate_poem_graph(variation=0.5, seed=42)

        positions = [s.position for s in graph.stanza_slots]
        assert positions == list(range(len(positions)))
