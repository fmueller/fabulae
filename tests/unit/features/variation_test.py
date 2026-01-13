"""Tests for variation system."""

from __future__ import annotations

import pytest

from fabulae.features.create.variation import (
    VariationConfig,
    create_variation_config_from_level,
)


class TestVariationConfigCreation:
    """Test creating VariationConfig from variation level."""

    def test_level_0_0_creates_minimal_probabilities(self) -> None:
        """At level 0.0, all probabilities should be 0.0 (minimal variation)."""
        config = create_variation_config_from_level(0.0)

        assert config.complication_probability == 0.0
        assert config.character_moment_probability == 0.0
        assert config.subplot_seed_probability == 0.0
        assert config.seed is None

    def test_level_1_0_creates_maximum_probabilities(self) -> None:
        """At level 1.0, all probabilities should be at maximum."""
        config = create_variation_config_from_level(1.0)

        assert config.complication_probability == 0.6
        assert config.character_moment_probability == 0.7
        assert config.subplot_seed_probability == 0.5

    def test_level_0_5_creates_default_probabilities(self) -> None:
        """At level 0.5, probabilities should be at default values."""
        config = create_variation_config_from_level(0.5)

        # Expected: min + (max - min) * 0.5
        assert config.complication_probability == pytest.approx(0.3)
        assert config.character_moment_probability == pytest.approx(0.35)
        assert config.subplot_seed_probability == pytest.approx(0.25)

    def test_level_0_25_interpolates_correctly(self) -> None:
        """Test interpolation at 0.25."""
        config = create_variation_config_from_level(0.25)

        # complication: 0 + (0.6 - 0) * 0.25 = 0.15
        assert config.complication_probability == pytest.approx(0.15)
        # character_moment: 0 + (0.7 - 0) * 0.25 = 0.175
        assert config.character_moment_probability == pytest.approx(0.175)
        # subplot_seed: 0 + (0.5 - 0) * 0.25 = 0.125
        assert config.subplot_seed_probability == pytest.approx(0.125)

    def test_level_0_75_interpolates_correctly(self) -> None:
        """Test interpolation at 0.75."""
        config = create_variation_config_from_level(0.75)

        # complication: 0 + (0.6 - 0) * 0.75 = 0.45
        assert config.complication_probability == pytest.approx(0.45)
        # character_moment: 0 + (0.7 - 0) * 0.75 = 0.525
        assert config.character_moment_probability == pytest.approx(0.525)
        # subplot_seed: 0 + (0.5 - 0) * 0.75 = 0.375
        assert config.subplot_seed_probability == pytest.approx(0.375)

    def test_seed_is_passed_through(self) -> None:
        """Test that the seed is passed through to the config."""
        config = create_variation_config_from_level(0.5, seed=42)

        assert config.seed == 42

    def test_seed_defaults_to_none(self) -> None:
        """Test that seed defaults to None when not provided."""
        config = create_variation_config_from_level(0.5)

        assert config.seed is None

    def test_invalid_level_below_zero_raises_error(self) -> None:
        """Test that level below 0.0 raises ValueError."""
        with pytest.raises(ValueError, match="Variation level must be in range"):
            create_variation_config_from_level(-0.1)

    def test_invalid_level_above_one_raises_error(self) -> None:
        """Test that level above 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="Variation level must be in range"):
            create_variation_config_from_level(1.1)

    def test_returns_variation_config_instance(self) -> None:
        """Test that the function returns a VariationConfig instance."""
        config = create_variation_config_from_level(0.5)

        assert isinstance(config, VariationConfig)

    def test_edge_case_very_small_positive_level(self) -> None:
        """Test with very small positive level (near 0.0)."""
        config = create_variation_config_from_level(0.001)

        assert config.complication_probability == pytest.approx(0.0006)
        assert config.character_moment_probability == pytest.approx(0.0007)
        assert config.subplot_seed_probability == pytest.approx(0.0005)

    def test_edge_case_very_large_level(self) -> None:
        """Test with very large level (near 1.0)."""
        config = create_variation_config_from_level(0.999)

        assert config.complication_probability == pytest.approx(0.5994, abs=0.0001)
        assert config.character_moment_probability == pytest.approx(0.6993, abs=0.0001)
        assert config.subplot_seed_probability == pytest.approx(0.4995, abs=0.0001)
