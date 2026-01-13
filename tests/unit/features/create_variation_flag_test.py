"""Tests for --variation flag in create command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from fabulae.features.create.schemas import CreateOptions
from fabulae.main import app


@pytest.fixture
def runner() -> CliRunner:
    """Create a CLI test runner."""
    return CliRunner()


def test_create_with_variation_flag_accepts_value(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --variation flag accepts float values between 0.0 and 1.0."""
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
                "--variation",
                "0.7",
            ],
        )

        assert result.exit_code == 0, result.stdout
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.variation == 0.7


def test_create_with_variation_0_0_minimizes_variation(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --variation 0.0 creates config with minimal probabilities."""
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
                "--variation",
                "0.0",
            ],
        )

        assert result.exit_code == 0, result.stdout
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.variation == 0.0


def test_create_with_variation_1_0_maximizes_variation(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --variation 1.0 creates config with maximum probabilities."""
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
                "--variation",
                "1.0",
            ],
        )

        assert result.exit_code == 0, result.stdout
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.variation == 1.0


def test_create_with_default_variation_is_0_5(runner: CliRunner, tmp_path: Path) -> None:
    """Test that default variation value is 0.5 when flag not specified."""
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
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.variation == 0.5


def test_create_rejects_variation_below_zero(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --variation values below 0.0 are rejected."""
    output_dir = tmp_path / "project"

    result = runner.invoke(
        app,
        [
            "create",
            str(output_dir),
            "--idea",
            "A test story",
            "--variation",
            "-0.1",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value" in result.output or "must be" in result.output.lower()


def test_create_rejects_variation_above_one(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --variation values above 1.0 are rejected."""
    output_dir = tmp_path / "project"

    result = runner.invoke(
        app,
        [
            "create",
            str(output_dir),
            "--idea",
            "A test story",
            "--variation",
            "1.5",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value" in result.output or "must be" in result.output.lower()


def test_create_with_variation_0_5_creates_default_config(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --variation 0.5 creates config with default probabilities."""
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
                "--variation",
                "0.5",
            ],
        )

        assert result.exit_code == 0, result.stdout
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.variation == 0.5


def test_create_variation_with_other_flags(runner: CliRunner, tmp_path: Path) -> None:
    """Test that --variation works alongside other flags."""
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
                "--format",
                "novella",
                "--variation",
                "0.3",
                "--temperature",
                "0.8",
            ],
        )

        assert result.exit_code == 0, result.stdout
        call_args = mock_generate.call_args
        options: CreateOptions = call_args.kwargs["options"]
        assert options.variation == 0.3
