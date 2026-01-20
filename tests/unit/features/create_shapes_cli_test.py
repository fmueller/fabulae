"""Tests for shape CLI commands."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from fabulae.features.create.shapes.loader import ShapeNotFoundError
from fabulae.main import app

runner = CliRunner()


class TestShapesListCommand:
    """Tests for the 'shapes' command (list mode)."""

    def test_shapes_lists_all_available_shapes(self) -> None:
        """Test that shapes command lists all available shapes."""
        result = runner.invoke(app, ["shapes"])

        assert result.exit_code == 0
        # Check that the output contains all 10 shapes
        assert "betrayal-arc" in result.stdout
        assert "coming-of-age" in result.stdout
        assert "fall-redemption" in result.stdout
        assert "fish-out-of-water" in result.stdout
        assert "forbidden-knowledge" in result.stdout
        assert "heros-journey" in result.stdout
        assert "mystery-reveal" in result.stdout
        assert "revenge-quest" in result.stdout
        assert "romance-arc" in result.stdout
        assert "transformation" in result.stdout

        # Check that it shows count
        assert "Available story shapes (10)" in result.stdout

    def test_shapes_shows_shape_names_and_descriptions(self) -> None:
        """Test that shapes command shows names and descriptions."""
        result = runner.invoke(app, ["shapes"])

        assert result.exit_code == 0
        # Check for some expected names
        assert "Betrayal Arc" in result.stdout
        assert "Hero's Journey" in result.stdout or "Hero's Journey" in result.stdout

        # Check for partial descriptions (they might be truncated)
        assert "narrative" in result.stdout.lower() or "trust" in result.stdout.lower()

    def test_shapes_handles_no_shapes_gracefully(self) -> None:
        """Test that shapes command handles no shapes found."""
        with patch("fabulae.features.create.shapes_cli.get_shape_ids", return_value=[]):
            result = runner.invoke(app, ["shapes"])

            assert result.exit_code == 0
            assert "No story shapes found" in result.stdout

    def test_shapes_handles_load_error_gracefully(self) -> None:
        """Test that shapes command handles individual shape load errors gracefully."""
        mock_load_shape = MagicMock(side_effect=ValueError("Test error"))

        with (
            patch("fabulae.features.create.shapes_cli.get_shape_ids", return_value=["test-shape"]),
            patch("fabulae.features.create.shapes_cli.load_shape", mock_load_shape),
        ):
            result = runner.invoke(app, ["shapes"])

            assert result.exit_code == 0
            assert "test-shape" in result.stdout
            assert "error loading" in result.stdout.lower()


class TestShapesDetailCommand:
    """Tests for the 'shapes <id>' command (detail mode)."""

    def test_shapes_shows_betrayal_arc_details(self) -> None:
        """Test that shapes command shows correct details for betrayal-arc."""
        result = runner.invoke(app, ["shapes", "betrayal-arc"])

        assert result.exit_code == 0

        # Check header info
        assert "Betrayal Arc" in result.stdout
        assert "ID: betrayal-arc" in result.stdout

        # Check for character slots
        assert "Character Slots" in result.stdout
        assert "protagonist" in result.stdout
        assert "betrayer" in result.stdout
        assert "witness" in result.stdout

        # Check for setting slots
        assert "Setting Slots" in result.stdout
        assert "trust-space" in result.stdout
        assert "revelation-space" in result.stdout

        # Check for required beats
        assert "Required Beats" in result.stdout
        assert "trust-building" in result.stdout
        assert "revelation" in result.stdout
        assert "confrontation" in result.stdout
        assert "aftermath" in result.stdout

        # Check for variation points
        assert "Variation Points" in result.stdout

        # Check for themes
        assert "Themes:" in result.stdout
        assert "trust" in result.stdout or "Trust" in result.stdout
        assert "deception" in result.stdout or "Deception" in result.stdout

        # Check for motifs
        assert "Motifs:" in result.stdout

        # Check for tone
        assert "Tone:" in result.stdout

    def test_shapes_shows_beat_positions_and_flexibility(self) -> None:
        """Test that shapes command shows beat position and flexibility info."""
        result = runner.invoke(app, ["shapes", "betrayal-arc"])

        assert result.exit_code == 0
        # Check that beats show position and flexibility
        assert "early" in result.stdout
        assert "middle" in result.stdout
        assert "late" in result.stdout
        assert "climax" in result.stdout
        assert "flexible" in result.stdout or "fixed" in result.stdout

    def test_shapes_shows_variation_probabilities(self) -> None:
        """Test that shapes command shows variation probabilities."""
        result = runner.invoke(app, ["shapes", "betrayal-arc"])

        assert result.exit_code == 0
        # Check that variation points show probabilities (should have % sign)
        assert "%" in result.stdout
        assert "probability" in result.stdout

    def test_shapes_shows_optional_markers(self) -> None:
        """Test that shapes command marks optional slots."""
        result = runner.invoke(app, ["shapes", "betrayal-arc"])

        assert result.exit_code == 0
        # Check that optional slots are marked
        assert "(optional)" in result.stdout

    def test_shapes_nonexistent_shows_error(self) -> None:
        """Test that shapes command shows error for nonexistent shape."""
        result = runner.invoke(app, ["shapes", "nonexistent-shape"])

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()
        assert "Available shapes:" in result.stdout

    def test_shapes_handles_load_error(self) -> None:
        """Test that shapes command handles load errors gracefully."""
        mock_load_shape = MagicMock(side_effect=ValueError("Test load error"))

        with patch("fabulae.features.create.shapes_cli.load_shape", mock_load_shape):
            result = runner.invoke(app, ["shapes", "test-shape"])

            assert result.exit_code == 1
            assert "Error loading shape" in result.stdout
            assert "test-shape" in result.stdout

    def test_shapes_handles_shape_not_found_error(self) -> None:
        """Test that shapes command handles ShapeNotFoundError."""
        mock_load_shape = MagicMock(
            side_effect=ShapeNotFoundError("Shape 'missing' not found. Available shapes: betrayal-arc, heros-journey")
        )

        with patch("fabulae.features.create.shapes_cli.load_shape", mock_load_shape):
            result = runner.invoke(app, ["shapes", "missing"])

            assert result.exit_code == 1
            assert "not found" in result.stdout
            assert "Available shapes:" in result.stdout

    def test_shapes_works_for_all_built_in_shapes(self) -> None:
        """Test that shapes command works for all built-in shapes."""
        # List of all 10 shapes
        shapes = [
            "betrayal-arc",
            "coming-of-age",
            "fall-redemption",
            "fish-out-of-water",
            "forbidden-knowledge",
            "heros-journey",
            "mystery-reveal",
            "revenge-quest",
            "romance-arc",
            "transformation",
        ]

        for shape_id in shapes:
            result = runner.invoke(app, ["shapes", shape_id])
            assert result.exit_code == 0, f"Failed for shape: {shape_id}"
            assert "Required Beats" in result.stdout, f"Missing beats for: {shape_id}"

    def test_shapes_shows_can_merge_with_for_character_slots(self) -> None:
        """Test that shapes command shows can_merge_with for character slots."""
        result = runner.invoke(app, ["shapes", "betrayal-arc"])

        assert result.exit_code == 0
        # Witness slot can merge with ally or confessor
        assert "Can merge with:" in result.stdout

    def test_shapes_shows_used_in_for_setting_slots(self) -> None:
        """Test that shapes command shows used_in for setting slots."""
        result = runner.invoke(app, ["shapes", "betrayal-arc"])

        assert result.exit_code == 0
        # Setting slots should show which beats they're used in
        assert "Used in:" in result.stdout
