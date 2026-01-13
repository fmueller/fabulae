"""Rich progress display for create command with timing tracking."""

from __future__ import annotations

import time
from collections.abc import Callable, Generator
from contextlib import contextmanager
from dataclasses import dataclass

from rich.console import Console
from rich.progress import Progress, ProgressColumn, SpinnerColumn, Task, TextColumn
from rich.text import Text


@dataclass
class StepTiming:
    """Timing information for a generation step."""

    name: str
    duration_seconds: float


class DualTimeColumn(ProgressColumn):
    """Custom column showing step time / total time."""

    def __init__(self, get_total_elapsed: Callable[[], float]) -> None:
        super().__init__()
        self._get_total_elapsed = get_total_elapsed

    def render(self, task: Task) -> Text:
        """Render the dual time display."""
        step_elapsed = task.elapsed or 0.0
        total_elapsed = self._get_total_elapsed()

        step_str = self._format_time(step_elapsed)
        total_str = self._format_time(total_elapsed)

        return Text(f"{step_str} / {total_str}", style="progress.elapsed")

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as H:MM:SS or M:SS."""
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"


class CreateProgress:
    """Rich progress display for create command with timing tracking."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._start_time: float | None = None
        self._step_timings: list[StepTiming] = []
        self._current_step_start: float | None = None

    def start(self) -> None:
        """Mark the start of generation."""
        self._start_time = time.monotonic()

    def _get_total_elapsed(self) -> float:
        """Get total elapsed time since start."""
        if self._start_time is None:
            return 0.0
        return time.monotonic() - self._start_time

    @contextmanager
    def stage(self, description: str) -> Generator[None, None, None]:
        """Context manager for a generation stage with dual timer display (step / total)."""
        if self._start_time is None:
            self._start_time = time.monotonic()

        self._current_step_start = time.monotonic()
        step_name = description.rstrip(".").strip()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            DualTimeColumn(self._get_total_elapsed),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(description, total=None)
            yield

        # Record step duration
        step_duration = time.monotonic() - self._current_step_start
        self._step_timings.append(StepTiming(name=step_name, duration_seconds=step_duration))

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds as H:MM:SS or M:SS."""
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _format_duration_human(seconds: float) -> str:
        """Format seconds as human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes, secs = divmod(int(seconds), 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes}m {secs}s"

    def success(self, message: str) -> None:
        """Display a success message."""
        self.console.print(f"[green]✓[/green] {message}")

    def warn(self, message: str) -> None:
        """Display a warning message in yellow."""
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def error(self, message: str) -> None:
        """Display an error message with red X."""
        self.console.print(f"[red]✗[/red] {message}")

    def info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")


@contextmanager
def maybe_stage(progress: CreateProgress | None, description: str) -> Generator[None, None, None]:
    """Context manager that wraps stage() if progress is available.

    This helper allows batch pipelines to use stage() for timing tracking
    while still supporting the optional progress parameter.

    Args:
        progress: Optional CreateProgress instance
        description: Stage description for spinner display
    """
    if progress:
        with progress.stage(description):
            yield
    else:
        yield


__all__ = ["CreateProgress", "StepTiming", "maybe_stage"]
