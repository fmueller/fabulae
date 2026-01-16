"""Tests for the history manager."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from fabulae.history.manager import FABULAE_DIR, HISTORY_DIR, HistoryManager
from fabulae.history.models import ActionType, HistoryEntry


class TestHistoryManager:
    """Tests for HistoryManager class."""

    def test_ensure_dirs_creates_fabulae_structure(self, tmp_path: Path) -> None:
        """ensure_dirs should create .fabulae directory structure."""
        manager = HistoryManager(tmp_path)
        manager.ensure_dirs()

        assert (tmp_path / FABULAE_DIR).exists()
        assert (tmp_path / FABULAE_DIR / HISTORY_DIR).exists()
        assert (tmp_path / FABULAE_DIR / "cache").exists()
        assert (tmp_path / FABULAE_DIR / "temp").exists()

    def test_ensure_dirs_disabled_does_nothing(self, tmp_path: Path) -> None:
        """ensure_dirs should not create directories when disabled."""
        manager = HistoryManager(tmp_path, enabled=False)
        manager.ensure_dirs()

        assert not (tmp_path / FABULAE_DIR).exists()

    def test_track_action_records_success(self, tmp_path: Path) -> None:
        """track_action should record successful actions."""
        manager = HistoryManager(tmp_path)

        with manager.track_action(
            action=ActionType.CREATE,
            command="fabulae create ./test",
            parameters={"format": "novel"},
        ):
            pass  # Simulate successful action

        entries = manager.get_history()
        assert len(entries) == 1
        assert entries[0].action == ActionType.CREATE
        assert entries[0].result == "success"
        assert entries[0].parameters == {"format": "novel"}
        assert entries[0].error_message is None

    def test_track_action_records_failure(self, tmp_path: Path) -> None:
        """track_action should record failed actions with error message."""
        manager = HistoryManager(tmp_path)

        with pytest.raises(ValueError, match="Test error"), manager.track_action(
            action=ActionType.CREATE,
            command="fabulae create ./test",
            parameters={},
        ):
            raise ValueError("Test error")

        entries = manager.get_history()
        assert len(entries) == 1
        assert entries[0].result == "failed"
        assert entries[0].error_message == "Test error"

    def test_track_action_disabled_does_not_record(self, tmp_path: Path) -> None:
        """track_action should not record when disabled."""
        manager = HistoryManager(tmp_path, enabled=False)

        with manager.track_action(
            action=ActionType.CREATE,
            command="fabulae create ./test",
            parameters={},
        ):
            pass

        # History directory should not exist
        assert not (tmp_path / FABULAE_DIR / HISTORY_DIR).exists()

    def test_get_history_returns_most_recent_first(self, tmp_path: Path) -> None:
        """get_history should return entries ordered by timestamp (most recent first)."""
        manager = HistoryManager(tmp_path)

        # Create multiple entries
        for i in range(3):
            with manager.track_action(
                action=ActionType.CREATE,
                command=f"command-{i}",
                parameters={"index": i},
            ):
                pass

        entries = manager.get_history()
        assert len(entries) == 3
        # Most recent (index 2) should be first
        assert entries[0].parameters["index"] == 2
        assert entries[2].parameters["index"] == 0

    def test_get_history_respects_limit(self, tmp_path: Path) -> None:
        """get_history should respect the limit parameter."""
        manager = HistoryManager(tmp_path)

        for i in range(5):
            with manager.track_action(
                action=ActionType.CREATE,
                command=f"command-{i}",
                parameters={},
            ):
                pass

        entries = manager.get_history(limit=2)
        assert len(entries) == 2

    def test_get_history_empty_returns_empty_list(self, tmp_path: Path) -> None:
        """get_history should return empty list when no history exists."""
        manager = HistoryManager(tmp_path)
        entries = manager.get_history()
        assert entries == []

    def test_clear_history_removes_all_entries(self, tmp_path: Path) -> None:
        """clear_history should remove all history entries."""
        manager = HistoryManager(tmp_path)

        for _ in range(3):
            with manager.track_action(
                action=ActionType.CREATE,
                command="test",
                parameters={},
            ):
                pass

        assert len(manager.get_history()) == 3

        count = manager.clear_history()
        assert count == 3
        assert len(manager.get_history()) == 0

    def test_clear_history_empty_returns_zero(self, tmp_path: Path) -> None:
        """clear_history should return 0 when no history exists."""
        manager = HistoryManager(tmp_path)
        count = manager.clear_history()
        assert count == 0

    def test_get_temp_dir_creates_directory(self, tmp_path: Path) -> None:
        """get_temp_dir should create and return the temp directory."""
        manager = HistoryManager(tmp_path)
        temp_dir = manager.get_temp_dir()

        assert temp_dir.exists()
        assert temp_dir == tmp_path / FABULAE_DIR / "temp"

    def test_clean_temp_removes_temp_files(self, tmp_path: Path) -> None:
        """clean_temp should remove all files in the temp directory."""
        manager = HistoryManager(tmp_path)
        temp_dir = manager.get_temp_dir()

        # Create some temp files
        (temp_dir / "file1.txt").write_text("test1")
        (temp_dir / "file2.txt").write_text("test2")

        count = manager.clean_temp()
        assert count == 2
        assert list(temp_dir.iterdir()) == []

    def test_clean_temp_empty_returns_zero(self, tmp_path: Path) -> None:
        """clean_temp should return 0 when temp directory is empty."""
        manager = HistoryManager(tmp_path)
        count = manager.clean_temp()
        assert count == 0

    def test_history_entry_serialization(self, tmp_path: Path) -> None:
        """History entries should be properly serialized to JSON."""
        manager = HistoryManager(tmp_path)

        with manager.track_action(
            action=ActionType.BUILD,
            command="fabulae build ./test",
            parameters={"output": "test.txt", "seed": 42},
        ):
            pass

        # Read the raw JSON file
        history_files = list((tmp_path / FABULAE_DIR / HISTORY_DIR).glob("*.json"))
        assert len(history_files) == 1

        data = json.loads(history_files[0].read_text())
        assert data["action"] == "build"
        assert data["command"] == "fabulae build ./test"
        assert data["parameters"]["output"] == "test.txt"
        assert data["result"] == "success"


class TestHistoryEntry:
    """Tests for HistoryEntry model."""

    def test_history_entry_validation(self) -> None:
        """HistoryEntry should validate and serialize correctly."""
        from datetime import datetime

        entry = HistoryEntry(
            id="abc12345",
            timestamp=datetime.now(),
            action=ActionType.CREATE,
            command="fabulae create ./test",
            parameters={"format": "novel"},
            result="success",
            duration_seconds=10.5,
        )

        # Test serialization
        data = entry.model_dump()
        assert data["id"] == "abc12345"
        assert data["action"] == "create"
        assert data["result"] == "success"
        assert data["duration_seconds"] == 10.5

    def test_history_entry_optional_fields(self) -> None:
        """HistoryEntry should allow optional fields to be None."""
        from datetime import datetime

        entry = HistoryEntry(
            id="abc12345",
            timestamp=datetime.now(),
            action=ActionType.CHECK,
            command="fabulae check ./test",
            parameters={},
            result="success",
        )

        assert entry.duration_seconds is None
        assert entry.error_message is None
        assert entry.changes is None
