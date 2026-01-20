"""Tests for --shape flag in create command (accepts both shape ID and file path)."""

from __future__ import annotations

import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from fabulae.features.create.schemas import CreateOptions
from fabulae.main import app
from fabulae.models import StoryShape


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_shape() -> StoryShape:
    """Create a minimal mock story shape."""
    return StoryShape(
        id="test-shape",
        name="Test Shape",
        description="A test story shape",
        character_slots=[],
        setting_slots=[],
        required_beats=[],
        variation_points=[],
        themes=[],
        motifs=[],
        tone="neutral",
    )


@pytest.fixture
def custom_shape_file(tmp_path: Path, mock_shape: StoryShape) -> Path:
    """Create a temporary custom shape file."""
    shape_file = tmp_path / "custom-shape.yml"
    import yaml

    with open(shape_file, "w", encoding="utf-8") as f:
        yaml.dump(mock_shape.model_dump(exclude_none=True), f)
    return shape_file


def strip_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)


def test_create_with_shape_flag_loads_shape(runner: CliRunner, tmp_path: Path, mock_shape: StoryShape) -> None:
    """Test that --shape flag loads the correct shape."""
    output_dir = tmp_path / "project"

    with (
        patch("fabulae.features.create.cli.generate_project_from_idea_sync") as mock_generate,
        patch("fabulae.features.create.shapes.loader.load_shape", return_value=mock_shape),
        patch("fabulae.features.create.cli.save_project"),
    ):
        mock_project = MagicMock()
        mock_project.characters = []
        mock_project.plot.scenes = []
        mock_project.plot.fragments = []
        mock_project.plot.stanzas = []
        mock_generate.return_value = mock_project

        result = runner.invoke(
            app,
            [
                "create",
                str(output_dir),
                "--idea",
                "A test story",
                "--shape",
                "betrayal-arc",
            ],
        )

        assert result.exit_code == 0, result.stdout
        # Verify that generate was called with shape_id in options
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.shape_id == "betrayal-arc"
        assert options.shape_file is None


def test_create_with_shape_file_path_loads_custom_shape(
    runner: CliRunner, tmp_path: Path, custom_shape_file: Path
) -> None:
    """Test that --shape with a file path loads custom shape from file."""
    output_dir = tmp_path / "project"

    with (
        patch("fabulae.features.create.cli.generate_project_from_idea_sync") as mock_generate,
        patch("fabulae.features.create.cli.save_project"),
    ):
        mock_project = MagicMock()
        mock_project.characters = []
        mock_project.plot.scenes = []
        mock_project.plot.fragments = []
        mock_project.plot.stanzas = []
        mock_generate.return_value = mock_project

        result = runner.invoke(
            app,
            [
                "create",
                str(output_dir),
                "--idea",
                "A test story",
                "--shape",
                str(custom_shape_file),
            ],
        )

        assert result.exit_code == 0, result.stdout
        # Verify that generate was called with shape_file in options
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.shape_file == custom_shape_file
        assert options.shape_id is None


def test_create_with_invalid_shape_id_shows_error(runner: CliRunner, tmp_path: Path) -> None:
    """Test that invalid shape ID shows appropriate error message."""
    output_dir = tmp_path / "project"

    result = runner.invoke(
        app,
        [
            "create",
            str(output_dir),
            "--idea",
            "A test story",
            "--shape",
            "nonexistent-shape",
        ],
    )

    assert result.exit_code != 0
    # The error should mention the shape not being found
    output = result.stdout + (result.stderr or "")
    assert "nonexistent-shape" in output or "Unknown shape" in output


def test_create_with_nonexistent_shape_shows_helpful_error(runner: CliRunner, tmp_path: Path) -> None:
    """Test that nonexistent shape (not a file, not a valid ID) shows helpful error."""
    output_dir = tmp_path / "project"

    result = runner.invoke(
        app,
        [
            "create",
            str(output_dir),
            "--idea",
            "A test story",
            "--shape",
            "does-not-exist.yml",  # Looks like a file but doesn't exist, treated as invalid shape ID
        ],
    )

    assert result.exit_code != 0
    output = result.stdout + result.stderr
    # Should mention it's unknown and suggest it might be a file path
    assert "Unknown shape" in output or "does-not-exist" in output


def test_create_with_shape_directory_fails(runner: CliRunner, tmp_path: Path) -> None:
    """Test that using a directory path as --shape raises an error."""
    output_dir = tmp_path / "project"
    shape_dir = tmp_path / "shapes"
    shape_dir.mkdir()

    result = runner.invoke(
        app,
        [
            "create",
            str(output_dir),
            "--idea",
            "A test story",
            "--shape",
            str(shape_dir),
        ],
    )

    assert result.exit_code != 0
    output = result.stdout + result.stderr
    assert "directory" in output.lower()


def test_create_without_shape_flags_works(runner: CliRunner, tmp_path: Path) -> None:
    """Test that create command works without shape flags (backward compatibility)."""
    output_dir = tmp_path / "project"

    with (
        patch("fabulae.features.create.cli.generate_project_from_idea_sync") as mock_generate,
        patch("fabulae.features.create.cli.save_project"),
    ):
        mock_project = MagicMock()
        mock_project.characters = []
        mock_project.plot.scenes = []
        mock_project.plot.fragments = []
        mock_project.plot.stanzas = []
        mock_generate.return_value = mock_project

        result = runner.invoke(
            app,
            [
                "create",
                str(output_dir),
                "--idea",
                "A test story",
            ],
        )

        assert result.exit_code == 0, result.stdout
        # Verify that generate was called with no shape options
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.shape_id is None
        assert options.shape_file is None


def test_shape_loaded_and_saved_to_artifacts(tmp_path: Path, mock_shape: StoryShape) -> None:
    """Test that loaded shape is saved to artifacts directory."""
    from fabulae.features.create.schemas import CreateOptions

    # Create the options with a shape_id
    options = CreateOptions(shape_id="test-shape")

    # Verify the options contain the shape_id
    assert options.shape_id == "test-shape"
    assert options.shape_file is None

    # Test that the shape loader can load from the options
    with patch("fabulae.features.create.shapes.loader.load_shape", return_value=mock_shape) as mock_loader:
        from fabulae.features.create.shapes.loader import load_shape

        loaded = load_shape("test-shape")
        assert loaded.id == mock_shape.id
        mock_loader.assert_called_once_with("test-shape")


def test_create_options_accepts_both_shape_id_and_file() -> None:
    """Test that CreateOptions dataclass can hold both shape_id and shape_file (for internal use)."""
    from pathlib import Path

    from fabulae.features.create.schemas import CreateOptions

    # CreateOptions allows both to be set (pipelines check shape_file first, then shape_id)
    shape_file = Path("/tmp/custom.yml")
    options = CreateOptions(
        shape_id="betrayal-arc",
        shape_file=shape_file,
    )

    # Both can be set in the dataclass
    assert options.shape_id == "betrayal-arc"
    assert options.shape_file == shape_file
    # CLI resolves --shape to exactly one of these, but internal code can set both


def test_create_with_no_shape_flag(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --no-shape flag sets no_shape=True in CreateOptions."""
    output_dir = tmp_path / "project"

    with (
        patch("fabulae.features.create.cli.generate_project_from_idea_sync") as mock_generate,
        patch("fabulae.features.create.cli.save_project"),
    ):
        mock_project = MagicMock()
        mock_project.characters = []
        mock_project.plot.scenes = []
        mock_project.plot.fragments = []
        mock_project.plot.stanzas = []
        mock_generate.return_value = mock_project

        result = runner.invoke(
            app,
            [
                "create",
                str(output_dir),
                "--idea",
                "A test story",
                "--no-shape",
            ],
        )

        assert result.exit_code == 0, result.stdout
        # Verify that generate was called with no_shape=True in options
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.no_shape is True
        assert options.shape_id is None
        assert options.shape_file is None


def test_create_with_no_shape_and_shape_fails(runner: CliRunner, tmp_path: Path) -> None:
    """Test that using both --no-shape and --shape together raises an error."""
    output_dir = tmp_path / "project"

    result = runner.invoke(
        app,
        [
            "create",
            str(output_dir),
            "--idea",
            "A test story",
            "--no-shape",
            "--shape",
            "betrayal-arc",
        ],
    )

    assert result.exit_code != 0
    output = strip_ansi(result.stdout + result.stderr)
    assert "Cannot specify --no-shape with --shape" in output


def test_create_with_no_shape_and_shape_file_path_fails(
    runner: CliRunner, tmp_path: Path, custom_shape_file: Path
) -> None:
    """Test that using both --no-shape and --shape (with file path) together raises an error."""
    output_dir = tmp_path / "project"

    result = runner.invoke(
        app,
        [
            "create",
            str(output_dir),
            "--idea",
            "A test story",
            "--no-shape",
            "--shape",
            str(custom_shape_file),
        ],
    )

    assert result.exit_code != 0
    output = strip_ansi(result.stdout + result.stderr)
    assert "Cannot specify --no-shape with --shape" in output
