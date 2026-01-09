"""Tests for the fabulae CLI."""

from pathlib import Path

from typer.testing import CliRunner

from fabulae import __version__
from fabulae.main import app

runner = CliRunner()


def test_version_command_shows_version() -> None:
    """Version command outputs the current version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"fabulae v{__version__}" in result.output


def test_help_flag_shows_help() -> None:
    """The --help flag displays usage information."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Fabulae" in result.output
    assert "version" in result.output
    assert "narrative-patterns" in result.output


def test_short_help_flag_shows_help() -> None:
    """The -h flag displays usage information."""
    result = runner.invoke(app, ["-h"])
    assert result.exit_code == 0
    assert "Fabulae" in result.output
    assert "version" in result.output
    assert "narrative-patterns" in result.output


def test_no_command_shows_help() -> None:
    """Running without a command shows help."""
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "Fabulae" in result.output


def test_validate_command_succeeds(tmp_path: Path) -> None:
    """Validate command succeeds for a minimal project."""
    import yaml

    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test premise.",
                "scenes": [{"id": "scene-one", "location": "apiary"}],
            }
        )
    )
    (tmp_path / "world.yml").write_text(
        yaml.dump(
            {"facts": [{"id": "apiary", "type": "location", "name": "Apiary"}]}
        )
    )

    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 0
    assert "Validation OK" in result.output


def test_validate_command_fails_for_missing_manifest(tmp_path: Path) -> None:
    """Validate command fails when fabulae.yml is missing."""
    result = runner.invoke(app, ["validate", str(tmp_path)])
    assert result.exit_code == 1
    assert "Validation failed" in result.output


def test_narrative_patterns_command_lists_patterns(tmp_path: Path) -> None:
    """Narrative patterns command lists available patterns."""
    import yaml

    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test premise.",
                "scenes": [{"id": "scene-one", "location": "apiary"}],
            }
        )
    )
    (tmp_path / "world.yml").write_text(
        yaml.dump(
            {"facts": [{"id": "apiary", "type": "location", "name": "Apiary"}]}
        )
    )
    (tmp_path / "narrative_patterns.yml").write_text(
        yaml.dump(
            {
                "narrative_patterns": [
                    {
                        "id": "cozy-mystery",
                        "name": "Cozy Mystery",
                        "description": "A gentle mystery unfolds.",
                    }
                ]
            }
        )
    )

    result = runner.invoke(app, ["narrative-patterns", str(tmp_path)])
    assert result.exit_code == 0
    assert "cozy-mystery" in result.output
