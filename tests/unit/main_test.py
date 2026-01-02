"""Tests for the fabulae CLI."""

from typer.testing import CliRunner

from fabulae import __version__
from fabulae.main import app

runner = CliRunner()


def test_version_command_shows_version() -> None:
    """Version command outputs the current version."""
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert f"fabulae v{__version__}" in result.output


def test_help_flag_shows_help() -> None:
    """The --help flag displays usage information."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Fabulae" in result.output
    assert "version" in result.output


def test_short_help_flag_shows_help() -> None:
    """The -h flag displays usage information."""
    result = runner.invoke(app, ["-h"])
    assert result.exit_code == 0
    assert "Fabulae" in result.output
    assert "version" in result.output


def test_no_command_shows_help() -> None:
    """Running without a command shows help."""
    result = runner.invoke(app)
    assert result.exit_code == 0
    assert "Fabulae" in result.output
