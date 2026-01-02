"""Version command for the CLI."""

import typer

from fabulae import __version__


def version_command() -> None:
    """Display the current version of fabulae."""
    typer.echo(f"fabulae v{__version__}")


__all__ = ["version_command"]
