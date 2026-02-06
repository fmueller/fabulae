"""Rich progress display for build command with dual timer (unit/total)."""

from __future__ import annotations

import time
from collections.abc import Callable, Generator
from contextlib import contextmanager

from rich.console import Console
from rich.progress import Progress, ProgressColumn, SpinnerColumn, Task, TextColumn
from rich.text import Text


class UnitDualTimeColumn(ProgressColumn):
    """Custom column showing unit_time / total_time.

    Unlike the create command's DualTimeColumn which shows phase/total,
    this shows the time spent on the current unit (scene/stanza/fragment)
    versus total build time.
    """

    def __init__(
        self,
        get_unit_elapsed: Callable[[], float],
        get_total_elapsed: Callable[[], float],
    ) -> None:
        super().__init__()
        self._get_unit_elapsed = get_unit_elapsed
        self._get_total_elapsed = get_total_elapsed

    def render(self, task: Task) -> Text:
        """Render the dual time display."""
        unit_elapsed = self._get_unit_elapsed()
        total_elapsed = self._get_total_elapsed()

        unit_str = self._format_time(unit_elapsed)
        total_str = self._format_time(total_elapsed)

        return Text(f"{unit_str} / {total_str}", style="progress.elapsed")

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as H:MM:SS or M:SS."""
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"


class BuildProgress:
    """Rich progress display for build command with dual timer tracking.

    Provides a self-contained progress display for the build feature that shows:
    - Dim status lines for each unit (e.g., "Building scene 1/12: scene-01")
    - A spinner at the bottom with dual timer: unit_time / total_time

    The dual timer is more meaningful than phase/total because:
    - unit_time resets for each scene/stanza/fragment
    - total_time tracks the entire build duration
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._start_time: float | None = None
        self._unit_start_time: float | None = None

    def start(self) -> None:
        """Mark the start of the build process."""
        self._start_time = time.monotonic()

    def start_unit(self) -> None:
        """Reset the unit timer for the current scene/stanza/fragment."""
        self._unit_start_time = time.monotonic()

    def _get_total_elapsed(self) -> float:
        """Get total elapsed time since start()."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    def _get_unit_elapsed(self) -> float:
        """Get elapsed time since start_unit()."""
        if self._unit_start_time is None:
            return 0.0
        return time.monotonic() - self._unit_start_time

    def print_status(self, message: str) -> None:
        """Print a dim status line (for 'Building scene X/Y: id')."""
        self.console.print(f"  [dim]{message}[/dim]")

    @contextmanager
    def task(self, description: str) -> Generator[None, None, None]:
        """Show spinner with dual timer (unit/total).

        The spinner remains visible while the context is active. Status lines
        printed via print_status() appear above the spinner.

        Args:
            description: Task description shown next to spinner
        """
        if self._start_time is None:
            self._start_time = time.monotonic()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            UnitDualTimeColumn(self._get_unit_elapsed, self._get_total_elapsed),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(description, total=None)
            yield

    def success(self, message: str) -> None:
        """Display a success message with green checkmark."""
        self.console.print(f"[green]\u2713[/green] {message}")

    def warn(self, message: str) -> None:
        """Display a warning message in yellow."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def error(self, message: str) -> None:
        """Display an error message with red X."""
        self.console.print(f"[red]\u2717[/red] {message}")

    def info(self, message: str) -> None:
        """Display an info message with blue indicator."""
        self.console.print(f"[blue]\u2139[/blue] {message}")


@contextmanager
def maybe_task(progress: BuildProgress | None, description: str) -> Generator[None, None, None]:
    """Context manager that wraps task() if progress is available.

    This helper allows pipelines to optionally show progress while still
    supporting the case where progress is None.

    Args:
        progress: Optional BuildProgress instance
        description: Task description for spinner display
    """
    if progress:
        with progress.task(description):
            yield
    else:
        yield


__all__ = ["BuildProgress", "UnitDualTimeColumn", "maybe_task"]
