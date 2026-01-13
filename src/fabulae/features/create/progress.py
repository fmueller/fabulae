"""Rich progress display for create command."""

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

if TYPE_CHECKING:
    from collections.abc import Generator


class CreateProgress:
    """Rich progress display for create command."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()

    @contextmanager
    def stage(self, description: str) -> Generator[None, None, None]:
        """Context manager for a generation stage with spinner."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(description, total=None)
            yield

    def success(self, message: str) -> None:
        """Display a success message with green checkmark."""
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


__all__ = ["CreateProgress"]
