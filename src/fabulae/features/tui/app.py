"""Main Textual application for Fabulae."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
from textual.app import App

from fabulae.features.tui.loaders import load_project_relaxed
from fabulae.features.tui.screens.project import ProjectScreen
from fabulae.features.tui.screens.welcome import WelcomeScreen
from fabulae.features.tui.state import TuiProjectState
from fabulae.models import load_project


class FabulaeApp(App[None]):
    """Fabulae Textual application."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, project_path: Path, start_create: bool = False) -> None:
        super().__init__()
        self.project_path = project_path
        self.start_create = start_create
        self.state = TuiProjectState(project_path=project_path)

    def on_mount(self) -> None:
        if self.start_create:
            self.push_screen(WelcomeScreen(self.state))
            return

        try:
            self.state.project = load_project(self.project_path)
            self.push_screen(ProjectScreen(self.state))
            return
        except (FileNotFoundError, ValueError, ValidationError) as exc:
            self.state.load_error = str(exc)

        config_path = self.project_path / "fabulae.yml"
        plot_path = self.project_path / "plot.yml"
        if config_path.exists() or plot_path.exists():
            self.state.project = load_project_relaxed(self.project_path)
            self.push_screen(ProjectScreen(self.state))
            return

        screen = WelcomeScreen(self.state)
        screen.set_error("Project not found. Create a new project to continue.")
        self.push_screen(screen)
