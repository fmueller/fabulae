"""Tests for the Fabulae Textual TUI."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from fabulae.features.tui.app import FabulaeApp
from fabulae.features.tui.modals.add_entity import _is_valid_id, _is_valid_int, _validate_form_data
from fabulae.features.tui.screens.project import ProjectScreen
from fabulae.features.tui.screens.welcome import WelcomeScreen
from fabulae.features.tui.widgets.project_tree import ProjectTree
from fabulae.models import Character, Plot, Project, ProjectConfig, Scene, save_project


@pytest.mark.anyio
async def test_tui_starts_in_welcome_for_missing_project(tmp_path: Path) -> None:
    """The TUI shows the welcome screen when no project exists."""
    app = FabulaeApp(tmp_path, start_create=False)

    async with app.run_test() as pilot:
        await pilot.pause()

        assert isinstance(app.screen, WelcomeScreen)
        error = app.screen.query_one("#error")
        # Error message comes from load_project when manifest is missing
        error_text = str(error.render_line(0))
        assert "not found" in error_text.lower() or "manifest" in error_text.lower()


@pytest.mark.anyio
async def test_tui_starts_in_project_screen_for_valid_project(tmp_path: Path) -> None:
    """The TUI shows the project screen when a valid project exists."""
    project = Project(
        config=ProjectConfig(version="0.1.0", title="Test Project"),
        plot=Plot(format="novel", premise="Test premise", scenes=[Scene(id="scene-one")]),
        characters=[Character(id="vera", name="Vera")],
    )
    save_project(project, tmp_path)

    app = FabulaeApp(tmp_path, start_create=False)

    async with app.run_test() as pilot:
        await pilot.pause()

        assert isinstance(app.screen, ProjectScreen)
        tree = app.screen.query_one(ProjectTree)
        labels = [str(child.label) for child in tree.root.children]
        assert "Characters (1)" in labels


@pytest.mark.anyio
async def test_tui_shows_welcome_when_relaxed_load_fails(tmp_path: Path) -> None:
    """The TUI shows welcome screen when relaxed load also fails."""
    # Create a malformed YAML file that will cause load_project_relaxed to fail
    (tmp_path / "fabulae.yml").write_text("{{{broken yaml")

    app = FabulaeApp(tmp_path, start_create=False)

    async with app.run_test() as pilot:
        await pilot.pause()

        # Should fall back to welcome screen with error, not crash
        assert isinstance(app.screen, WelcomeScreen)


@pytest.mark.anyio
async def test_tui_handles_relaxed_load_exception_gracefully(tmp_path: Path) -> None:
    """The TUI doesn't crash when load_project_relaxed raises an exception."""
    (tmp_path / "fabulae.yml").write_text("version: '0.1.0'\n")
    (tmp_path / "plot.yml").write_text("format: novel\npremise: test\n")

    # Simulate an unexpected exception in load_project_relaxed
    with patch(
        "fabulae.features.tui.app.load_project_relaxed",
        side_effect=RuntimeError("Unexpected error"),
    ):
        app = FabulaeApp(tmp_path, start_create=False)

        async with app.run_test() as pilot:
            await pilot.pause()

            # Should fall back to welcome screen, not crash
            assert isinstance(app.screen, WelcomeScreen)


class TestAddEntityValidation:
    """Tests for add entity modal validation."""

    def test_valid_id_accepts_lowercase_with_hyphens(self) -> None:
        assert _is_valid_id("scene-01") is True
        assert _is_valid_id("character-alice") is True
        assert _is_valid_id("my-long-id-123") is True

    def test_valid_id_rejects_invalid_formats(self) -> None:
        assert _is_valid_id("UPPERCASE") is False
        assert _is_valid_id("has spaces") is False
        assert _is_valid_id("has_underscores") is False
        assert _is_valid_id("-starts-with-hyphen") is False
        assert _is_valid_id("ends-with-hyphen-") is False

    def test_valid_int_accepts_numbers(self) -> None:
        assert _is_valid_int("42") is True
        assert _is_valid_int("0") is True
        assert _is_valid_int("1000") is True

    def test_valid_int_rejects_non_numbers(self) -> None:
        assert _is_valid_int("abc") is False
        assert _is_valid_int("12.5") is False
        assert _is_valid_int("") is False

    def test_validate_form_data_catches_invalid_id(self) -> None:
        errors = _validate_form_data("character", {"id": "INVALID_ID"})
        assert len(errors) == 1
        assert "ID must be lowercase" in errors[0]

    def test_validate_form_data_catches_invalid_target_words(self) -> None:
        errors = _validate_form_data("beat", {"id": "beat-01", "target_words": "abc"})
        assert len(errors) == 1
        assert "Target words must be a number" in errors[0]

    def test_validate_form_data_allows_empty_optional_fields(self) -> None:
        errors = _validate_form_data("beat", {"id": "beat-01", "target_words": ""})
        assert len(errors) == 0
