"""CLI command for viewing and managing project history."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from fabulae.history.manager import HistoryManager


def register_history_command(app: typer.Typer) -> None:
    """Register the history command with the CLI app.

    Args:
        app: The Typer application to register the command with.
    """

    @app.command(name="history", help="View or manage project history.")
    def history_command(
        project_dir: Annotated[
            Path,
            typer.Argument(help="Path to the Fabulae project directory."),
        ] = Path("."),
        limit: Annotated[
            int,
            typer.Option("--limit", "-n", help="Maximum number of entries to display."),
        ] = 10,
        clear: Annotated[
            bool,
            typer.Option("--clear", help="Clear all history entries."),
        ] = False,
        json_output: Annotated[
            bool,
            typer.Option("--json", help="Output history as JSON."),
        ] = False,
    ) -> None:
        """View or manage project history.

        Shows recent actions performed on the project, or clears the history.
        """
        manager = HistoryManager(project_dir)

        if clear:
            count = manager.clear_history()
            typer.echo(f"Cleared {count} history entries")
            return

        entries = manager.get_history(limit=limit)

        if json_output:
            output = [e.model_dump(mode="json") for e in entries]
            typer.echo(json.dumps(output, default=str, indent=2))
            return

        if not entries:
            typer.echo(f"No history found for project: {project_dir}")
            return

        # Pretty print history
        console = Console()
        console.print(f"\n[bold]Project History: {project_dir}[/bold]")
        console.print("─" * 60)

        for entry in entries:
            icon = "✓" if entry.result == "success" else "✗"
            color = "green" if entry.result == "success" else "red"
            timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M")
            console.print(f"[{color}]{icon}[/{color}] {timestamp} - [bold]{entry.action.value}[/bold]")
            if entry.duration_seconds is not None:
                console.print(f"    Duration: {entry.duration_seconds:.1f}s")
            if entry.error_message:
                console.print(f"    [red]Error: {entry.error_message}[/red]")
            if entry.parameters:
                # Show key parameters
                for key, value in list(entry.parameters.items())[:3]:
                    if value is not None and key not in ("idea",):  # Skip large text fields
                        console.print(f"    {key}: {value}")

        console.print("─" * 60)
        total = len(manager.get_history())
        console.print(f"Showing {len(entries)} of {total} entries")


__all__ = ["register_history_command"]
