"""Tests for character assignment variation in structure.py."""

import random

from fabulae.features.create.graph import CharacterSlot, PlotGraph, SceneSlot
from fabulae.features.create.structure import (
    _assign_characters_to_scenes,
    _get_character_count_range,
    _weighted_character_selection,
)


class TestGetCharacterCountRange:
    """Tests for _get_character_count_range function."""

    def test_early_scenes_favor_fewer_characters(self) -> None:
        """Test that early scenes get smaller character ranges."""
        rng = random.Random(42)
        min_chars, max_chars = _get_character_count_range("early", 0.1, 5, rng)
        assert min_chars >= 1
        assert max_chars <= 3  # Early should cap at 2, maybe 3 with middle boost

    def test_climax_scenes_favor_more_characters(self) -> None:
        """Test that climax scenes get larger character ranges."""
        rng = random.Random(42)
        min_chars, max_chars = _get_character_count_range("climax", 0.95, 5, rng)
        assert min_chars >= 3
        assert max_chars >= 3

    def test_middle_progress_increases_max(self) -> None:
        """Test that middle of story (0.3-0.7 progress) increases max."""
        rng = random.Random(42)
        early_min, early_max = _get_character_count_range("middle", 0.1, 5, rng)
        mid_min, mid_max = _get_character_count_range("middle", 0.5, 5, rng)
        # Middle progress should give slightly higher max
        assert mid_max >= early_max

    def test_respects_available_character_limit(self) -> None:
        """Test that max doesn't exceed available characters."""
        rng = random.Random(42)
        min_chars, max_chars = _get_character_count_range("climax", 0.9, 2, rng)
        assert max_chars <= 2

    def test_min_never_exceeds_max(self) -> None:
        """Test that min is always <= max."""
        rng = random.Random(42)
        for position in ["early", "middle", "late", "climax"]:
            for total in [1, 2, 3, 5, 10]:
                for progress in [0.0, 0.25, 0.5, 0.75, 1.0]:
                    min_c, max_c = _get_character_count_range(position, progress, total, rng)
                    assert min_c <= max_c, f"min {min_c} > max {max_c} for {position}, {total}, {progress}"


class TestWeightedCharacterSelection:
    """Tests for _weighted_character_selection function."""

    def test_selects_requested_count(self) -> None:
        """Test that correct number of characters are selected."""
        rng = random.Random(42)
        available = ["char-01", "char-02", "char-03", "char-04"]
        counts = {c: 0 for c in available}
        selected = _weighted_character_selection(available, 2, counts, rng)
        assert len(selected) == 2

    def test_prefers_less_appeared_characters(self) -> None:
        """Test that selection favors characters with fewer appearances."""
        # Run multiple times to check statistical preference
        rng = random.Random(42)
        available = ["char-01", "char-02", "char-03"]
        counts = {"char-01": 5, "char-02": 0, "char-03": 5}  # char-02 should be preferred

        selection_counts = {"char-01": 0, "char-02": 0, "char-03": 0}
        for _ in range(100):
            rng = random.Random(_ * 13)  # Different seed each time
            selected = _weighted_character_selection(available, 1, counts, rng)
            for c in selected:
                selection_counts[c] += 1

        # char-02 (with 0 appearances) should be selected most often
        assert selection_counts["char-02"] > selection_counts["char-01"]
        assert selection_counts["char-02"] > selection_counts["char-03"]

    def test_handles_empty_available(self) -> None:
        """Test that empty available list returns empty."""
        rng = random.Random(42)
        selected = _weighted_character_selection([], 3, {}, rng)
        assert selected == []

    def test_handles_zero_count(self) -> None:
        """Test that zero count returns empty."""
        rng = random.Random(42)
        available = ["char-01", "char-02"]
        selected = _weighted_character_selection(available, 0, {}, rng)
        assert selected == []

    def test_caps_at_available_count(self) -> None:
        """Test that selection doesn't exceed available characters."""
        rng = random.Random(42)
        available = ["char-01", "char-02"]
        selected = _weighted_character_selection(available, 5, {}, rng)
        assert len(selected) == 2  # Capped at available


class TestAssignCharactersToScenes:
    """Tests for _assign_characters_to_scenes function."""

    def _create_test_graph(self, num_scenes: int, num_characters: int) -> PlotGraph:
        """Helper to create a test PlotGraph."""
        graph = PlotGraph(format="novel", seed=42)

        # Create scenes with positions
        positions = ["early"] * (num_scenes // 4) + ["middle"] * (num_scenes // 2) + ["late"] * (num_scenes // 4)
        if num_scenes > 0:
            positions[-1] = "climax"

        for i in range(num_scenes):
            scene = SceneSlot(
                id=f"scene-{i+1:02d}",
                chapter_id=None,
                beat_slots=[],
                position=i,
            )
            scene.position_label = positions[i] if i < len(positions) else "middle"
            graph.scenes.append(scene)

        # Create characters
        roles = ["protagonist"] + ["supporting"] * (num_characters - 1) if num_characters > 0 else []
        for i, role in enumerate(roles):
            graph.characters.append(
                CharacterSlot(id=f"char-{i+1:02d}", role=role)
            )

        return graph

    def test_character_counts_vary_across_scenes(self) -> None:
        """Test that character counts are not uniform across all scenes."""
        graph = self._create_test_graph(10, 5)
        rng = random.Random(42)

        _assign_characters_to_scenes(graph, None, rng)

        # Collect character counts per scene
        counts = [len(scene.character_ids) for scene in graph.scenes]

        # Should have some variation (not all the same)
        assert len(set(counts)) > 1, f"All scenes have same character count: {counts}"

    def test_protagonist_appears_frequently(self) -> None:
        """Test that protagonist appears in most scenes."""
        graph = self._create_test_graph(10, 5)
        rng = random.Random(42)

        _assign_characters_to_scenes(graph, None, rng)

        protagonist_appearances = sum(
            1 for scene in graph.scenes if "char-01" in scene.character_ids
        )

        # Protagonist should appear in at least 70% of scenes
        assert protagonist_appearances >= 7, f"Protagonist only in {protagonist_appearances}/10 scenes"

    def test_solo_scenes_can_occur(self) -> None:
        """Test that some scenes may have only one character."""
        # Run multiple times to increase chance of hitting the 15% solo chance
        solo_found = False

        for seed in range(20):
            graph = self._create_test_graph(20, 5)
            rng = random.Random(seed)

            _assign_characters_to_scenes(graph, None, rng)

            for scene in graph.scenes:
                if len(scene.character_ids) == 1 and scene.position_label != "climax":
                    solo_found = True
                    break
            if solo_found:
                break

        assert solo_found, "No solo scenes found across multiple seeds"

    def test_climax_has_more_characters(self) -> None:
        """Test that climax scenes tend to have more characters."""
        climax_counts = []
        other_counts = []

        for seed in range(10):
            graph = self._create_test_graph(10, 5)
            rng = random.Random(seed)

            _assign_characters_to_scenes(graph, None, rng)

            for scene in graph.scenes:
                count = len(scene.character_ids)
                if scene.position_label == "climax":
                    climax_counts.append(count)
                else:
                    other_counts.append(count)

        avg_climax = sum(climax_counts) / len(climax_counts) if climax_counts else 0
        avg_other = sum(other_counts) / len(other_counts) if other_counts else 0

        # Climax should have higher average character count
        assert avg_climax >= avg_other, f"Climax avg ({avg_climax}) < other avg ({avg_other})"

    def test_handles_no_scenes(self) -> None:
        """Test that empty scene list is handled."""
        graph = self._create_test_graph(0, 5)
        rng = random.Random(42)

        # Should not raise
        _assign_characters_to_scenes(graph, None, rng)
        assert len(graph.scenes) == 0

    def test_handles_no_characters(self) -> None:
        """Test that empty character list is handled."""
        graph = self._create_test_graph(5, 0)
        rng = random.Random(42)

        # Should not raise
        _assign_characters_to_scenes(graph, None, rng)

        # All scenes should have empty character lists
        for scene in graph.scenes:
            assert scene.character_ids == []

    def test_deterministic_with_seed(self) -> None:
        """Test that same seed produces same results."""
        graph1 = self._create_test_graph(10, 5)
        graph2 = self._create_test_graph(10, 5)

        _assign_characters_to_scenes(graph1, None, random.Random(123))
        _assign_characters_to_scenes(graph2, None, random.Random(123))

        for s1, s2 in zip(graph1.scenes, graph2.scenes, strict=True):
            assert s1.character_ids == s2.character_ids, "Same seed produced different results"

    def test_different_seeds_produce_different_results(self) -> None:
        """Test that different seeds produce different results."""
        results = []

        for seed in [1, 2, 3]:
            graph = self._create_test_graph(10, 5)
            _assign_characters_to_scenes(graph, None, random.Random(seed))
            result = [tuple(scene.character_ids) for scene in graph.scenes]
            results.append(tuple(result))

        # At least some results should differ
        assert len(set(results)) > 1, "Different seeds produced identical results"
