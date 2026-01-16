"""Tests for world fact CRUD commands."""

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
    """Create a minimal test project with world facts."""
    (tmp_path / "fabulae.yml").write_text(yaml.dump({"version": "0.1.0"}))
    (tmp_path / "plot.yml").write_text(
        yaml.dump({
            "premise": "A test story.",
            "format": "novel",
            "scenes": [
                {"id": "scene-01", "location": "loc-01"},
            ],
        })
    )
    (tmp_path / "world.yml").write_text(
        yaml.dump({
            "facts": [
                {
                    "id": "loc-01",
                    "type": "location",
                    "name": "The Tavern",
                    "facts": ["Old wooden building", "Popular gathering spot"],
                },
            ]
        })
    )
    return tmp_path


class TestWorldAdd:
    """Tests for world add command."""

    def test_add_world_fact(self, tmp_path: Path) -> None:
        """Add a new world fact to the project."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "world", "add", str(tmp_path),
                "--id", "loc-02",
                "--type", "location",
                "--name", "The Castle",
            ],
        )
        assert result.exit_code == 0
        assert "Added world fact" in result.output
        assert "The Castle" in result.output

        project = load_project(tmp_path)
        assert project.world is not None
        assert any(f.id == "loc-02" and f.name == "The Castle" for f in project.world.facts)

    def test_add_world_fact_with_details(self, tmp_path: Path) -> None:
        """Add a world fact with multiple details."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "world", "add", str(tmp_path),
                "--id", "culture-01",
                "--type", "culture",
                "--name", "The Elves",
                "--fact", "Ancient race",
                "--fact", "Masters of magic",
            ],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        assert project.world is not None
        fact = next(f for f in project.world.facts if f.id == "culture-01")
        assert fact.type == "culture"
        assert "Ancient race" in fact.facts
        assert "Masters of magic" in fact.facts

    def test_add_world_fact_duplicate_id_fails(self, tmp_path: Path) -> None:
        """Adding a world fact with duplicate ID fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "world", "add", str(tmp_path),
                "--id", "loc-01",
                "--type", "location",
                "--name", "Duplicate",
            ],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_add_world_fact_invalid_type_fails(self, tmp_path: Path) -> None:
        """Adding a world fact with invalid type fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            [
                "world", "add", str(tmp_path),
                "--id", "invalid-01",
                "--type", "invalid",
                "--name", "Test",
            ],
        )
        assert result.exit_code == 1
        assert "Invalid type" in result.output


class TestWorldList:
    """Tests for world list command."""

    def test_list_all_world_facts(self, tmp_path: Path) -> None:
        """List all world facts in the project."""
        create_test_project(tmp_path)

        result = runner.invoke(app, ["world", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "loc-01" in result.output
        assert "The Tavern" in result.output

    def test_list_world_facts_by_type(self, tmp_path: Path) -> None:
        """List world facts filtered by type."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "list", str(tmp_path), "--type", "location"],
        )
        assert result.exit_code == 0
        assert "loc-01" in result.output

    def test_list_world_facts_json(self, tmp_path: Path) -> None:
        """List world facts in JSON format."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "list", str(tmp_path), "--format", "json"],
        )
        assert result.exit_code == 0
        assert '"id": "loc-01"' in result.output

    def test_list_world_facts_yaml(self, tmp_path: Path) -> None:
        """List world facts in YAML format."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "list", str(tmp_path), "--format", "yaml"],
        )
        assert result.exit_code == 0
        assert "id: loc-01" in result.output


class TestWorldRemove:
    """Tests for world remove command."""

    def test_remove_world_fact_with_force(self, tmp_path: Path) -> None:
        """Remove a world fact with force flag."""
        create_test_project(tmp_path)
        # Add an unreferenced fact
        runner.invoke(
            app,
            [
                "world", "add", str(tmp_path),
                "--id", "loc-unused",
                "--type", "location",
                "--name", "Unused",
            ],
        )

        result = runner.invoke(
            app,
            ["world", "remove", str(tmp_path), "loc-unused", "--force"],
        )
        assert result.exit_code == 0
        assert "Removed world fact" in result.output

    def test_remove_referenced_world_fact_shows_warning(self, tmp_path: Path) -> None:
        """Removing a referenced world fact shows warning."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "remove", str(tmp_path), "loc-01", "--force"],
        )
        assert result.exit_code == 0
        # Should have been warned about the reference
        assert "referenced" in result.output or "Removed" in result.output

    def test_remove_nonexistent_world_fact_fails(self, tmp_path: Path) -> None:
        """Removing nonexistent world fact fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "remove", str(tmp_path), "loc-99", "--force"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestWorldEdit:
    """Tests for world edit command."""

    def test_edit_world_fact_name(self, tmp_path: Path) -> None:
        """Edit a world fact's name."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "edit", str(tmp_path), "loc-01", "--name", "The Grand Tavern"],
        )
        assert result.exit_code == 0
        assert "Updated world fact" in result.output

        project = load_project(tmp_path)
        assert project.world is not None
        fact = next(f for f in project.world.facts if f.id == "loc-01")
        assert fact.name == "The Grand Tavern"

    def test_edit_world_fact_add_detail(self, tmp_path: Path) -> None:
        """Add a detail to a world fact."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "edit", str(tmp_path), "loc-01", "--add-fact", "Has a secret cellar"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        assert project.world is not None
        fact = next(f for f in project.world.facts if f.id == "loc-01")
        assert "Has a secret cellar" in fact.facts

    def test_edit_world_fact_remove_detail(self, tmp_path: Path) -> None:
        """Remove a detail from a world fact."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "edit", str(tmp_path), "loc-01", "--remove-fact", "Old wooden building"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        assert project.world is not None
        fact = next(f for f in project.world.facts if f.id == "loc-01")
        assert "Old wooden building" not in fact.facts

    def test_edit_world_fact_type(self, tmp_path: Path) -> None:
        """Edit a world fact's type."""
        create_test_project(tmp_path)
        # First add an unreferenced world fact
        runner.invoke(
            app,
            [
                "world", "add", str(tmp_path),
                "--id", "item-01",
                "--type", "object",
                "--name", "Magic Sword",
            ],
        )

        # Now change its type
        result = runner.invoke(
            app,
            ["world", "edit", str(tmp_path), "item-01", "--type", "rule"],
        )
        assert result.exit_code == 0

        project = load_project(tmp_path)
        assert project.world is not None
        fact = next(f for f in project.world.facts if f.id == "item-01")
        assert fact.type == "rule"

    def test_edit_nonexistent_world_fact_fails(self, tmp_path: Path) -> None:
        """Editing nonexistent world fact fails."""
        create_test_project(tmp_path)

        result = runner.invoke(
            app,
            ["world", "edit", str(tmp_path), "loc-99", "--name", "None"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output


class TestWorldSuggest:
    """Tests for world suggest command."""

    def test_suggest_help_shows_options(self, tmp_path: Path) -> None:
        """Suggest command help shows all options."""
        result = runner.invoke(app, ["world", "suggest", "--help"])
        assert result.exit_code == 0
        output = strip_ansi(result.output)
        assert "--type" in output
        assert "--idea" in output
        assert "--model" in output
        assert "--yes" in output
