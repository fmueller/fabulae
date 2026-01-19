"""Tests for chapter CRUD commands."""

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
    """Create a minimal test project with chapters."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test story.",
                "format": "novel",
                "chapters": [
                    {"id": "chapter-01", "title": "Beginning", "scene_ids": ["scene-01"]},
                ],
                "scenes": [
                    {"id": "scene-01", "summary": "First scene"},
                ],
            }
        )
    )
    return tmp_path


class TestChapterAdd:
    """Tests for chapter add command."""

    def test_add_chapter(self, tmp_path: Path) -> None:
        """Add a new chapter to the project."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "add", str(tmp_path), "--id", "chapter-02"],
        )
        assert result.exit_code == 0
        assert "Added chapter" in result.output
        assert "chapter-02" in result.output

        project = load_project(tmp_path)
        assert any(c.id == "chapter-02" for c in project.plot.chapters)

    def test_add_chapter_with_title(self, tmp_path: Path) -> None:
        """Add a chapter with title."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "chapter",
                "add",
                str(tmp_path),
                "--id",
                "chapter-03",
                "--title",
                "The Middle",
                "--summary",
                "Things get complicated",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        chapter = next(c for c in project.plot.chapters if c.id == "chapter-03")
        assert chapter.title == "The Middle"
        assert chapter.summary == "Things get complicated"

    def test_add_chapter_duplicate_id_fails(self, tmp_path: Path) -> None:
        """Adding a chapter with duplicate ID fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "add", str(tmp_path), "--id", "chapter-01"],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output


class TestChapterList:
    """Tests for chapter list command."""

    def test_list_chapters(self, tmp_path: Path) -> None:
        """List all chapters in the project."""
        create_test_project(tmp_path)

        result = runner.invoke(app, ["chapter", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "chapter-01" in result.output
        assert "Beginning" in result.output

    def test_list_chapters_json(self, tmp_path: Path) -> None:
        """List chapters in JSON format."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "list", str(tmp_path), "--format", "json"],
        )
        assert result.exit_code == 0
        assert '"id": "chapter-01"' in result.output

    def test_list_chapters_yaml(self, tmp_path: Path) -> None:
        """List chapters in YAML format."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "list", str(tmp_path), "--format", "yaml"],
        )
        assert result.exit_code == 0
        assert "id: chapter-01" in result.output


class TestChapterRemove:
    """Tests for chapter remove command."""

    def test_remove_empty_chapter_with_force(self, tmp_path: Path) -> None:
        """Remove an empty chapter with force flag."""
        create_test_project(tmp_path)
        # First add an empty chapter
        runner.invoke(app, ["chapter", "add", str(tmp_path), "--id", "chapter-empty"])

        result = runner.invoke(
            app,
            ["chapter", "remove", str(tmp_path), "chapter-empty", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed chapter" in result.output

    def test_remove_chapter_with_scenes_requires_explicit_action(self, tmp_path: Path) -> None:
        """Removing chapter with scenes requires --move-scenes-to or --cascade."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "remove", str(tmp_path), "chapter-01", "--force"],
        )
        assert result.exit_code == 1
        assert "scene(s)" in result.output
        assert "--move-scenes-to" in result.output
        assert "--cascade" in result.output

    def test_remove_chapter_with_move_scenes_to(self, tmp_path: Path) -> None:
        """Remove chapter and move its scenes to another chapter."""
        create_test_project(tmp_path)
        # Add target chapter
        runner.invoke(app, ["chapter", "add", str(tmp_path), "--id", "chapter-02"])

        result = runner.invoke(
            app,
            ["chapter", "remove", str(tmp_path), "chapter-01", "--move-scenes-to", "chapter-02"],
        )
        assert result.exit_code == 0
        assert "Moved" in result.output
        assert "Removed chapter" in result.output

        # Verify scenes moved to new chapter
        project = load_project(tmp_path)
        chapter_02 = next(c for c in project.plot.chapters if c.id == "chapter-02")
        assert chapter_02.scene_ids is not None
        assert "scene-01" in chapter_02.scene_ids

    def test_remove_chapter_with_cascade_deletes_scenes(self, tmp_path: Path) -> None:
        """Remove chapter with --cascade deletes the chapter and its scenes."""
        # Create project with two chapters so we can delete one
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A test story.",
                    "format": "novel",
                    "chapters": [
                        {"id": "chapter-01", "title": "First", "scene_ids": ["scene-01"]},
                        {"id": "chapter-02", "title": "Second", "scene_ids": ["scene-02"]},
                    ],
                    "scenes": [
                        {"id": "scene-01", "summary": "First scene"},
                        {"id": "scene-02", "summary": "Second scene"},
                    ],
                }
            )
        )

        result = runner.invoke(
            app,
            ["chapter", "remove", str(tmp_path), "chapter-01", "--cascade"],
            input="y\n",
        )
        assert result.exit_code == 0
        assert "Removed chapter" in result.output

        # Verify chapter and its scenes are deleted, but other content remains
        project = load_project(tmp_path)
        assert not any(c.id == "chapter-01" for c in project.plot.chapters)
        assert not any(s.id == "scene-01" for s in project.plot.scenes)
        # Verify chapter-02 and scene-02 still exist
        assert any(c.id == "chapter-02" for c in project.plot.chapters)
        assert any(s.id == "scene-02" for s in project.plot.scenes)

    def test_remove_chapter_cascade_requires_confirmation(self, tmp_path: Path) -> None:
        """--cascade requires confirmation before deleting scenes."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "remove", str(tmp_path), "chapter-01", "--cascade"],
            input="n\n",
        )
        # Should abort without deleting
        assert "not removed" in result.output.lower() or result.exit_code == 0

        # Verify chapter still exists
        project = load_project(tmp_path)
        assert any(c.id == "chapter-01" for c in project.plot.chapters)

    def test_remove_chapter_move_to_nonexistent_fails(self, tmp_path: Path) -> None:
        """Moving scenes to nonexistent chapter fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "remove", str(tmp_path), "chapter-01", "--move-scenes-to", "nonexistent"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_remove_nonexistent_chapter_fails(self, tmp_path: Path) -> None:
        """Removing nonexistent chapter fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "remove", str(tmp_path), "chapter-99", "--force"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestChapterEdit:
    """Tests for chapter edit command."""

    def test_edit_chapter_title(self, tmp_path: Path) -> None:
        """Edit a chapter's title."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "edit", str(tmp_path), "chapter-01", "--title", "New Title"],
        )
        assert result.exit_code == 0
        assert "Updated chapter" in result.output

        project = load_project(tmp_path)
        chapter = next(c for c in project.plot.chapters if c.id == "chapter-01")
        assert chapter.title == "New Title"

    def test_edit_chapter_summary(self, tmp_path: Path) -> None:
        """Edit a chapter's summary."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "edit", str(tmp_path), "chapter-01", "--summary", "New summary"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        chapter = next(c for c in project.plot.chapters if c.id == "chapter-01")
        assert chapter.summary == "New summary"

    def test_edit_nonexistent_chapter_fails(self, tmp_path: Path) -> None:
        """Editing nonexistent chapter fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "edit", str(tmp_path), "chapter-99", "--title", "None"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestChapterSuggest:
    """Tests for chapter suggest command."""

    def test_suggest_help_shows_options(self, tmp_path: Path) -> None:
        """Suggest command help shows all options."""
        result = runner.invoke(app, ["chapter", "suggest", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--idea" in output
        assert "--model" in output
        assert "--yes" in output


class TestChapterAddValidation:
    """Tests for chapter add input validation."""

    def test_add_chapter_invalid_id_shows_clean_error(self, tmp_path: Path) -> None:
        """Adding chapter with invalid ID shows clean error, not traceback."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "add", str(tmp_path), "--id", "UPPERCASE"],
        )
        assert result.exit_code == 1
        # Should show clean error message
        assert "Invalid ID" in result.output or "invalid" in result.output.lower()
        # Should NOT show traceback
        assert "Traceback" not in result.output
        assert "ValidationError" not in result.output

    def test_add_chapter_id_with_spaces_shows_clean_error(self, tmp_path: Path) -> None:
        """Adding chapter with spaces in ID shows clean error."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["chapter", "add", str(tmp_path), "--id", "has spaces"],
        )
        assert result.exit_code == 1
        assert "Traceback" not in result.output
