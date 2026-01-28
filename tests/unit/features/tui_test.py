"""Tests for the Fabulae Textual TUI."""

from __future__ import annotations

from pathlib import Path

import pytest

from fabulae.features.tui.app import FabulaeApp
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
        assert "Project not found" in str(error.render_line(0))


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
