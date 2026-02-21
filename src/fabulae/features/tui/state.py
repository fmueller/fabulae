"""Shared TUI state container."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from fabulae.models import Project


@dataclass
class TuiProjectState:
    project_path: Path
    project: Project | None = None
    create_output_dir: Path | None = None
    load_error: str | None = None
