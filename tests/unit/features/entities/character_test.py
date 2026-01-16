"""Tests for character CRUD commands."""

import re
from pathlib import Path

import yaml
from typer.testing import CliRunner

from fabulae.main import app
from fabulae.models import load_project

runner = CliRunner()


def strip_ansi(text: str) -> str:
    """Strip ANSI escape codes from text."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def create_test_project(tmp_path: Path) -> Path:
    """Create a minimal test project."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump({
            "premise": "A test story.",
            "format": "novel",
            "scenes": [
                {"id": "scene-01", "characters": ["char-01"]},
            ],
        })
    )
    (tmp_path / "characters.yml").write_text(
        yaml.dump({
            "characters": [
                {"id": "char-01", "name": "Alice", "role": "protagonist"},
            ]
        })
    )
    return tmp_path


class TestCharacterAdd:
    """Tests for character add command."""

    def test_add_character(self, tmp_path: Path) -> None:
        """Add a new character to the project."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["character", "add", str(tmp_path), "--id", "char-02", "--name", "Bob"],
        )
        assert result.exit_code == 0
        assert "Added character: Bob (char-02)" in result.output

        # Verify the character was added
        project = load_project(tmp_path)
        assert any(c.id == "char-02" and c.name == "Bob" for c in project.characters)

    def test_add_character_with_all_options(self, tmp_path: Path) -> None:
        """Add a character with all optional fields."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "character", "add", str(tmp_path),
                "--id", "char-03",
                "--name", "Charlie",
                "--role", "antagonist",
                "--desire", "Wants power",
                "--need", "Needs love",
                "--flaw", "Pride",
                "--secret", "Hidden past",
                "--trait", "cunning",
                "--trait", "charismatic",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        char = next(c for c in project.characters if c.id == "char-03")
        assert char.name == "Charlie"
        assert char.role == "antagonist"
        assert char.desire == "Wants power"
        assert char.flaw == "Pride"
        assert "cunning" in char.traits

    def test_add_character_duplicate_id_fails(self, tmp_path: Path) -> None:
        """Adding a character with duplicate ID fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["character", "add", str(tmp_path), "--id", "char-01", "--name", "Duplicate"],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output


class TestCharacterList:
    """Tests for character list command."""

    def test_list_characters_table(self, tmp_path: Path) -> None:
        """List characters in table format."""
        create_test_project(tmp_path)

        result = runner.invoke(app, ["character", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "char-01" in result.output
        assert "Alice" in result.output

    def test_list_characters_json(self, tmp_path: Path) -> None:
        """List characters in JSON format."""
        create_test_project(tmp_path)

        result = runner.invoke(app, ["character", "list", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        assert '"id": "char-01"' in result.output
        assert '"name": "Alice"' in result.output

    def test_list_characters_yaml(self, tmp_path: Path) -> None:
        """List characters in YAML format."""
        create_test_project(tmp_path)

        result = runner.invoke(app, ["character", "list", str(tmp_path), "--format", "yaml"])
        assert result.exit_code == 0
        assert "id: char-01" in result.output
        assert "name: Alice" in result.output

    def test_list_empty_characters(self, tmp_path: Path) -> None:
        """List with no characters shows appropriate message."""
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump({"premise": "A test story.", "scenes": [{"id": "scene-01"}]})
        )
        (tmp_path / "characters.yml").write_text(yaml.dump({"characters": []}))

        result = runner.invoke(app, ["character", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "No characters" in result.output


class TestCharacterRemove:
    """Tests for character remove command."""

    def test_remove_character_with_force(self, tmp_path: Path) -> None:
        """Remove a character with force flag."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["character", "remove", str(tmp_path), "char-01", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed character" in result.output

    def test_remove_nonexistent_character_fails(self, tmp_path: Path) -> None:
        """Removing nonexistent character fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["character", "remove", str(tmp_path), "char-99", "--force"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestCharacterEdit:
    """Tests for character edit command."""

    def test_edit_character_name(self, tmp_path: Path) -> None:
        """Edit character name."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["character", "edit", str(tmp_path), "char-01", "--name", "Alice Smith"],
        )
        assert result.exit_code == 0
        assert "Updated character" in result.output

        project = load_project(tmp_path)
        char = next(c for c in project.characters if c.id == "char-01")
        assert char.name == "Alice Smith"

    def test_edit_character_multiple_fields(self, tmp_path: Path) -> None:
        """Edit multiple character fields."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "character", "edit", str(tmp_path), "char-01",
                "--role", "antagonist",
                "--desire", "World domination",
                "--add-trait", "cunning",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        char = next(c for c in project.characters if c.id == "char-01")
        assert char.role == "antagonist"
        assert char.desire == "World domination"
        assert "cunning" in char.traits

    def test_edit_nonexistent_character_fails(self, tmp_path: Path) -> None:
        """Editing nonexistent character fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["character", "edit", str(tmp_path), "char-99", "--name", "Nobody"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestCharacterSuggest:
    """Tests for character suggest command."""

    def test_suggest_help_shows_options(self, tmp_path: Path) -> None:
        """Suggest command help shows all options."""
        result = runner.invoke(app, ["character", "suggest", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--idea" in output
        assert "--model" in output
        assert "--temperature" in output
        assert "--yes" in output
