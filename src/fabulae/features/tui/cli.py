"""CLI entry points for the Textual TUI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

import typer

from fabulae.features.tui.app import FabulaeApp


def launch_tui(project_path: Path, *, start_create: bool = False) -> None:
    """Launch the Textual TUI for a project path."""
    app = FabulaeApp(project_path, start_create=start_create)
    app.run()


def tui_disabled() -> bool:
    """Return True when the TUI should not launch (e.g., tests)."""
    return os.getenv("FABULAE_DISABLE_TUI") == "1"


def register_tui_command(app: typer.Typer) -> None:
    """Register the explicit TUI command."""

    @app.command(name="tui", help="Launch the interactive Fabulae TUI.")
    def tui_command(
        path: Annotated[Path, typer.Argument(help="Project directory.")] = Path("."),
        new: Annotated[bool, typer.Option("--new", help="Start with project creation.")] = False,
    ) -> None:
        """Launch the interactive TUI."""
        launch_tui(path, start_create=new)
