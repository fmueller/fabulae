"""Tests for variation point selection and assignment from story shapes."""

from __future__ import annotations

import pytest

from fabulae.features.create.graph import BeatSlot
from fabulae.features.create.structure import generate_plot_graph
from fabulae.features.create.variation import (
    SelectedVariationPoint,
    VariationConfig,
    VariationEngine,
    assign_scene_positions,
)
from fabulae.models import StoryShape, VariationPoint


@pytest.fixture
def sample_shape() -> StoryShape:
    """Create a sample story shape with variation points for testing."""
    return StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A shape for testing variation points",
        character_slots=[],
        setting_slots=[],
        required_beats=[],
        variation_points=[
            VariationPoint(
                type="mentor-death",
                description="The mentor dies, forcing the hero to continue alone.",
                probability=0.4,
                position="middle",
            ),
            VariationPoint(
                type="ally-betrayal",
                description="An ally reveals hidden motives or is forced to betray.",
                probability=0.3,
                position="middle",
            ),
            VariationPoint(
                type="false-victory",
                description="The hero appears to win before the true ordeal.",
                probability=0.35,
                position="middle",
            ),
            VariationPoint(
                type="rescue-from-without",
                description="The hero needs help from allies to escape.",
                probability=0.5,
                position="late",
            ),
            VariationPoint(
                type="shadow-redeemed",
                description="The antagonist is transformed or redeemed.",
                probability=0.25,
                position="climax",
            ),
        ],
    )


@pytest.fixture
def shape_with_anywhere_position() -> StoryShape:
    """Create a shape with a variation point that can go anywhere."""
    return StoryShape(
        id="anywhere-shape",
        name="Anywhere Shape",
        description="Shape with anywhere position variation point",
        variation_points=[
            VariationPoint(
                type="flexible-beat",
                description="Can happen at any point in the narrative.",
                probability=1.0,  # Always selected
                position="anywhere",
            ),
        ],
    )


class TestVariationPointSelection:
    """Test that variation points are selected based on probability."""

    def test_selection_with_zero_probability(self) -> None:
        """Variation points with probability 0.0 should never be selected."""
        shape = StoryShape(
            id="zero-prob",
            name="Zero Prob",
            description="Test",
            variation_points=[
                VariationPoint(
                    type="never-selected",
                    description="Should never be selected",
                    probability=0.0,
                    position="middle",
                ),
            ],
        )
        config = VariationConfig(seed=42)
        engine = VariationEngine(shape, config)

        # Run selection many times to ensure it's never selected
        for _ in range(100):
            selected = engine._select_variation_points()
            assert len(selected) == 0, "Zero probability VP should never be selected"

    def test_selection_with_full_probability(self) -> None:
        """Variation points with probability 1.0 should always be selected."""
        shape = StoryShape(
            id="full-prob",
            name="Full Prob",
            description="Test",
            variation_points=[
                VariationPoint(
                    type="always-selected",
                    description="Should always be selected",
                    probability=1.0,
                    position="middle",
                ),
            ],
        )
        config = VariationConfig(seed=42)
        engine = VariationEngine(shape, config)

        # Run selection many times to ensure it's always selected
        for _ in range(100):
            # Need fresh engine for each test to reset RNG
            engine = VariationEngine(shape, VariationConfig(seed=None))
            selected = engine._select_variation_points()
            assert len(selected) == 1, "Full probability VP should always be selected"
            assert selected[0].type == "always-selected"

    def test_selection_preserves_metadata(self, sample_shape: StoryShape) -> None:
        """Selected variation points should preserve type, description, and position."""
        config = VariationConfig(seed=42)
        engine = VariationEngine(sample_shape, config)
        selected = engine._select_variation_points()

        for vp in selected:
            # Find matching variation point in shape
            shape_vp = next(
                (svp for svp in sample_shape.variation_points if svp.type == vp.type),
                None,
            )
            assert shape_vp is not None
            assert vp.description == shape_vp.description
            assert vp.position == shape_vp.position
            # assigned_scene_id should be None until assignment
            assert vp.assigned_scene_id is None

    def test_selection_without_shape(self) -> None:
        """Selection with None shape should return empty list."""
        config = VariationConfig(seed=42)
        engine = VariationEngine(None, config)
        selected = engine._select_variation_points()
        assert selected == []

    def test_selection_with_empty_variation_points(self) -> None:
        """Selection with empty variation_points should return empty list."""
        shape = StoryShape(
            id="empty",
            name="Empty",
            description="Test",
            variation_points=[],
        )
        config = VariationConfig(seed=42)
        engine = VariationEngine(shape, config)
        selected = engine._select_variation_points()
        assert selected == []


class TestVariationPointAssignment:
    """Test that variation points are assigned to appropriate scenes."""

    def test_assignment_respects_position(self) -> None:
        """Variation points should be assigned to scenes matching their position."""
        # Create variation points for different positions
        variation_points = [
            SelectedVariationPoint(
                type="early-beat",
                description="Early beat",
                position="early",
            ),
            SelectedVariationPoint(
                type="middle-beat",
                description="Middle beat",
                position="middle",
            ),
            SelectedVariationPoint(
                type="late-beat",
                description="Late beat",
                position="late",
            ),
            SelectedVariationPoint(
                type="climax-beat",
                description="Climax beat",
                position="climax",
            ),
        ]

        # Create scene positions (10 scenes)
        scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
        positions = assign_scene_positions(scene_ids)

        config = VariationConfig(seed=42)
        engine = VariationEngine(None, config)
        assigned = engine._assign_variation_points_to_scenes(variation_points, positions)

        # Check each assignment
        for vp in assigned:
            if vp.assigned_scene_id:
                scene_position = positions[vp.assigned_scene_id]
                assert scene_position == vp.position, (
                    f"VP with position {vp.position} assigned to scene with position {scene_position}"
                )

    def test_assignment_with_anywhere_position(
        self, shape_with_anywhere_position: StoryShape
    ) -> None:
        """Variation points with 'anywhere' position can go to any scene."""
        config = VariationConfig(seed=42)
        engine = VariationEngine(shape_with_anywhere_position, config)
        selected = engine._select_variation_points()

        scene_ids = [f"scene-{i:02d}" for i in range(1, 6)]
        positions = assign_scene_positions(scene_ids)

        assigned = engine._assign_variation_points_to_scenes(selected, positions)

        # Should be assigned to some scene
        assert len(assigned) == 1
        assert assigned[0].assigned_scene_id in scene_ids

    def test_assignment_with_no_matching_scenes(self) -> None:
        """Variation points with no matching scenes should remain unassigned."""
        variation_points = [
            SelectedVariationPoint(
                type="climax-beat",
                description="Climax beat",
                position="climax",
            ),
        ]

        # Create positions with no climax scenes (only 2 scenes -> early and climax)
        # Actually with 2 scenes, second is climax, so let's use single scene = climax
        # For truly no climax, we need to manipulate the positions dict directly
        positions = {
            "scene-01": "early",
            "scene-02": "middle",
        }

        config = VariationConfig(seed=42)
        engine = VariationEngine(None, config)
        assigned = engine._assign_variation_points_to_scenes(variation_points, positions)

        # Should remain unassigned since there's no climax scene
        assert assigned[0].assigned_scene_id is None

    def test_assignment_distributes_across_scenes(self) -> None:
        """Multiple variation points should prefer different scenes when possible."""
        # Create multiple variation points for the same position
        variation_points = [
            SelectedVariationPoint(type="vp-1", description="VP 1", position="middle"),
            SelectedVariationPoint(type="vp-2", description="VP 2", position="middle"),
            SelectedVariationPoint(type="vp-3", description="VP 3", position="middle"),
        ]

        # Create positions with multiple middle scenes
        positions = {
            "scene-01": "early",
            "scene-02": "middle",
            "scene-03": "middle",
            "scene-04": "middle",
            "scene-05": "late",
        }

        config = VariationConfig(seed=42)
        engine = VariationEngine(None, config)
        assigned = engine._assign_variation_points_to_scenes(variation_points, positions)

        # Collect assigned scene IDs
        assigned_scenes = [vp.assigned_scene_id for vp in assigned if vp.assigned_scene_id]

        # Should be 3 assignments to 3 different scenes (since we have 3 middle scenes)
        assert len(assigned_scenes) == 3
        assert len(set(assigned_scenes)) == 3, "VPs should be assigned to different scenes"


class TestVariationPointReproducibility:
    """Test that variation point selection is reproducible with same seed."""

    def test_same_seed_same_selection(self, sample_shape: StoryShape) -> None:
        """Same seed should produce same selection."""
        seed = 12345

        config1 = VariationConfig(seed=seed)
        engine1 = VariationEngine(sample_shape, config1)
        selected1 = engine1._select_variation_points()

        config2 = VariationConfig(seed=seed)
        engine2 = VariationEngine(sample_shape, config2)
        selected2 = engine2._select_variation_points()

        assert len(selected1) == len(selected2)
        for vp1, vp2 in zip(selected1, selected2, strict=True):
            assert vp1.type == vp2.type
            assert vp1.position == vp2.position

    def test_different_seed_different_selection(self, sample_shape: StoryShape) -> None:
        """Different seeds may produce different selections (probabilistic)."""
        # Run with many different seeds and collect results
        selections = []
        for seed in range(100):
            config = VariationConfig(seed=seed)
            engine = VariationEngine(sample_shape, config)
            selected = engine._select_variation_points()
            selections.append(frozenset(vp.type for vp in selected))

        # With enough variation, we should see different selections
        unique_selections = set(selections)
        # Given the probabilities, we expect to see multiple different combinations
        assert len(unique_selections) > 1, "Different seeds should produce different selections"


class TestVariationPointsInProjectVariation:
    """Test that variation points are included in ProjectVariation."""

    def test_project_variation_includes_selected_points(
        self, sample_shape: StoryShape
    ) -> None:
        """ProjectVariation should include selected_variation_points field."""
        config = VariationConfig(seed=42)
        engine = VariationEngine(sample_shape, config)

        scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
        character_ids = ["character-01", "character-02"]

        project_variation = engine.generate_project_variation(scene_ids, character_ids)

        # Should have selected_variation_points field
        assert hasattr(project_variation, "selected_variation_points")
        assert isinstance(project_variation.selected_variation_points, list)

        # All selected points should have assigned_scene_id
        for vp in project_variation.selected_variation_points:
            assert isinstance(vp, SelectedVariationPoint)
            # Most should be assigned (unless no matching position)
            # At least check the type is preserved
            assert vp.type in [svp.type for svp in sample_shape.variation_points]


class TestVariationPointsInStructureGeneration:
    """Test that variation points are integrated into plot graph structure."""

    def test_variation_points_create_beat_slots(self, sample_shape: StoryShape) -> None:
        """Selected variation points should create beat slots in scenes."""
        # Create a shape that always selects at least one variation point
        shape = StoryShape(
            id="guaranteed-vp",
            name="Guaranteed VP",
            description="Test",
            variation_points=[
                VariationPoint(
                    type="guaranteed-beat",
                    description="This beat is guaranteed to be selected.",
                    probability=1.0,
                    position="middle",
                ),
            ],
        )

        # Select variation points
        config = VariationConfig(seed=42)
        engine = VariationEngine(shape, config)
        selected = engine._select_variation_points()
        assert len(selected) == 1  # Guaranteed to be selected

        # Generate plot graph with variation points
        graph = generate_plot_graph(
            format="short-story",
            shape=shape,
            variation=0.5,
            seed=42,
            selected_variation_points=selected,
        )

        # Find the beat slot with the variation point
        found_vp_beat = False
        for scene in graph.scenes:
            for beat in scene.beat_slots:
                if beat.kind == "guaranteed-beat" and beat.variation_point_description:
                    found_vp_beat = True
                    assert "guaranteed to be selected" in beat.variation_point_description.lower()
                    break
            if found_vp_beat:
                break

        assert found_vp_beat, "Should find a beat slot with variation point description"

    def test_variation_point_beat_slot_attributes(self) -> None:
        """Beat slots from variation points should have correct attributes."""
        vp = SelectedVariationPoint(
            type="test-vp",
            description="Test variation point description",
            position="middle",
            assigned_scene_id="scene-01",
        )

        # Create a beat slot manually as it would be created in structure generation
        beat_slot = BeatSlot(
            id="scene-01-beat-01",
            kind=vp.type,
            required=False,
            shape_beat_type=vp.type,
            variation_point_description=vp.description,
        )

        assert beat_slot.kind == "test-vp"
        assert beat_slot.required is False
        assert beat_slot.variation_point_description == "Test variation point description"
        assert beat_slot.shape_beat_type == "test-vp"

    def test_graph_without_variation_points(self) -> None:
        """Graph generation should work without variation points."""
        graph = generate_plot_graph(
            format="short-story",
            shape=None,
            variation=0.5,
            seed=42,
            selected_variation_points=None,
        )

        # Should still generate valid structure
        assert len(graph.scenes) > 0
        for scene in graph.scenes:
            assert len(scene.beat_slots) > 0
            for beat in scene.beat_slots:
                # No beat should have variation_point_description
                assert beat.variation_point_description is None
