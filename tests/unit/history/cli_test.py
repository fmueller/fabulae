"""Tests for the history CLI command."""

from __future__ import annotations

import json
import re
from pathlib import Path

from typer.testing import CliRunner

from fabulae.history.manager import HistoryManager
from fabulae.history.models import ActionType
from fabulae.main import app

runner = CliRunner()

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;]*m")


class TestHistoryCommand:
    """Tests for the fabulae history command."""

    def test_history_shows_no_entries_message(self, tmp_path: Path) -> None:
        """history command should show message when no history exists."""
        result = runner.invoke(app, ["history", str(tmp_path)])
        assert result.exit_code == 0
        assert "No history found" in result.output

    def test_history_shows_entries(self, tmp_path: Path) -> None:
        """history command should display history entries."""
        # Create some history
        manager = HistoryManager(tmp_path)
        with manager.track_action(
            action=ActionType.CREATE,
            command="fabulae create ./test",
            parameters={"format": "novel"},
        ):
            pass

        result = runner.invoke(app, ["history", str(tmp_path)])
        assert result.exit_code == 0
        assert "create" in result.output

    def test_history_limit_option(self, tmp_path: Path) -> None:
        """history command should respect --limit option."""
        manager = HistoryManager(tmp_path)
        for i in range(5):
            with manager.track_action(
                action=ActionType.CREATE,
                command=f"command-{i}",
                parameters={},
            ):
                pass

        result = runner.invoke(app, ["history", str(tmp_path), "--limit", "2"])
        assert result.exit_code == 0
        assert "Showing 2 of 5" in result.output

    def test_history_clear_option(self, tmp_path: Path) -> None:
        """history command should clear history with --clear option."""
        manager = HistoryManager(tmp_path)
        with manager.track_action(
            action=ActionType.CREATE,
            command="test",
            parameters={},
        ):
            pass

        assert len(manager.get_history()) == 1

        result = runner.invoke(app, ["history", str(tmp_path), "--clear"])
        assert result.exit_code == 0
        assert "Cleared 1 history entries" in result.output
        assert len(manager.get_history()) == 0

    def test_history_json_output(self, tmp_path: Path) -> None:
        """history command should output JSON with --json option."""
        manager = HistoryManager(tmp_path)
        with manager.track_action(
            action=ActionType.BUILD,
            command="fabulae build ./test",
            parameters={"seed": 42},
        ):
            pass

        result = runner.invoke(app, ["history", str(tmp_path), "--json"])
        assert result.exit_code == 0

        # Parse output as JSON
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["action"] == "build"
        assert data[0]["parameters"]["seed"] == 42

    def test_history_shows_failed_entries_with_error(self, tmp_path: Path) -> None:
        """history command should display error message for failed entries."""
        manager = HistoryManager(tmp_path)
        try:
            with manager.track_action(ActionType.BUILD, "test", {}):
                raise ValueError("Something went wrong")
        except ValueError:
            pass

        result = runner.invoke(app, ["history", str(tmp_path)])
        assert result.exit_code == 0
        clean_output = ANSI_ESCAPE_PATTERN.sub("", result.output)
        assert "Something went wrong" in clean_output


class TestNoHistoryFlag:
    """Tests for the global --no-history flag."""

    def test_no_history_flag_in_help(self) -> None:
        """--no-history flag should appear in help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        clean_output = ANSI_ESCAPE_PATTERN.sub("", result.output)
        assert "--no-history" in clean_output

    def test_no_history_flag_is_global(self) -> None:
        """--no-history flag should be available at the app level."""
        # This should not error - flag is recognized
        result = runner.invoke(app, ["--no-history", "version"])
        assert result.exit_code == 0
