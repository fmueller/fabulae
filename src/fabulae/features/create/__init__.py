"""Create-from-idea feature slice."""

from fabulae.features.create.cli import register_create_command
from fabulae.features.create.service import generate_project_from_idea

__all__ = ["generate_project_from_idea", "register_create_command"]
