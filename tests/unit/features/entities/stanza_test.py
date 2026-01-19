"""Tests for stanza CRUD commands."""

from pathlib import Path

import yaml

from fabulae.main import app
from fabulae.models import load_project
from tests.conftest import runner, strip_ansi


def create_poem_project(tmp_path: Path) -> Path:
    """Create a minimal poem test project."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A poem about nature.",
                "format": "poem",
                "stanzas": [
                    {"id": "stanza-01", "lines": ["The wind blows cold.", "Through ancient pines."]},
                    {"id": "stanza-02", "lines": ["Stars shine bright.", "In winter night."]},
                ],
            }
        )
    )
    return tmp_path


def create_prose_project(tmp_path: Path) -> Path:
    """Create a minimal prose (novel) test project."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test story.",
                "format": "novel",
                "scenes": [
                    {"id": "scene-01", "summary": "First scene"},
                ],
            }
        )
    )
    return tmp_path


class TestStanzaAdd:
    """Tests for stanza add command."""

    def test_add_stanza(self, tmp_path: Path) -> None:
        """Add a new stanza to poem project."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "stanza",
                "add",
                str(tmp_path),
                "--id",
                "stanza-03",
                "--line",
                "A new line of verse.",
            ],
        )
        assert result.exit_code == 0
        assert "Added stanza" in result.output

        project = load_project(tmp_path)
        assert any(s.id == "stanza-03" for s in project.plot.stanzas)

    def test_add_stanza_with_multiple_lines(self, tmp_path: Path) -> None:
        """Add stanza with multiple lines."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "stanza",
                "add",
                str(tmp_path),
                "--id",
                "stanza-03",
                "--line",
                "First line here.",
                "--line",
                "Second line flows.",
                "--line",
                "Third line ends.",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        stanza = next(s for s in project.plot.stanzas if s.id == "stanza-03")
        assert len(stanza.lines) == 3
        assert stanza.lines[0] == "First line here."

    def test_add_stanza_with_meter_and_rhyme(self, tmp_path: Path) -> None:
        """Add stanza with meter and rhyme scheme."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "stanza",
                "add",
                str(tmp_path),
                "--id",
                "stanza-03",
                "--line",
                "A formal verse.",
                "--meter",
                "iambic pentameter",
                "--rhyme-scheme",
                "ABAB",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        stanza = next(s for s in project.plot.stanzas if s.id == "stanza-03")
        assert stanza.meter == "iambic pentameter"
        assert stanza.rhyme_scheme == "ABAB"

    def test_add_stanza_duplicate_id_fails(self, tmp_path: Path) -> None:
        """Adding stanza with duplicate ID fails."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "stanza",
                "add",
                str(tmp_path),
                "--id",
                "stanza-01",  # Already exists
                "--line",
                "Duplicate line.",
            ],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_add_stanza_invalid_id_shows_clean_error(self, tmp_path: Path) -> None:
        """Adding stanza with invalid ID shows clean error."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "add", str(tmp_path), "--id", "UPPERCASE", "--line", "Test line."],
        )
        assert result.exit_code == 1
        assert "Invalid ID" in result.output or "invalid" in result.output.lower()
        assert "Traceback" not in result.output

    def test_add_stanza_on_prose_format_fails(self, tmp_path: Path) -> None:
        """Adding stanza to prose project fails with format error."""
        create_prose_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "stanza",
                "add",
                str(tmp_path),
                "--id",
                "stanza-01",
                "--line",
                "Test line.",
            ],
        )
        assert result.exit_code == 1
        output = strip_ansi(result.output)
        assert "novel" in output or "prose" in output.lower()
        assert "scene" in output.lower()


class TestStanzaList:
    """Tests for stanza list command."""

    def test_list_stanzas(self, tmp_path: Path) -> None:
        """List all stanzas in poem project."""
        create_poem_project(tmp_path)

        result = runner.invoke(app, ["stanza", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "stanza-01" in result.output
        assert "stanza-02" in result.output

    def test_list_stanzas_json(self, tmp_path: Path) -> None:
        """List stanzas in JSON format."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "list", str(tmp_path), "--format", "json"],
        )
        assert result.exit_code == 0
        assert '"id": "stanza-01"' in result.output

    def test_list_stanzas_yaml(self, tmp_path: Path) -> None:
        """List stanzas in YAML format."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "list", str(tmp_path), "--format", "yaml"],
        )
        assert result.exit_code == 0
        assert "id: stanza-01" in result.output

    def test_list_stanzas_on_prose_format_fails(self, tmp_path: Path) -> None:
        """Listing stanzas on prose project fails with format error."""
        create_prose_project(tmp_path)

        result = runner.invoke(app, ["stanza", "list", str(tmp_path)])
        assert result.exit_code == 1
        output = strip_ansi(result.output)
        assert "novel" in output or "prose" in output.lower()


class TestStanzaEdit:
    """Tests for stanza edit command."""

    def test_edit_stanza_add_line(self, tmp_path: Path) -> None:
        """Add a line to a stanza."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "edit", str(tmp_path), "stanza-01", "--add-line", "A new line added."],
        )
        assert result.exit_code == 0
        assert "Updated stanza" in result.output

        project = load_project(tmp_path)
        stanza = next(s for s in project.plot.stanzas if s.id == "stanza-01")
        assert "A new line added." in stanza.lines

    def test_edit_stanza_remove_line(self, tmp_path: Path) -> None:
        """Remove a line from a stanza (by index)."""
        create_poem_project(tmp_path)

        # stanza-01 has 2 lines, remove line 0
        result = runner.invoke(
            app,
            ["stanza", "edit", str(tmp_path), "stanza-01", "--remove-line", "0"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        stanza = next(s for s in project.plot.stanzas if s.id == "stanza-01")
        assert len(stanza.lines) == 1
        assert "Through ancient pines." in stanza.lines[0]

    def test_edit_stanza_meter(self, tmp_path: Path) -> None:
        """Edit a stanza's meter."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "edit", str(tmp_path), "stanza-01", "--meter", "trochaic tetrameter"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        stanza = next(s for s in project.plot.stanzas if s.id == "stanza-01")
        assert stanza.meter == "trochaic tetrameter"

    def test_edit_stanza_rhyme_scheme(self, tmp_path: Path) -> None:
        """Edit a stanza's rhyme scheme."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "edit", str(tmp_path), "stanza-01", "--rhyme-scheme", "ABBA"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        stanza = next(s for s in project.plot.stanzas if s.id == "stanza-01")
        assert stanza.rhyme_scheme == "ABBA"

    def test_edit_nonexistent_stanza_fails(self, tmp_path: Path) -> None:
        """Editing nonexistent stanza fails."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "edit", str(tmp_path), "stanza-99", "--meter", "free verse"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestStanzaRemove:
    """Tests for stanza remove command."""

    def test_remove_stanza_with_force(self, tmp_path: Path) -> None:
        """Remove a stanza with force flag."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "remove", str(tmp_path), "stanza-01", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed stanza" in result.output

        project = load_project(tmp_path)
        assert not any(s.id == "stanza-01" for s in project.plot.stanzas)

    def test_remove_nonexistent_stanza_fails(self, tmp_path: Path) -> None:
        """Removing nonexistent stanza fails."""
        create_poem_project(tmp_path)

        result = runner.invoke(
            app,
            ["stanza", "remove", str(tmp_path), "stanza-99", "--force"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_remove_last_stanza_fails(self, tmp_path: Path) -> None:
        """Removing last stanza fails (format requires at least one)."""
        # Create project with only one stanza
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A single stanza poem.",
                    "format": "poem",
                    "stanzas": [
                        {"id": "stanza-01", "lines": ["Only stanza."]},
                    ],
                }
            )
        )

        result = runner.invoke(
            app,
            ["stanza", "remove", str(tmp_path), "stanza-01", "--force"],
        )
        assert result.exit_code == 1
        # Should fail during save_project validation


class TestStanzaSuggest:
    """Tests for stanza suggest command."""

    def test_suggest_help_shows_options(self, tmp_path: Path) -> None:
        """Suggest command help shows all options."""
        result = runner.invoke(app, ["stanza", "suggest", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--idea" in output
        assert "--model" in output
        assert "--yes" in output
