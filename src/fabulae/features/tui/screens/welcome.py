"""Welcome screen for creating new projects."""

from __future__ import annotations

from typing import cast

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Button, Input, LoadingIndicator, ProgressBar, Select, Static

from fabulae.features.create.schemas import CreateOptions
from fabulae.features.create.service import CreateProjectError, generate_project_from_idea
from fabulae.features.create.shapes.loader import load_all_shapes
from fabulae.features.tui.screens.project import ProjectScreen
from fabulae.features.tui.state import TuiProjectState
from fabulae.llm import resolve_config
from fabulae.models import AVAILABLE_FORMATS, LiteratureFormat, sanitize_project, save_project


class WelcomeScreen(Screen[None]):
    """Welcome screen for creating new projects."""

    def __init__(self, state: TuiProjectState) -> None:
        super().__init__()
        self.state = state
        self._progress_timer: Timer | None = None
        self._pending_error: str | None = None

    def compose(self) -> ComposeResult:
        yield Static("Fabulae v0.1.0", id="title")
        yield Static("Welcome to Fabulae!")
        yield Static("Enter your story idea:")
        yield Input(placeholder="A detective investigates...", id="idea")
        shape_options = self._shape_options()
        with Horizontal(id="selectors"):
            yield Select(
                [(fmt, fmt) for fmt in AVAILABLE_FORMATS],
                value="novel",
                id="format",
            )
            yield Select(shape_options, value=shape_options[0][1], id="shape")
        with Horizontal(id="buttons"):
            yield Button("Create Project", variant="primary", id="create")
            yield Button("Cancel", id="cancel")
        yield Static("", id="error")
        yield LoadingIndicator(id="loading", classes="hidden")
        yield ProgressBar(total=100, id="progress", show_eta=False)
        yield Static("", id="progress-label")

    def _shape_options(self) -> list[tuple[str, str]]:
        shapes = load_all_shapes()
        if not shapes:
            return [("", "No shapes available")]
        return [(shape.name, shape.id) for shape in shapes]

    def set_error(self, message: str) -> None:
        if not self.is_mounted:
            self._pending_error = message
            return
        self.query_one("#error", Static).update(message)

    def on_mount(self) -> None:
        if self.query_one(ProgressBar).progress is None:
            self.query_one(ProgressBar).update(progress=0)
        if self._pending_error:
            self.query_one("#error", Static).update(self._pending_error)
            self._pending_error = None

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.exit()
            return

        if event.button.id != "create":
            return

        idea = self.query_one("#idea", Input).value.strip()
        if not idea:
            self.set_error("Please enter a story idea to continue.")
            return

        format_value = self.query_one("#format", Select).value
        shape_value = self.query_one("#shape", Select).value

        if format_value is None or shape_value is None:
            self.set_error("Please choose a format and shape.")
            return

        self.set_error("")
        self.query_one("#loading", LoadingIndicator).remove_class("hidden")
        self.query_one("#progress-label", Static).update("Creating project...")

        self._start_progress_animation()
        self.run_worker(
            self._run_create(
                idea=idea,
                format_name=str(format_value),
                shape_id=str(shape_value),
            ),
            exclusive=True,
        )

    def _start_progress_animation(self) -> None:
        progress = self.query_one(ProgressBar)
        progress.update(progress=0)

        if self._progress_timer:
            self._progress_timer.stop()

        def tick() -> None:
            current = progress.progress or 0
            if current < 95:
                progress.update(progress=min(current + 2, 95))

        self._progress_timer = self.set_interval(0.15, tick)

    async def _run_create(self, idea: str, format_name: str, shape_id: str) -> None:
        try:
            config = resolve_config(None, None, None, None, None)
            options = CreateOptions(shape_id=shape_id)
            project = await generate_project_from_idea(
                idea=idea,
                format_name=cast(LiteratureFormat, format_name),
                config=config,
                output_dir=self.state.project_path,
                options=options,
            )
            sanitize_project(project)
            save_project(project, self.state.project_path)
            self.state.project = project
        except (CreateProjectError, ValueError) as exc:
            self.app.call_from_thread(self.set_error, f"Create failed: {exc}")
            self.app.call_from_thread(self._stop_progress_animation, False)
            return

        self.app.call_from_thread(self._stop_progress_animation, True)
        self.app.call_from_thread(self.app.push_screen, ProjectScreen(self.state))

    def _stop_progress_animation(self, success: bool) -> None:
        if self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer = None

        progress = self.query_one(ProgressBar)
        progress.update(progress=100 if success else progress.progress)
        self.query_one("#loading", LoadingIndicator).add_class("hidden")
        label = "Project created!" if success else "Creation failed."
        self.query_one("#progress-label", Static).update(label)
