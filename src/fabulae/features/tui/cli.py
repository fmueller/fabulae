"""CLI entry point for the Fabulae TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer


def register_tui_command(app: typer.Typer) -> None:
    """Register the explicit `tui` command with the Typer app."""

    @app.command(name="tui", help="Launch the interactive TUI.")
    def tui_command(
        path: Annotated[
            Path,
            typer.Argument(help="Project directory."),
        ] = Path("."),
        new: Annotated[
            bool,
            typer.Option("--new", help="Start with project creation."),
        ] = False,
    ) -> None:
        """Launch the interactive TUI for project management."""
        from fabulae.features.tui.app import FabulaeApp

        has_project = (path / "fabulae.yml").exists()
        tui_app = FabulaeApp(path, start_create=new or not has_project)
        tui_app.run()


def launch_tui(path: Path | None = None, new: bool = False) -> None:
    """Launch the TUI application.

    Called from the main callback when no subcommand is provided.
    """
    from fabulae.features.tui.app import FabulaeApp

    project_path = path or Path.cwd()
    has_project = (project_path / "fabulae.yml").exists()
    tui_app = FabulaeApp(project_path, start_create=new or not has_project)
    tui_app.run()
