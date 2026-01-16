"""Data models for project history tracking."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Types of actions that can be tracked in project history."""

    CREATE = "create"
    BUILD = "build"
    CHECK = "check"
    VALIDATE = "validate"
    INIT = "init"
    CHARACTER_ADD = "character_add"
    CHARACTER_EDIT = "character_edit"
    CHARACTER_REMOVE = "character_remove"
    CHARACTER_SUGGEST = "character_suggest"
    SCENE_ADD = "scene_add"
    SCENE_EDIT = "scene_edit"
    SCENE_REMOVE = "scene_remove"
    WORLD_ADD = "world_add"
    WORLD_EDIT = "world_edit"
    WORLD_REMOVE = "world_remove"
    BEAT_ADD = "beat_add"
    BEAT_EDIT = "beat_edit"
    BEAT_REMOVE = "beat_remove"
    CHAPTER_ADD = "chapter_add"
    CHAPTER_EDIT = "chapter_edit"
    CHAPTER_REMOVE = "chapter_remove"


class HistoryEntry(BaseModel):
    """A single action recorded in project history."""

    id: str = Field(description="Unique identifier for this history entry (short UUID)")
    timestamp: datetime = Field(description="When the action was performed")
    action: ActionType = Field(description="Type of action performed")
    command: str = Field(description="Full command line that was executed")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    result: str = Field(description="Outcome: success, failed, or cancelled")
    duration_seconds: float | None = Field(default=None, description="How long the action took")
    error_message: str | None = Field(default=None, description="Error message if action failed")
    changes: list[str] | None = Field(default=None, description="List of files that were changed")
