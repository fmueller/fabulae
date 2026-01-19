"""Tests for fragment CRUD commands."""

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


def create_micro_prose_project(tmp_path: Path) -> Path:
    """Create a minimal micro-prose test project."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A flash fiction test.",
                "format": "micro-prose",
                "fragments": [
                    {"id": "fragment-01", "content": "First fragment content."},
                    {"id": "fragment-02", "content": "Second fragment content."},
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


class TestFragmentAdd:
    """Tests for fragment add command."""

    def test_add_fragment(self, tmp_path: Path) -> None:
        """Add a new fragment to micro-prose project."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "fragment",
                "add",
                str(tmp_path),
                "--id",
                "fragment-03",
                "--content",
                "New fragment content.",
            ],
        )
        assert result.exit_code == 0
        assert "Added fragment" in result.output

        project = load_project(tmp_path)
        assert any(f.id == "fragment-03" for f in project.plot.fragments)

    def test_add_fragment_with_all_options(self, tmp_path: Path) -> None:
        """Add fragment with all optional fields."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "fragment",
                "add",
                str(tmp_path),
                "--id",
                "fragment-03",
                "--content",
                "New content.",
                "--target-words",
                "100",
                "--notes",
                "This is a note.",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        fragment = next(f for f in project.plot.fragments if f.id == "fragment-03")
        assert fragment.content == "New content."
        assert fragment.target_words == 100
        assert fragment.notes == "This is a note."

    def test_add_fragment_duplicate_id_fails(self, tmp_path: Path) -> None:
        """Adding fragment with duplicate ID fails."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "fragment",
                "add",
                str(tmp_path),
                "--id",
                "fragment-01",  # Already exists
                "--content",
                "Duplicate content.",
            ],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_add_fragment_invalid_id_shows_clean_error(self, tmp_path: Path) -> None:
        """Adding fragment with invalid ID shows clean error."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "add", str(tmp_path), "--id", "UPPERCASE", "--content", "Test"],
        )
        assert result.exit_code == 1
        assert "Invalid ID" in result.output or "invalid" in result.output.lower()
        assert "Traceback" not in result.output

    def test_add_fragment_on_prose_format_fails(self, tmp_path: Path) -> None:
        """Adding fragment to prose project fails with format error."""
        create_prose_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "fragment",
                "add",
                str(tmp_path),
                "--id",
                "fragment-01",
                "--content",
                "Test",
            ],
        )
        assert result.exit_code == 1
        output = strip_ansi(result.output)
        assert "novel" in output or "prose" in output.lower()
        assert "scene" in output.lower()


class TestFragmentList:
    """Tests for fragment list command."""

    def test_list_fragments(self, tmp_path: Path) -> None:
        """List all fragments in micro-prose project."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(app, ["fragment", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "fragment-01" in result.output
        assert "fragment-02" in result.output

    def test_list_fragments_json(self, tmp_path: Path) -> None:
        """List fragments in JSON format."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "list", str(tmp_path), "--format", "json"],
        )
        assert result.exit_code == 0
        assert '"id": "fragment-01"' in result.output

    def test_list_fragments_yaml(self, tmp_path: Path) -> None:
        """List fragments in YAML format."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "list", str(tmp_path), "--format", "yaml"],
        )
        assert result.exit_code == 0
        assert "id: fragment-01" in result.output

    def test_list_fragments_on_prose_format_fails(self, tmp_path: Path) -> None:
        """Listing fragments on prose project fails with format error."""
        create_prose_project(tmp_path)

        result = runner.invoke(app, ["fragment", "list", str(tmp_path)])
        assert result.exit_code == 1
        output = strip_ansi(result.output)
        assert "novel" in output or "prose" in output.lower()


class TestFragmentEdit:
    """Tests for fragment edit command."""

    def test_edit_fragment_content(self, tmp_path: Path) -> None:
        """Edit a fragment's content."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "edit", str(tmp_path), "fragment-01", "--content", "Updated content."],
        )
        assert result.exit_code == 0
        assert "Updated fragment" in result.output

        project = load_project(tmp_path)
        fragment = next(f for f in project.plot.fragments if f.id == "fragment-01")
        assert fragment.content == "Updated content."

    def test_edit_fragment_notes(self, tmp_path: Path) -> None:
        """Edit a fragment's notes."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "edit", str(tmp_path), "fragment-01", "--notes", "New notes."],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        fragment = next(f for f in project.plot.fragments if f.id == "fragment-01")
        assert fragment.notes == "New notes."

    def test_edit_fragment_target_words(self, tmp_path: Path) -> None:
        """Edit a fragment's target word count."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "edit", str(tmp_path), "fragment-01", "--target-words", "250"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        fragment = next(f for f in project.plot.fragments if f.id == "fragment-01")
        assert fragment.target_words == 250

    def test_edit_nonexistent_fragment_fails(self, tmp_path: Path) -> None:
        """Editing nonexistent fragment fails."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "edit", str(tmp_path), "fragment-99", "--content", "Test"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestFragmentRemove:
    """Tests for fragment remove command."""

    def test_remove_fragment_with_force(self, tmp_path: Path) -> None:
        """Remove a fragment with force flag."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "remove", str(tmp_path), "fragment-01", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed fragment" in result.output

        project = load_project(tmp_path)
        assert not any(f.id == "fragment-01" for f in project.plot.fragments)

    def test_remove_nonexistent_fragment_fails(self, tmp_path: Path) -> None:
        """Removing nonexistent fragment fails."""
        create_micro_prose_project(tmp_path)

        result = runner.invoke(
            app,
            ["fragment", "remove", str(tmp_path), "fragment-99", "--force"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_remove_last_fragment_fails(self, tmp_path: Path) -> None:
        """Removing last fragment fails (format requires at least one)."""
        # Create project with only one fragment
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A flash fiction test.",
                    "format": "micro-prose",
                    "fragments": [
                        {"id": "fragment-01", "content": "Only fragment."},
                    ],
                }
            )
        )

        result = runner.invoke(
            app,
            ["fragment", "remove", str(tmp_path), "fragment-01", "--force"],
        )
        assert result.exit_code == 1
        # Should fail during save_project validation


class TestFragmentSuggest:
    """Tests for fragment suggest command."""

    def test_suggest_help_shows_options(self, tmp_path: Path) -> None:
        """Suggest command help shows all options."""
        result = runner.invoke(app, ["fragment", "suggest", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--idea" in output
        assert "--model" in output
        assert "--yes" in output
