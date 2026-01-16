"""Tests for beat CRUD commands."""

from pathlib import Path

import yaml
from typer.testing import CliRunner

from fabulae.main import app
from fabulae.models import load_project

runner = CliRunner()


def create_test_project(tmp_path: Path) -> Path:
    """Create a minimal test project with scenes."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump({
            "premise": "A test story.",
            "format": "novel",
            "scenes": [
                {
                    "id": "scene-01",
                    "summary": "First scene",
                    "beats": [
                        {"id": "beat-01", "kind": "setup", "summary": "Opening beat"},
                    ],
                },
                {
                    "id": "scene-02",
                    "summary": "Second scene",
                    "beats": [],
                },
            ],
        })
    )
    return tmp_path


class TestBeatAdd:
    """Tests for beat add command."""

    def test_add_beat(self, tmp_path: Path) -> None:
        """Add a new beat to a scene."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "beat", "add", str(tmp_path),
                "--scene", "scene-01",
                "--id", "beat-02",
                "--kind", "action",
            ],
        )
        assert result.exit_code == 0
        assert "Added beat: beat-02 to scene scene-01" in result.output

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        assert any(b.id == "beat-02" and b.kind == "action" for b in scene.beats)

    def test_add_beat_with_all_options(self, tmp_path: Path) -> None:
        """Add a beat with all optional fields."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "beat", "add", str(tmp_path),
                "--scene", "scene-02",
                "--id", "beat-03",
                "--kind", "dialogue",
                "--summary", "Characters argue",
                "--goal", "Convince the other",
                "--conflict", "Disagreement",
                "--outcome", "Stalemate",
                "--pace", "fast",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-02")
        beat = next(b for b in scene.beats if b.id == "beat-03")
        assert beat.kind == "dialogue"
        assert beat.summary == "Characters argue"
        assert beat.goal == "Convince the other"
        assert beat.pace == "fast"

    def test_add_beat_to_nonexistent_scene_fails(self, tmp_path: Path) -> None:
        """Adding a beat to nonexistent scene fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "beat", "add", str(tmp_path),
                "--scene", "scene-99",
                "--id", "beat-04",
                "--kind", "action",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_add_beat_duplicate_id_fails(self, tmp_path: Path) -> None:
        """Adding a beat with duplicate ID fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "beat", "add", str(tmp_path),
                "--scene", "scene-01",
                "--id", "beat-01",  # Already exists
                "--kind", "action",
            ],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output


class TestBeatList:
    """Tests for beat list command."""

    def test_list_all_beats(self, tmp_path: Path) -> None:
        """List all beats in the project."""
        create_test_project(tmp_path)

        result = runner.invoke(app, ["beat", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "beat-01" in result.output
        assert "scene-01" in result.output

    def test_list_beats_filtered_by_scene(self, tmp_path: Path) -> None:
        """List beats filtered by scene."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "list", str(tmp_path), "--scene", "scene-01"],
        )
        assert result.exit_code == 0
        assert "beat-01" in result.output

    def test_list_beats_json(self, tmp_path: Path) -> None:
        """List beats in JSON format."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "list", str(tmp_path), "--format", "json"],
        )
        assert result.exit_code == 0
        assert '"id": "beat-01"' in result.output

    def test_list_empty_scene_beats(self, tmp_path: Path) -> None:
        """List beats from empty scene shows appropriate message."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "list", str(tmp_path), "--scene", "scene-02"],
        )
        assert result.exit_code == 0
        assert "No beats" in result.output


class TestBeatMove:
    """Tests for beat move command."""

    def test_move_beat_to_another_scene(self, tmp_path: Path) -> None:
        """Move a beat to a different scene."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "move", str(tmp_path), "beat-01", "--to-scene", "scene-02"],
        )
        assert result.exit_code == 0
        assert "Moved beat" in result.output

        project = load_project(tmp_path)
        scene1 = next(s for s in project.plot.scenes if s.id == "scene-01")
        scene2 = next(s for s in project.plot.scenes if s.id == "scene-02")
        assert not any(b.id == "beat-01" for b in scene1.beats)
        assert any(b.id == "beat-01" for b in scene2.beats)

    def test_move_beat_with_position(self, tmp_path: Path) -> None:
        """Move a beat to specific position."""
        # First add a beat to scene-02
        create_test_project(tmp_path)
        runner.invoke(
            app,
            [
                "beat", "add", str(tmp_path),
                "--scene", "scene-02",
                "--id", "beat-existing",
                "--kind", "setup",
            ],
        )

        # Now move beat-01 to position 0
        result = runner.invoke(
            app,
            ["beat", "move", str(tmp_path), "beat-01", "--to-scene", "scene-02", "--position", "0"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        scene2 = next(s for s in project.plot.scenes if s.id == "scene-02")
        assert scene2.beats[0].id == "beat-01"

    def test_move_nonexistent_beat_fails(self, tmp_path: Path) -> None:
        """Moving nonexistent beat fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "move", str(tmp_path), "beat-99", "--to-scene", "scene-02"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestBeatRemove:
    """Tests for beat remove command."""

    def test_remove_beat_with_force(self, tmp_path: Path) -> None:
        """Remove a beat with force flag."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "remove", str(tmp_path), "beat-01", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed beat" in result.output

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        assert not any(b.id == "beat-01" for b in scene.beats)

    def test_remove_nonexistent_beat_fails(self, tmp_path: Path) -> None:
        """Removing nonexistent beat fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "remove", str(tmp_path), "beat-99", "--force"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestBeatEdit:
    """Tests for beat edit command."""

    def test_edit_beat(self, tmp_path: Path) -> None:
        """Edit a beat's properties."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "beat", "edit", str(tmp_path), "beat-01",
                "--kind", "climax",
                "--summary", "Updated summary",
            ],
        )
        assert result.exit_code == 0
        assert "Updated beat" in result.output

        project = load_project(tmp_path)
        scene = next(s for s in project.plot.scenes if s.id == "scene-01")
        beat = next(b for b in scene.beats if b.id == "beat-01")
        assert beat.kind == "climax"
        assert beat.summary == "Updated summary"

    def test_edit_nonexistent_beat_fails(self, tmp_path: Path) -> None:
        """Editing nonexistent beat fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["beat", "edit", str(tmp_path), "beat-99", "--kind", "action"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestBeatSuggest:
    """Tests for beat suggest command."""

    def test_suggest_help_shows_options(self, tmp_path: Path) -> None:
        """Suggest command help shows all options."""
        result = runner.invoke(app, ["beat", "suggest", "--help"])
        assert result.exit_code == 0
        assert "--scene" in result.output
        assert "--idea" in result.output
        assert "--model" in result.output
        assert "--yes" in result.output
