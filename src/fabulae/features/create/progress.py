"""Rich progress display for create command with timing tracking."""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, ProgressColumn, SpinnerColumn, Task, TextColumn, TimeElapsedColumn
from rich.table import Table
from rich.text import Text

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class StepTiming:
    """Timing information for a generation step."""

    name: str
    duration_seconds: float


class TotalElapsedColumn(ProgressColumn):
    """Custom column that displays total elapsed time since start."""

    def __init__(self, get_start_time: Callable[[], float | None]) -> None:
        super().__init__()
        self._get_start_time = get_start_time

    def render(self, task: Task) -> Text:
        start_time = self._get_start_time()
        if start_time is None:
            return Text("0:00")
        elapsed = time.monotonic() - start_time
        return Text(self._format_duration(elapsed))

    @staticmethod
    def _format_duration(seconds: float) -> str:
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

    def _get_start_time(self) -> float | None:
        """Get the start time for total elapsed calculation."""
        return self._start_time

    @contextmanager
    def stage(self, description: str) -> Generator[None, None, None]:
        """Context manager for a generation stage with dual timer display."""
        if self._start_time is None:
            self._start_time = time.monotonic()

        self._current_step_start = time.monotonic()
        step_name = description.rstrip(".").strip()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[dim]step:[/dim]"),
            TimeElapsedColumn(),
            TextColumn("[dim]total:[/dim]"),
            TotalElapsedColumn(self._get_start_time),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(description, total=None)
            yield

        # Record step duration
        step_duration = time.monotonic() - self._current_step_start
        self._step_timings.append(StepTiming(name=step_name, duration_seconds=step_duration))

    def _format_total_elapsed(self) -> str:
        """Format total elapsed time."""
        if self._start_time is None:
            return "0:00"
        elapsed = time.monotonic() - self._start_time
        return self._format_duration(elapsed)

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
        """Display a success message with step duration."""
        duration_str = ""
        if self._step_timings:
            last_step = self._step_timings[-1]
            duration_str = f" ({self._format_duration_human(last_step.duration_seconds)})"
        self.console.print(f"[green]✓[/green] {message}{duration_str}")

    def warn(self, message: str) -> None:
        """Display a warning message in yellow."""
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def error(self, message: str) -> None:
        """Display an error message with red X."""
        self.console.print(f"[red]✗[/red] {message}")

    def info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")

    def print_summary(self) -> None:
        """Print timing summary table."""
        if not self._step_timings:
            return

        self.console.print()
        self.console.print("[bold]Generation Summary:[/bold]")

        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column("Step", style="dim")
        table.add_column("Duration", justify="right")

        total_seconds = 0.0
        for step in self._step_timings:
            duration_str = self._format_duration_human(step.duration_seconds)
            table.add_row(f"  {step.name}:", duration_str)
            total_seconds += step.duration_seconds

        # Add separator and total
        table.add_row("  " + "─" * 20, "─" * 8)
        table.add_row("  Total:", self._format_duration_human(total_seconds))

        self.console.print(table)


__all__ = ["CreateProgress", "StepTiming"]
