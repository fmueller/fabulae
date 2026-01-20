"""Tests for variation system data structures."""

from __future__ import annotations

import random

from fabulae.features.create.variation import (
    ProjectVariation,
    SceneVariation,
    VariationConfig,
    VariationEngine,
    assign_scene_positions,
    generate_subplot_seed,
    select_complication_type,
    select_filler_beats,
)


class TestVariationConfig:
    """Test VariationConfig dataclass."""

    def test_variation_config_default_values(self) -> None:
        """Test VariationConfig instantiation with default values."""
        config = VariationConfig()

        assert config.complication_probability == 0.3
        assert config.character_moment_probability == 0.4
        assert config.subplot_seed_probability == 0.2
        assert config.seed is None

    def test_variation_config_custom_values(self) -> None:
        """Test VariationConfig instantiation with custom values."""
        config = VariationConfig(
            complication_probability=0.5,
            character_moment_probability=0.6,
            subplot_seed_probability=0.1,
            seed=42,
        )

        assert config.complication_probability == 0.5
        assert config.character_moment_probability == 0.6
        assert config.subplot_seed_probability == 0.1
        assert config.seed == 42

    def test_variation_config_field_access(self) -> None:
        """Test that all fields are accessible."""
        config = VariationConfig(seed=123)

        # All fields should be accessible
        _ = config.complication_probability
        _ = config.character_moment_probability
        _ = config.subplot_seed_probability
        _ = config.seed

        assert config.seed == 123


class TestSceneVariation:
    """Test SceneVariation dataclass."""

    def test_scene_variation_basic_instantiation(self) -> None:
        """Test SceneVariation with minimal required fields."""
        variation = SceneVariation(
            scene_id="scene-01",
            position="early",
            has_complication=False,
        )

        assert variation.scene_id == "scene-01"
        assert variation.position == "early"
        assert variation.has_complication is False
        assert variation.complication_type is None
        assert variation.has_character_moment is False
        assert variation.character_focus is None
        assert variation.subplot_seed is None
        assert variation.filler_beats == []

    def test_scene_variation_full_instantiation(self) -> None:
        """Test SceneVariation with all fields populated."""
        variation = SceneVariation(
            scene_id="scene-03",
            position="climax",
            has_complication=True,
            complication_type="external-obstacle",
            has_character_moment=True,
            character_focus="character-01",
            subplot_seed="hidden-past",
            filler_beats=["setup", "bridge", "escalation"],
        )

        assert variation.scene_id == "scene-03"
        assert variation.position == "climax"
        assert variation.has_complication is True
        assert variation.complication_type == "external-obstacle"
        assert variation.has_character_moment is True
        assert variation.character_focus == "character-01"
        assert variation.subplot_seed == "hidden-past"
        assert variation.filler_beats == ["setup", "bridge", "escalation"]

    def test_scene_variation_field_access(self) -> None:
        """Test that all fields are accessible."""
        variation = SceneVariation(
            scene_id="scene-02",
            position="middle",
            has_complication=True,
        )

        # All fields should be accessible
        _ = variation.scene_id
        _ = variation.position
        _ = variation.has_complication
        _ = variation.complication_type
        _ = variation.has_character_moment
        _ = variation.character_focus
        _ = variation.subplot_seed
        _ = variation.filler_beats

        assert variation.scene_id == "scene-02"

    def test_scene_variation_with_empty_filler_beats(self) -> None:
        """Test SceneVariation with empty filler_beats list."""
        variation = SceneVariation(
            scene_id="scene-04",
            position="late",
            has_complication=False,
            filler_beats=[],
        )

        assert variation.filler_beats == []

    def test_scene_variation_different_positions(self) -> None:
        """Test SceneVariation with different position values."""
        for position in ["early", "middle", "late", "climax"]:
            variation = SceneVariation(
                scene_id="scene-01",
                position=position,
                has_complication=False,
            )
            assert variation.position == position


class TestProjectVariation:
    """Test ProjectVariation dataclass."""

    def test_project_variation_basic_instantiation(self) -> None:
        """Test ProjectVariation instantiation."""
        config = VariationConfig()
        scene_vars = [
            SceneVariation(scene_id="scene-01", position="early", has_complication=False),
            SceneVariation(scene_id="scene-02", position="late", has_complication=True),
        ]
        subplot_seeds = ["hidden-past", "secret-alliance"]

        project_var = ProjectVariation(
            scene_variations=scene_vars,
            subplot_seeds=subplot_seeds,
            config=config,
        )

        assert len(project_var.scene_variations) == 2
        assert project_var.scene_variations[0].scene_id == "scene-01"
        assert project_var.scene_variations[1].scene_id == "scene-02"
        assert project_var.subplot_seeds == ["hidden-past", "secret-alliance"]
        assert project_var.config == config

    def test_project_variation_empty_lists(self) -> None:
        """Test ProjectVariation with empty scene variations and subplot seeds."""
        config = VariationConfig()
        project_var = ProjectVariation(
            scene_variations=[],
            subplot_seeds=[],
            config=config,
        )

        assert project_var.scene_variations == []
        assert project_var.subplot_seeds == []

    def test_project_variation_field_access(self) -> None:
        """Test that all fields are accessible."""
        config = VariationConfig(seed=99)
        scene_vars = [
            SceneVariation(scene_id="scene-01", position="early", has_complication=False),
        ]
        project_var = ProjectVariation(
            scene_variations=scene_vars,
            subplot_seeds=["theme-01"],
            config=config,
        )

        # All fields should be accessible
        _ = project_var.scene_variations
        _ = project_var.subplot_seeds
        _ = project_var.config

        assert project_var.config.seed == 99
        assert len(project_var.scene_variations) == 1

    def test_project_variation_with_custom_config(self) -> None:
        """Test ProjectVariation with custom VariationConfig."""
        config = VariationConfig(
            complication_probability=0.7,
            character_moment_probability=0.5,
            subplot_seed_probability=0.3,
            seed=42,
        )
        project_var = ProjectVariation(
            scene_variations=[],
            subplot_seeds=[],
            config=config,
        )

        assert project_var.config.complication_probability == 0.7
        assert project_var.config.character_moment_probability == 0.5
        assert project_var.config.subplot_seed_probability == 0.3
        assert project_var.config.seed == 42

    def test_project_variation_multiple_scene_variations(self) -> None:
        """Test ProjectVariation with multiple scene variations."""
        config = VariationConfig()
        scene_vars = [
            SceneVariation(
                scene_id="scene-01",
                position="early",
                has_complication=True,
                complication_type="setup",
            ),
            SceneVariation(
                scene_id="scene-02",
                position="middle",
                has_complication=False,
            ),
            SceneVariation(
                scene_id="scene-03",
                position="late",
                has_complication=True,
                complication_type="climax",
            ),
            SceneVariation(
                scene_id="scene-04",
                position="climax",
                has_complication=False,
            ),
        ]

        project_var = ProjectVariation(
            scene_variations=scene_vars,
            subplot_seeds=["seed-1", "seed-2", "seed-3"],
            config=config,
        )

        assert len(project_var.scene_variations) == 4
        assert project_var.scene_variations[0].scene_id == "scene-01"
        assert project_var.scene_variations[3].scene_id == "scene-04"
        assert len(project_var.subplot_seeds) == 3


class TestAssignScenePositions:
    """Test assign_scene_positions function."""

    def test_assign_scene_positions_ten_scenes(self) -> None:
        """Test position assignment for 10 scenes."""
        scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
        positions = assign_scene_positions(scene_ids)

        assert len(positions) == 10

        # First 3 should be "early" (0-25% of 10 = indices 0-2, percentages 0.00, 0.11, 0.22)
        assert positions["scene-01"] == "early"
        assert positions["scene-02"] == "early"
        assert positions["scene-03"] == "early"

        # Middle scenes should be "middle" (25-70% = indices 3-6, percentages 0.33-0.67)
        assert positions["scene-04"] == "middle"
        assert positions["scene-05"] == "middle"
        assert positions["scene-06"] == "middle"
        assert positions["scene-07"] == "middle"

        # Late scenes should be "late" (70-90% = indices 7-8, percentages 0.78, 0.89)
        assert positions["scene-08"] == "late"
        assert positions["scene-09"] == "late"

        # Last 1 should be "climax" (90-100% = index 9, percentage 1.00)
        assert positions["scene-10"] == "climax"

    def test_assign_scene_positions_single_scene(self) -> None:
        """Test single scene is assigned 'climax'."""
        scene_ids = ["scene-01"]
        positions = assign_scene_positions(scene_ids)

        assert len(positions) == 1
        assert positions["scene-01"] == "climax"

    def test_assign_scene_positions_two_scenes(self) -> None:
        """Test two scenes: first 'early', second 'climax'."""
        scene_ids = ["scene-01", "scene-02"]
        positions = assign_scene_positions(scene_ids)

        assert len(positions) == 2
        assert positions["scene-01"] == "early"
        assert positions["scene-02"] == "climax"

    def test_assign_scene_positions_empty_list(self) -> None:
        """Test empty scene list returns empty dict."""
        positions = assign_scene_positions([])

        assert positions == {}

    def test_assign_scene_positions_three_scenes(self) -> None:
        """Test three scenes distribution."""
        scene_ids = ["scene-01", "scene-02", "scene-03"]
        positions = assign_scene_positions(scene_ids)

        assert len(positions) == 3
        assert positions["scene-01"] == "early"
        # scene-02 is at 50%, should be "middle"
        assert positions["scene-02"] == "middle"
        # scene-03 is at 100%, should be "climax"
        assert positions["scene-03"] == "climax"


class TestSelectFillerBeats:
    """Test select_filler_beats function."""

    def test_select_filler_beats_early_position(self) -> None:
        """Test 'early' position returns appropriate beats."""
        rng = random.Random(42)
        beats = select_filler_beats(5, "early", rng)

        assert len(beats) == 5
        # All beats should be from early pool
        valid_beats = {"setup", "bridge", "foreshadow", "character-moment"}
        for beat in beats:
            assert beat in valid_beats

    def test_select_filler_beats_climax_position(self) -> None:
        """Test 'climax' position returns appropriate beats."""
        rng = random.Random(42)
        beats = select_filler_beats(5, "climax", rng)

        assert len(beats) == 5
        # All beats should be from climax pool
        valid_beats = {"confrontation", "turn", "resolution", "revelation"}
        for beat in beats:
            assert beat in valid_beats

    def test_select_filler_beats_middle_position(self) -> None:
        """Test 'middle' position returns appropriate beats."""
        rng = random.Random(42)
        beats = select_filler_beats(5, "middle", rng)

        assert len(beats) == 5
        # All beats should be from middle pool
        valid_beats = {"escalation", "complication", "revelation", "character-moment", "bridge"}
        for beat in beats:
            assert beat in valid_beats

    def test_select_filler_beats_late_position(self) -> None:
        """Test 'late' position returns appropriate beats."""
        rng = random.Random(42)
        beats = select_filler_beats(5, "late", rng)

        assert len(beats) == 5
        # All beats should be from late pool
        valid_beats = {"escalation", "confrontation", "revelation", "turn"}
        for beat in beats:
            assert beat in valid_beats

    def test_select_filler_beats_seeded_rng_reproducibility(self) -> None:
        """Test with seeded RNG for reproducibility."""
        rng1 = random.Random(123)
        rng2 = random.Random(123)

        beats1 = select_filler_beats(10, "middle", rng1)
        beats2 = select_filler_beats(10, "middle", rng2)

        assert beats1 == beats2

    def test_select_filler_beats_count_matches_requested(self) -> None:
        """Test returned count matches requested count."""
        for count in [1, 3, 5, 10, 20]:
            beats = select_filler_beats(count, "early", random.Random(42))
            assert len(beats) == count

    def test_select_filler_beats_unknown_position_uses_middle(self) -> None:
        """Test unknown position defaults to middle pool."""
        rng = random.Random(42)
        beats = select_filler_beats(5, "unknown-position", rng)

        assert len(beats) == 5
        # Should use middle pool as default
        valid_beats = {"escalation", "complication", "revelation", "character-moment", "bridge"}
        for beat in beats:
            assert beat in valid_beats


class TestSelectComplicationType:
    """Test select_complication_type function."""

    def test_select_complication_type_returns_valid_type(self) -> None:
        """Test returns a valid complication type."""
        complication = select_complication_type(random.Random(42))

        valid_types = {
            "obstacle",
            "betrayal",
            "revelation",
            "deadline",
            "loss",
            "moral-dilemma",
            "misunderstanding",
            "reversal",
        }
        assert complication in valid_types

    def test_select_complication_type_seeded_rng_reproducibility(self) -> None:
        """Test with seeded RNG for reproducibility."""
        rng1 = random.Random(456)
        rng2 = random.Random(456)

        complication1 = select_complication_type(rng1)
        complication2 = select_complication_type(rng2)

        assert complication1 == complication2

    def test_select_complication_type_multiple_calls(self) -> None:
        """Test multiple calls can produce different results."""
        rng = random.Random(789)
        complications = {select_complication_type(rng) for _ in range(50)}

        # With enough calls, should see variety (at least 3 different types)
        assert len(complications) >= 3


class TestGenerateSubplotSeed:
    """Test generate_subplot_seed function."""

    def test_generate_subplot_seed_returns_valid_seed(self) -> None:
        """Test returns a valid subplot seed."""
        seed = generate_subplot_seed(random.Random(42))

        valid_seeds = {
            "romance",
            "rivalry",
            "secret",
            "debt",
            "grudge",
            "ambition",
            "loyalty-test",
            "past-connection",
        }
        assert seed in valid_seeds

    def test_generate_subplot_seed_seeded_rng_reproducibility(self) -> None:
        """Test with seeded RNG for reproducibility."""
        rng1 = random.Random(999)
        rng2 = random.Random(999)

        seed1 = generate_subplot_seed(rng1)
        seed2 = generate_subplot_seed(rng2)

        assert seed1 == seed2

    def test_generate_subplot_seed_multiple_calls(self) -> None:
        """Test multiple calls can produce different results."""
        rng = random.Random(111)
        seeds = {generate_subplot_seed(rng) for _ in range(50)}

        # With enough calls, should see variety (at least 3 different seeds)
        assert len(seeds) >= 3


class TestVariationEngine:
    """Test VariationEngine class."""

    def test_variation_engine_initialization(self) -> None:
        """Test VariationEngine can be initialized."""
        config = VariationConfig(seed=42)
        shape = None  # No shape needed for basic engine tests
        engine = VariationEngine(shape, config)

        assert engine.shape is shape
        assert engine.config is config
        assert engine.rng is not None

    def test_variation_engine_seeded_rng_reproducibility(self) -> None:
        """Test with seeded RNG for reproducibility."""
        config1 = VariationConfig(seed=12345)
        config2 = VariationConfig(seed=12345)
        shape = None

        engine1 = VariationEngine(shape, config1)
        engine2 = VariationEngine(shape, config2)

        scene_ids = ["scene-01", "scene-02", "scene-03"]
        character_ids = ["character-01", "character-02"]

        variation1 = engine1.generate_project_variation(scene_ids, character_ids)
        variation2 = engine2.generate_project_variation(scene_ids, character_ids)

        # Should produce identical results
        assert len(variation1.scene_variations) == len(variation2.scene_variations)
        for sv1, sv2 in zip(variation1.scene_variations, variation2.scene_variations, strict=True):
            assert sv1.scene_id == sv2.scene_id
            assert sv1.position == sv2.position
            assert sv1.has_complication == sv2.has_complication
            assert sv1.complication_type == sv2.complication_type
            assert sv1.has_character_moment == sv2.has_character_moment
            assert sv1.character_focus == sv2.character_focus
            assert sv1.subplot_seed == sv2.subplot_seed
            assert sv1.filler_beats == sv2.filler_beats

    def test_variation_engine_generates_all_scene_variations(self) -> None:
        """Test that all scenes get variations."""
        config = VariationConfig(seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01", "scene-02", "scene-03", "scene-04", "scene-05"]
        character_ids = ["character-01", "character-02", "character-03"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        assert len(variation.scene_variations) == len(scene_ids)
        for i, scene_var in enumerate(variation.scene_variations):
            assert scene_var.scene_id == scene_ids[i]

    def test_variation_engine_assigns_positions(self) -> None:
        """Test that scenes are assigned correct positions."""
        config = VariationConfig(seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01", "scene-02", "scene-03", "scene-04", "scene-05"]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        # Verify positions match expected distribution
        positions = [sv.position for sv in variation.scene_variations]
        assert "early" in positions
        assert "climax" in positions

    def test_variation_engine_complication_probability(self) -> None:
        """Test complication probability is respected (approximately)."""
        config = VariationConfig(complication_probability=0.8, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = [f"scene-{i:02d}" for i in range(1, 21)]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        complications_count = sum(1 for sv in variation.scene_variations if sv.has_complication)

        # With 20 scenes and 80% probability, expect roughly 16 complications
        # Allow some variance due to randomness (12-19 is reasonable)
        assert 12 <= complications_count <= 19

    def test_variation_engine_complication_type_set_when_has_complication(self) -> None:
        """Test complication type is set when has_complication is True."""
        config = VariationConfig(complication_probability=1.0, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01", "scene-02", "scene-03"]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        for sv in variation.scene_variations:
            if sv.has_complication:
                assert sv.complication_type is not None
                # Check it's a valid complication type
                valid_types = {
                    "obstacle",
                    "betrayal",
                    "revelation",
                    "deadline",
                    "loss",
                    "moral-dilemma",
                    "misunderstanding",
                    "reversal",
                }
                assert sv.complication_type in valid_types

    def test_variation_engine_character_moment_probability(self) -> None:
        """Test character moment probability is respected (approximately)."""
        config = VariationConfig(character_moment_probability=0.5, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = [f"scene-{i:02d}" for i in range(1, 21)]
        character_ids = ["character-01", "character-02"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        char_moments_count = sum(1 for sv in variation.scene_variations if sv.has_character_moment)

        # With 20 scenes and 50% probability, expect roughly 10 character moments
        # Allow variance (6-14 is reasonable)
        assert 6 <= char_moments_count <= 14

    def test_variation_engine_character_focus_balanced(self) -> None:
        """Test character focus distribution is balanced."""
        config = VariationConfig(character_moment_probability=1.0, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        # Use many scenes to test balancing
        scene_ids = [f"scene-{i:02d}" for i in range(1, 31)]
        character_ids = ["character-01", "character-02", "character-03"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        # Count focuses per character
        focus_count: dict[str, int] = {char_id: 0 for char_id in character_ids}
        for sv in variation.scene_variations:
            if sv.character_focus:
                focus_count[sv.character_focus] += 1

        # All characters should get roughly equal focus
        # With 30 scenes and 3 characters, expect roughly 10 per character
        # Allow some variance (7-13 is reasonable)
        for char_id, count in focus_count.items():
            assert 7 <= count <= 13, f"{char_id} has {count} focuses, expected 7-13"

        # No character should have way more than others (max difference should be ≤ 3)
        max_count = max(focus_count.values())
        min_count = min(focus_count.values())
        assert max_count - min_count <= 3

    def test_variation_engine_character_focus_none_when_no_moment(self) -> None:
        """Test character focus is None when no character moment."""
        config = VariationConfig(character_moment_probability=0.0, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01", "scene-02", "scene-03"]
        character_ids = ["character-01", "character-02"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        for sv in variation.scene_variations:
            assert sv.has_character_moment is False
            assert sv.character_focus is None

    def test_variation_engine_subplot_seeds_only_early_middle(self) -> None:
        """Test subplot seeds only appear in early/middle scenes, not late/climax."""
        config = VariationConfig(subplot_seed_probability=1.0, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        for sv in variation.scene_variations:
            if sv.subplot_seed is not None:
                # Subplot seeds should only appear in early/middle positions
                assert sv.position in ["early", "middle"]
            if sv.position in ["late", "climax"]:
                # Late/climax scenes should not have subplot seeds
                assert sv.subplot_seed is None

    def test_variation_engine_subplot_seed_probability(self) -> None:
        """Test subplot seed probability is respected for early/middle scenes."""
        config = VariationConfig(subplot_seed_probability=0.5, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        # Use many scenes to get good early/middle distribution
        scene_ids = [f"scene-{i:02d}" for i in range(1, 21)]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        # Count early/middle scenes and those with subplots
        early_middle_count = sum(1 for sv in variation.scene_variations if sv.position in ["early", "middle"])
        subplot_count = sum(1 for sv in variation.scene_variations if sv.subplot_seed is not None)

        # With roughly 14 early/middle scenes (70% of 20) and 50% probability,
        # expect roughly 7 subplots (allow variance 4-10)
        assert early_middle_count > 0
        assert 4 <= subplot_count <= 10

    def test_variation_engine_subplot_seeds_collected(self) -> None:
        """Test that subplot seeds are collected in the ProjectVariation."""
        config = VariationConfig(subplot_seed_probability=1.0, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        # All unique subplot seeds should be in the list
        scene_subplot_seeds = {sv.subplot_seed for sv in variation.scene_variations if sv.subplot_seed is not None}

        for seed in scene_subplot_seeds:
            assert seed in variation.subplot_seeds

    def test_variation_engine_filler_beats_generated(self) -> None:
        """Test that filler beats are generated for all scenes."""
        config = VariationConfig(seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01", "scene-02", "scene-03"]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        for sv in variation.scene_variations:
            # All scenes should have filler beats
            assert len(sv.filler_beats) > 0

    def test_variation_engine_filler_beats_count_by_position(self) -> None:
        """Test filler beats count varies by position."""
        config = VariationConfig(seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = [f"scene-{i:02d}" for i in range(1, 11)]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        # Climax scenes should have 4 beats, late 3, others 2
        for sv in variation.scene_variations:
            if sv.position == "climax":
                assert len(sv.filler_beats) == 4
            elif sv.position == "late":
                assert len(sv.filler_beats) == 3
            else:  # early or middle
                assert len(sv.filler_beats) == 2

    def test_variation_engine_empty_character_list(self) -> None:
        """Test engine works with empty character list."""
        config = VariationConfig(character_moment_probability=1.0, seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01", "scene-02"]
        character_ids: list[str] = []

        variation = engine.generate_project_variation(scene_ids, character_ids)

        # Should not crash, but character_focus should be None
        for sv in variation.scene_variations:
            assert sv.character_focus is None

    def test_variation_engine_single_scene(self) -> None:
        """Test engine works with a single scene."""
        config = VariationConfig(seed=42)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01"]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        assert len(variation.scene_variations) == 1
        assert variation.scene_variations[0].scene_id == "scene-01"
        assert variation.scene_variations[0].position == "climax"

    def test_variation_engine_config_stored(self) -> None:
        """Test that config is stored in ProjectVariation."""
        config = VariationConfig(seed=999)
        shape = None
        engine = VariationEngine(shape, config)

        scene_ids = ["scene-01"]
        character_ids = ["character-01"]

        variation = engine.generate_project_variation(scene_ids, character_ids)

        assert variation.config is config
        assert variation.config.seed == 999
