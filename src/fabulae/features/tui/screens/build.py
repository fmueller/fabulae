"""Build progress screen for the Fabulae TUI."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Button, LoadingIndicator, ProgressBar, Static

from fabulae.features.build.service import build_project
from fabulae.features.build.writer import write_build_output
from fabulae.features.tui.state import TuiProjectState
from fabulae.llm import resolve_config


class BuildScreen(Screen[None]):
    """Build progress and results screen."""

    def __init__(self, state: TuiProjectState) -> None:
        super().__init__()
        self.state = state
        self._progress_timer: Timer | None = None

    def compose(self) -> ComposeResult:
        title = self._project_title()
        with Vertical(id="build-container"):
            yield Static(f"Building {title}...", id="build-title")
            yield LoadingIndicator(id="build-loading")
            yield ProgressBar(total=100, id="build-progress", show_eta=False)
            yield Static("", id="build-status")
            yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        self._start_progress_animation()
        self.run_worker(self._run_build(), exclusive=True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.app.pop_screen()

    def _project_title(self) -> str:
        project = self.state.project
        if project is None:
            return "project"
        return project.plot.title or project.config.title or "project"

    async def _run_build(self) -> None:
        project = self.state.project
        if project is None:
            self.app.call_from_thread(self._finish_failure, "No project loaded.")
            return

        try:
            config = resolve_config(None, None, None, None, None)
            result = await build_project(project, config, seed=None, progress=None)
        except Exception as exc:  # noqa: BLE001
            self.app.call_from_thread(self._finish_failure, f"Build failed: {exc}")
            return

        output_dir = self.state.project_path / "output"
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        build_dir = output_dir / timestamp
        write_build_output(result, build_dir, "md")

        self.app.call_from_thread(self._finish_success, result.total_word_count, str(build_dir))

    def _start_progress_animation(self) -> None:
        progress = self.query_one("#build-progress", ProgressBar)
        progress.update(progress=0)

        if self._progress_timer:
            self._progress_timer.stop()

        def tick() -> None:
            current = progress.progress or 0
            if current < 95:
                progress.update(progress=min(current + 1, 95))

        self._progress_timer = self.set_interval(0.2, tick)

    def _finish_success(self, word_count: int, build_dir: str | None) -> None:
        self._stop_progress_animation()
        progress = self.query_one("#build-progress", ProgressBar)
        progress.update(progress=100)
        output_text = f"✓ Build complete! {word_count:,} words."
        if build_dir:
            output_text = f"{output_text} Output: {build_dir}"
        self.query_one("#build-status", Static).update(output_text)
        self.query_one("#build-loading", LoadingIndicator).add_class("hidden")

    def _finish_failure(self, message: str) -> None:
        self._stop_progress_animation()
        self.query_one("#build-status", Static).update(message)
        self.query_one("#build-loading", LoadingIndicator).add_class("hidden")

    def _stop_progress_animation(self) -> None:
        if self._progress_timer:
            self._progress_timer.stop()
            self._progress_timer = None
