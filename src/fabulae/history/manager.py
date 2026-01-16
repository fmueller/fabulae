"""History manager for tracking project actions."""

from __future__ import annotations

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fabulae.history.models import ActionType, HistoryEntry

if TYPE_CHECKING:
    pass

FABULAE_DIR = ".fabulae"
HISTORY_DIR = "history"
CACHE_DIR = "cache"
TEMP_DIR = "temp"


class HistoryManager:
    """Manages project history stored in the .fabulae folder."""

    def __init__(self, project_path: Path, enabled: bool = True) -> None:
        """Initialize the history manager.

        Args:
            project_path: Path to the project directory.
            enabled: Whether history tracking is enabled.
        """
        self.project_path = project_path
        self.enabled = enabled
        self.fabulae_dir = project_path / FABULAE_DIR
        self.history_dir = self.fabulae_dir / HISTORY_DIR

    def ensure_dirs(self) -> None:
        """Create .fabulae directory structure if needed."""
        if not self.enabled:
            return
        self.history_dir.mkdir(parents=True, exist_ok=True)
        (self.fabulae_dir / CACHE_DIR).mkdir(exist_ok=True)
        (self.fabulae_dir / TEMP_DIR).mkdir(exist_ok=True)

    def get_temp_dir(self) -> Path:
        """Get the temp directory, creating if needed.

        Returns:
            Path to the temp directory.
        """
        self.ensure_dirs()
        return self.fabulae_dir / TEMP_DIR

    def clean_temp(self) -> int:
        """Remove all temp files.

        Returns:
            Count of deleted files.
        """
        temp_dir = self.fabulae_dir / TEMP_DIR
        if not temp_dir.exists():
            return 0

        count = 0
        for file in temp_dir.iterdir():
            if file.is_file():
                file.unlink()
                count += 1
        return count

    @contextmanager
    def track_action(
        self,
        action: ActionType,
        command: str,
        parameters: dict[str, Any],
    ) -> Iterator[None]:
        """Context manager to track an action.

        Args:
            action: Type of action being performed.
            command: Full command line string.
            parameters: Dictionary of command parameters.

        Yields:
            None
        """
        if not self.enabled:
            yield
            return

        self.ensure_dirs()
        entry_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        result = "success"
        error_message: str | None = None
        changes: list[str] = []

        try:
            yield
        except Exception as e:
            result = "failed"
            error_message = str(e)
            raise
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            entry = HistoryEntry(
                id=entry_id,
                timestamp=start_time,
                action=action,
                command=command,
                parameters=parameters,
                result=result,
                duration_seconds=duration,
                error_message=error_message,
                changes=changes if changes else None,
            )
            self._save_entry(entry)

    def _save_entry(self, entry: HistoryEntry) -> None:
        """Save a history entry to disk.

        Args:
            entry: The history entry to save.
        """
        # Include microseconds and entry ID for uniqueness when multiple entries are created quickly
        filename = f"{entry.timestamp.strftime('%Y-%m-%d_%H%M%S_%f')}_{entry.id}_{entry.action.value}.json"
        filepath = self.history_dir / filename
        filepath.write_text(entry.model_dump_json(indent=2))

    def get_history(self, limit: int | None = None) -> list[HistoryEntry]:
        """Load history entries from disk.

        Args:
            limit: Maximum number of entries to return (None for all).

        Returns:
            List of history entries, most recent first.
        """
        if not self.history_dir.exists():
            return []

        entries: list[HistoryEntry] = []
        for file in sorted(self.history_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(file.read_text())
                entries.append(HistoryEntry.model_validate(data))
                if limit and len(entries) >= limit:
                    break
            except Exception:
                continue  # Skip corrupted entries

        return entries

    def clear_history(self) -> int:
        """Clear all history entries.

        Returns:
            Count of deleted entries.
        """
        if not self.history_dir.exists():
            return 0

        count = 0
        for file in self.history_dir.glob("*.json"):
            file.unlink()
            count += 1
        return count
