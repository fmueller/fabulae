"""Create-from-idea feature slice."""

from fabulae.features.create.cli import register_create_command
from fabulae.features.create.service import (
    CreateProjectError,
    ErrorMode,
    SceneContext,
    StageResult,
    generate_project_from_idea,
    generate_project_from_idea_sync,
    run_stage,
)

__all__ = [
    "CreateProjectError",
    "ErrorMode",
    "SceneContext",
    "StageResult",
    "generate_project_from_idea",
    "generate_project_from_idea_sync",
    "register_create_command",
    "run_stage",
]
