"""Shared entity generation functions for CRUD and create commands.

This module provides a unified entity generation layer that is used by both:
- CRUD `suggest` commands (e.g., `fabulae character suggest`)
- `fabulae create` command's entity generation phases

The shared approach ensures:
- Consistent output quality across features
- Single source of truth for entity generation prompts
- Reduced code duplication
- Easier maintenance
"""

from fabulae.features.entities.generation.beat import suggest_beat
from fabulae.features.entities.generation.character import suggest_character
from fabulae.features.entities.generation.fragment import suggest_fragment
from fabulae.features.entities.generation.scene import suggest_scene
from fabulae.features.entities.generation.stanza import suggest_stanza
from fabulae.features.entities.generation.world_fact import suggest_world_fact

__all__ = [
    "suggest_character",
    "suggest_world_fact",
    "suggest_scene",
    "suggest_beat",
    "suggest_fragment",
    "suggest_stanza",
]
