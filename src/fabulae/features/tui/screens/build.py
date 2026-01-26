"""Build progress and results screen for the Fabulae TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, ProgressBar, Static
from textual.worker import Worker, WorkerState

from fabulae.features.build.schemas import BuildOutput
from fabulae.models import Project


class BuildScreen(Screen[None]):
    """Build progress and results screen."""

    BINDINGS = [
        ("escape", "go_back", "Back"),
    ]

    def __init__(self, project: Project, project_path: Path) -> None:
        super().__init__()
        self.project = project
        self.project_path = project_path
        self._build_result: BuildOutput | None = None
        self._build_worker: Worker[BuildOutput] | None = None

    def compose(self) -> ComposeResult:
        title = self.project.plot.title or self.project.config.title or "Project"
        with Vertical(id="build-container"):
            yield Static(f"Building {title}...", id="build-title")
            yield ProgressBar(total=100, id="build-progress")
            yield Static("Preparing build...", id="build-status")
            with Horizontal(classes="build-buttons"):
                yield Button("Cancel", id="cancel")

    async def on_mount(self) -> None:
        """Start the build process."""
        self._build_worker = self.run_worker(self._run_build(), exclusive=True)

    async def _run_build(self) -> BuildOutput:
        """Run the build as an async worker."""
        from fabulae.features.build.service import build_project
        from fabulae.features.build.writer import write_build_output
        from fabulae.llm import resolve_config

        config = resolve_config(None, None, None, None, None)

        # Update status (runs in event loop, so direct calls work)
        self._update_status("Generating narrative...")
        self._update_progress(10)

        result = await build_project(self.project, config, seed=None)

        self._update_status("Writing output files...")
        self._update_progress(80)

        # Write output
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        output_dir = self.project_path / "output" / timestamp
        write_build_output(result, output_dir)

        self._update_progress(100)
        self._show_complete(str(output_dir), result.total_word_count)

        return result

    def _update_status(self, message: str) -> None:
        self.query_one("#build-status", Static).update(message)

    def _update_progress(self, value: int) -> None:
        self.query_one("#build-progress", ProgressBar).update(progress=float(value))

    def _show_complete(self, output_dir: str, word_count: int) -> None:
        self.query_one("#build-title", Static).update("Build Complete!")
        self.query_one("#build-status", Static).update(
            f"Output: {output_dir}\nWords: {word_count:,}"
        )
        # Replace cancel with back button
        cancel_btn = self.query_one("#cancel", Button)
        cancel_btn.label = "Back to Project"
        cancel_btn.id = "back"

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            if self._build_worker is not None and self._build_worker.state == WorkerState.RUNNING:
                self._build_worker.cancel()
            self.app.pop_screen()
        elif event.button.id == "back":
            self.app.pop_screen()

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        """Handle worker state changes."""
        if event.state == WorkerState.ERROR:
            error_msg = str(event.worker.error) if event.worker.error else "Unknown error"
            self._update_status(f"Build failed: {error_msg}")
            self.query_one("#build-title", Static).update("Build Failed")
            cancel_btn = self.query_one("#cancel", Button)
            cancel_btn.label = "Back"

    def action_go_back(self) -> None:
        """Go back to the project screen."""
        if self._build_worker is not None and self._build_worker.state == WorkerState.RUNNING:
            self._build_worker.cancel()
        self.app.pop_screen()
