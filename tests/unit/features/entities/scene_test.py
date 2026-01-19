"""Tests for scene CRUD commands."""

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
    """Create a minimal test project with scenes and chapters."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump(
            {
                "premise": "A test story.",
                "format": "novel",
                "chapters": [
                    {"id": "chapter-01", "title": "Beginning", "scene_ids": ["scene-01"]},
                    {"id": "chapter-02", "title": "Middle", "scene_ids": []},
                ],
                "scenes": [
                    {"id": "scene-01", "summary": "First scene", "characters": ["char-01"]},
                ],
            }
        )
    )
    (tmp_path / "characters.yml").write_text(
        yaml.dump(
            {
                "characters": [
                    {"id": "char-01", "name": "Alice"},
                    {"id": "char-02", "name": "Bob"},
                ]
            }
        )
    )
    (tmp_path / "world.yml").write_text(
        yaml.dump(
            {
                "facts": [
                    {"id": "loc-01", "type": "location", "name": "Tavern"},
                    {"id": "artifact-01", "type": "object", "name": "Magic Sword"},
                    {"id": "rule-01", "type": "rule", "name": "No magic after midnight"},
                ]
            }
        )
    )
    return tmp_path


class TestSceneAdd:
    """Tests for scene add command."""

    def test_add_scene(self, tmp_path: Path) -> None:
        """Add a new scene to the project (must assign to chapter when chapters exist)."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "add", str(tmp_path), "--id", "scene-02", "--chapter", "chapter-02"],
        )
        assert result.exit_code == 0
        assert "Added scene: scene-02" in result.output

        project = load_project(tmp_path)
        assert any(s.id == "scene-02" for s in project.plot.scenes)

    def test_add_scene_to_chapter(self, tmp_path: Path) -> None:
        """Add a scene to a specific chapter."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "add",
                str(tmp_path),
                "--id",
                "scene-03",
                "--chapter",
                "chapter-02",
            ],
        )
        assert result.exit_code == 0
        assert "to chapter chapter-02" in result.output

        project = load_project(tmp_path)
        chapter = next(c for c in project.plot.chapters if c.id == "chapter-02")
        assert "scene-03" in (chapter.scene_ids or [])

    def test_add_scene_with_all_options(self, tmp_path: Path) -> None:
        """Add a scene with all optional fields."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "add",
                str(tmp_path),
                "--id",
                "scene-04",
                "--chapter",
                "chapter-02",
                "--location",
                "loc-01",
                "--time",
                "evening",
                "--summary",
                "A test scene",
                "--character",
                "char-01",
                "--character",
                "char-02",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-04")
        assert scene.location == "loc-01"
        assert scene.time == "evening"
        assert "char-01" in scene.characters
        assert "char-02" in scene.characters

    def test_add_scene_invalid_location_fails(self, tmp_path: Path) -> None:
        """Adding scene with invalid location fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "add",
                str(tmp_path),
                "--id",
                "scene-05",
                "--location",
                "invalid-loc",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestSceneList:
    """Tests for scene list command."""

    def test_list_all_scenes(self, tmp_path: Path) -> None:
        """List all scenes in the project."""
        create_test_project(tmp_path)

        result = runner.invoke(app, ["scene", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "scene-01" in result.output

    def test_list_scenes_by_chapter(self, tmp_path: Path) -> None:
        """List scenes filtered by chapter."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "list", str(tmp_path), "--chapter", "chapter-01"],
        )
        assert result.exit_code == 0
        assert "scene-01" in result.output

    def test_list_scenes_json(self, tmp_path: Path) -> None:
        """List scenes in JSON format."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "list", str(tmp_path), "--format", "json"],
        )
        assert result.exit_code == 0
        assert '"id": "scene-01"' in result.output


class TestSceneMove:
    """Tests for scene move command."""

    def test_move_scene_to_chapter(self, tmp_path: Path) -> None:
        """Move a scene to a different chapter."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "move", str(tmp_path), "scene-01", "--to-chapter", "chapter-02"],
        )
        assert result.exit_code == 0
        assert "Moved scene" in result.output

        project = load_project(tmp_path)
        chapter1 = next(c for c in project.plot.chapters if c.id == "chapter-01")
        chapter2 = next(c for c in project.plot.chapters if c.id == "chapter-02")
        assert "scene-01" not in (chapter1.scene_ids or [])
        assert "scene-01" in (chapter2.scene_ids or [])

    def test_move_nonexistent_scene_fails(self, tmp_path: Path) -> None:
        """Moving nonexistent scene fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "move", str(tmp_path), "scene-99", "--to-chapter", "chapter-02"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestSceneRemove:
    """Tests for scene remove command."""

    def test_remove_scene_with_force(self, tmp_path: Path) -> None:
        """Remove a scene with force flag."""
        create_test_project(tmp_path)

        # First add another scene so we can remove one (novel requires at least one scene)
        runner.invoke(
            app,
            ["scene", "add", str(tmp_path), "--id", "scene-02", "--chapter", "chapter-01"],
        )

        result = runner.invoke(
            app,
            ["scene", "remove", str(tmp_path), "scene-01", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed scene" in result.output

    def test_remove_nonexistent_scene_fails(self, tmp_path: Path) -> None:
        """Removing nonexistent scene fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "remove", str(tmp_path), "scene-99", "--force"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestSceneEdit:
    """Tests for scene edit command."""

    def test_edit_scene(self, tmp_path: Path) -> None:
        """Edit a scene's properties."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "edit",
                str(tmp_path),
                "scene-01",
                "--location",
                "loc-01",
                "--summary",
                "Updated summary",
            ],
        )
        assert result.exit_code == 0
        assert "Updated scene" in result.output

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        assert scene.location == "loc-01"
        assert scene.summary == "Updated summary"

    def test_edit_scene_add_character(self, tmp_path: Path) -> None:
        """Add a character to a scene."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "edit", str(tmp_path), "scene-01", "--add-character", "char-02"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        assert "char-02" in scene.characters


class TestSceneSuggest:
    """Tests for scene suggest command."""

    def test_suggest_help_shows_options(self, tmp_path: Path) -> None:
        """Suggest command help shows all options."""
        result = runner.invoke(app, ["scene", "suggest", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--chapter" in output
        assert "--idea" in output
        assert "--model" in output
        assert "--yes" in output


class TestSceneWorldFacts:
    """Tests for scene world_fact_ids management."""

    def test_add_scene_with_world_fact(self, tmp_path: Path) -> None:
        """Add a scene with world facts."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "add",
                str(tmp_path),
                "--id",
                "scene-02",
                "--chapter",
                "chapter-02",
                "--world-fact",
                "artifact-01",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-02")
        assert "artifact-01" in scene.world_fact_ids

    def test_add_scene_with_multiple_world_facts(self, tmp_path: Path) -> None:
        """Add a scene with multiple world facts."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "add",
                str(tmp_path),
                "--id",
                "scene-02",
                "--chapter",
                "chapter-02",
                "--world-fact",
                "artifact-01",
                "--world-fact",
                "rule-01",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-02")
        assert "artifact-01" in scene.world_fact_ids
        assert "rule-01" in scene.world_fact_ids

    def test_add_scene_with_invalid_world_fact_fails(self, tmp_path: Path) -> None:
        """Adding scene with invalid world fact fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "add",
                str(tmp_path),
                "--id",
                "scene-02",
                "--chapter",
                "chapter-02",
                "--world-fact",
                "nonexistent-fact",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_edit_scene_add_world_fact(self, tmp_path: Path) -> None:
        """Add a world fact to an existing scene."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "edit", str(tmp_path), "scene-01", "--add-world-fact", "artifact-01"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        assert "artifact-01" in scene.world_fact_ids

    def test_edit_scene_add_multiple_world_facts(self, tmp_path: Path) -> None:
        """Add multiple world facts to an existing scene."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "scene",
                "edit",
                str(tmp_path),
                "scene-01",
                "--add-world-fact",
                "artifact-01",
                "--add-world-fact",
                "rule-01",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        assert "artifact-01" in scene.world_fact_ids
        assert "rule-01" in scene.world_fact_ids

    def test_edit_scene_remove_world_fact(self, tmp_path: Path) -> None:
        """Remove a world fact from a scene."""
        # Create project with scene that has world_fact_ids
        create_test_project(tmp_path)
        # First add a world fact
        runner.invoke(
            app,
            ["scene", "edit", str(tmp_path), "scene-01", "--add-world-fact", "artifact-01"],
        )

        # Now remove it
        result = runner.invoke(
            app,
            ["scene", "edit", str(tmp_path), "scene-01", "--remove-world-fact", "artifact-01"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        assert "artifact-01" not in scene.world_fact_ids

    def test_edit_scene_add_invalid_world_fact_warns(self, tmp_path: Path) -> None:
        """Adding invalid world fact shows warning."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "edit", str(tmp_path), "scene-01", "--add-world-fact", "nonexistent"],
        )
        # Should still succeed but with warning
        assert result.exit_code == 0
        assert "not found" in result.output.lower() or "warning" in result.output.lower()


class TestSceneFormatValidation:
    """Tests for scene format validation."""

    def test_scene_add_on_micro_prose_fails_with_helpful_error(self, tmp_path: Path) -> None:
        """Adding scene to micro-prose project fails with format error."""
        # Create micro-prose project
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A micro story",
                    "format": "micro-prose",
                    "fragments": [{"id": "frag-01", "content": "Opening."}],
                }
            )
        )

        result = runner.invoke(
            app,
            ["scene", "add", str(tmp_path), "--id", "scene-01", "--summary", "Test"],
        )
        assert result.exit_code == 1
        assert "micro-prose" in result.output
        assert "fragment" in result.output.lower()

    def test_scene_add_on_poem_fails_with_helpful_error(self, tmp_path: Path) -> None:
        """Adding scene to poem project fails with format error."""
        # Create poem project
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A poem",
                    "format": "poem",
                    "stanzas": [{"id": "stanza-01", "lines": ["First line"]}],
                }
            )
        )

        result = runner.invoke(
            app,
            ["scene", "add", str(tmp_path), "--id", "scene-01", "--summary", "Test"],
        )
        assert result.exit_code == 1
        assert "poem" in result.output
        assert "stanza" in result.output.lower()

    def test_scene_list_on_micro_prose_fails_with_helpful_error(self, tmp_path: Path) -> None:
        """Listing scenes on micro-prose project fails with format error."""
        # Create micro-prose project
        (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
        (tmp_path / "plot.yml").write_text(
            yaml.dump(
                {
                    "premise": "A micro story",
                    "format": "micro-prose",
                    "fragments": [{"id": "frag-01", "content": "Opening."}],
                }
            )
        )

        result = runner.invoke(app, ["scene", "list", str(tmp_path)])
        assert result.exit_code == 1
        assert "micro-prose" in result.output
        assert "fragment" in result.output.lower()


class TestSceneAddValidation:
    """Tests for scene add input validation."""

    def test_add_scene_invalid_id_shows_clean_error(self, tmp_path: Path) -> None:
        """Adding scene with invalid ID shows clean error, not traceback."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "add", str(tmp_path), "--id", "UPPERCASE", "--chapter", "chapter-01"],
        )
        assert result.exit_code == 1
        # Should show clean error message
        assert "Invalid ID" in result.output or "invalid" in result.output.lower()
        # Should NOT show traceback
        assert "Traceback" not in result.output
        assert "ValidationError" not in result.output

    def test_add_scene_id_with_spaces_shows_clean_error(self, tmp_path: Path) -> None:
        """Adding scene with spaces in ID shows clean error."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["scene", "add", str(tmp_path), "--id", "has spaces", "--chapter", "chapter-01"],
        )
        assert result.exit_code == 1
        assert "Traceback" not in result.output
