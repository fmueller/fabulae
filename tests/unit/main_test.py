"""Tests for the fabulae CLI."""

from pathlib import Path

from typer.testing import CliRunner

from fabulae import __version__
from fabulae.main import app

TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "templates"
NOVEL_TEMPLATE_DIR = TEMPLATES_DIR / "novel"
NOVELLA_TEMPLATE_DIR = TEMPLATES_DIR / "novella"
SHORT_STORY_TEMPLATE_DIR = TEMPLATES_DIR / "short-story"
POEM_TEMPLATE_DIR = TEMPLATES_DIR / "poem"
MICRO_PROSE_TEMPLATE_DIR = TEMPLATES_DIR / "micro-prose"

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
    assert "narrative-patterns" not in result.output


def test_short_help_flag_shows_help() -> None:
    """The -h flag displays usage information."""
    result = runner.invoke(app, ["-h"])
    assert result.exit_code == 0
    assert "Fabulae" in result.output
    assert "version" in result.output
    assert "narrative-patterns" not in result.output


def test_no_command_shows_help() -> None:
    """Running without a command shows help."""
    result = runner.invoke(app, env={"FABULAE_DISABLE_TUI": "1"})
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



def test_init_command_creates_novel_project_by_default(tmp_path: Path) -> None:
    """Init command bootstraps a novel project by default."""
    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 0
    assert "format: novel" in result.output

    expected_files = {path.name for path in NOVEL_TEMPLATE_DIR.glob("*.yml")}
    expected_files.add(".gitignore")  # Also copies .gitignore
    created_files = {path.name for path in tmp_path.iterdir() if path.is_file()}
    assert expected_files
    assert created_files == expected_files

    assert (tmp_path / "fabulae.yml").read_text(encoding="utf-8") == (
        NOVEL_TEMPLATE_DIR / "fabulae.yml"
    ).read_text(encoding="utf-8")


def test_init_command_creates_poem_project(tmp_path: Path) -> None:
    """Init command with --format poem creates a poem project."""
    result = runner.invoke(app, ["init", "--format", "poem", str(tmp_path)])
    assert result.exit_code == 0
    assert "format: poem" in result.output

    expected_files = {path.name for path in POEM_TEMPLATE_DIR.glob("*.yml")}
    expected_files.add(".gitignore")  # Also copies .gitignore
    created_files = {path.name for path in tmp_path.iterdir() if path.is_file()}
    assert expected_files
    assert created_files == expected_files


def test_init_command_creates_micro_prose_project(tmp_path: Path) -> None:
    """Init command with --format micro-prose creates a micro-prose project."""
    result = runner.invoke(app, ["init", "--format", "micro-prose", str(tmp_path)])
    assert result.exit_code == 0
    assert "format: micro-prose" in result.output

    expected_files = {path.name for path in MICRO_PROSE_TEMPLATE_DIR.glob("*.yml")}
    expected_files.add(".gitignore")  # Also copies .gitignore
    created_files = {path.name for path in tmp_path.iterdir() if path.is_file()}
    assert expected_files
    assert created_files == expected_files


def test_init_command_creates_novella_project(tmp_path: Path) -> None:
    """Init command with --format novella creates a novella project."""
    result = runner.invoke(app, ["init", "--format", "novella", str(tmp_path)])
    assert result.exit_code == 0
    assert "format: novella" in result.output

    expected_files = {path.name for path in NOVELLA_TEMPLATE_DIR.glob("*.yml")}
    expected_files.add(".gitignore")  # Also copies .gitignore
    created_files = {path.name for path in tmp_path.iterdir() if path.is_file()}
    assert expected_files
    assert created_files == expected_files


def test_init_command_creates_short_story_project(tmp_path: Path) -> None:
    """Init command with --format short-story creates a short-story project."""
    result = runner.invoke(app, ["init", "--format", "short-story", str(tmp_path)])
    assert result.exit_code == 0
    assert "format: short-story" in result.output

    expected_files = {path.name for path in SHORT_STORY_TEMPLATE_DIR.glob("*.yml")}
    expected_files.add(".gitignore")  # Also copies .gitignore
    created_files = {path.name for path in tmp_path.iterdir() if path.is_file()}
    assert expected_files
    assert created_files == expected_files


def test_init_command_format_short_flag(tmp_path: Path) -> None:
    """Init command accepts -f as short flag for --format."""
    result = runner.invoke(app, ["init", "-f", "poem", str(tmp_path)])
    assert result.exit_code == 0
    assert "format: poem" in result.output


def test_init_command_fails_on_unknown_format(tmp_path: Path) -> None:
    """Init command fails for unknown format."""
    result = runner.invoke(app, ["init", "--format", "screenplay", str(tmp_path)])
    assert result.exit_code != 0
    assert "Unknown format" in result.output
    assert "screenplay" in result.output


def test_init_command_fails_on_existing_files(tmp_path: Path) -> None:
    """Init command fails when target files already exist."""
    (tmp_path / "fabulae.yml").write_text("version: 9.9.9", encoding="utf-8")

    result = runner.invoke(app, ["init", str(tmp_path)])
    assert result.exit_code == 1
    assert "already exist" in result.output


def test_init_command_overwrites_with_force(tmp_path: Path) -> None:
    """Init command overwrites existing files when forced."""
    (tmp_path / "fabulae.yml").write_text("version: 9.9.9", encoding="utf-8")

    result = runner.invoke(app, ["init", "--force", str(tmp_path)])
    assert result.exit_code == 0
    assert (tmp_path / "fabulae.yml").read_text(encoding="utf-8") == (
        NOVEL_TEMPLATE_DIR / "fabulae.yml"
    ).read_text(encoding="utf-8")
