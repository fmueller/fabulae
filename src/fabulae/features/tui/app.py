"""Main Textual application for Fabulae TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import App

from fabulae import __version__
from fabulae.features.tui.screens.project import ProjectScreen
from fabulae.features.tui.screens.welcome import WelcomeScreen
from fabulae.models import LiteratureFormat


class FabulaeApp(App[None]):
    """Fabulae interactive TUI application."""

    TITLE = f"Fabulae v{__version__}"
    CSS_PATH = "styles.tcss"

    def __init__(self, project_path: Path, start_create: bool = False) -> None:
        super().__init__()
        self.project_path = project_path
        self.start_create = start_create

    async def on_mount(self) -> None:
        """Set up the initial screen based on project state."""
        if self.start_create:
            self.push_screen(WelcomeScreen(self.project_path), callback=self._on_welcome_result)
        else:
            self.push_screen(ProjectScreen(self.project_path))

    def _on_welcome_result(self, result: tuple[str, LiteratureFormat, str | None] | None) -> None:
        """Handle the result from the WelcomeScreen."""
        if result is not None:
            idea, format_value, shape = result
            self.run_worker(self._run_create(idea, format_value, shape))
        else:
            self.exit()

    async def _run_create(self, idea: str, format_value: LiteratureFormat, shape: str | None) -> None:
        """Run project creation and then show the project view."""
        from fabulae.features.create.schemas import CreateOptions
        from fabulae.features.create.service import generate_project_from_idea
        from fabulae.llm import resolve_config
        from fabulae.models import save_project

        config = resolve_config(None, None, None, None, None)

        options = CreateOptions(
            shape_id=shape,
            no_shape=shape is None,
        )

        self.notify("Creating project... This may take a moment.")

        try:
            project = await generate_project_from_idea(
                idea=idea,
                format_name=format_value,
                config=config,
                output_dir=self.project_path,
                options=options,
            )
            save_project(project, self.project_path)
            self.notify("Project created successfully!")
            self.push_screen(ProjectScreen(self.project_path))
        except Exception as exc:
            self.notify(f"Creation failed: {exc}", severity="error")
            self.exit()
