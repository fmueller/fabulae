"""Entity CRUD commands for Fabulae projects."""

from fabulae.features.entities.beat import beat_app
from fabulae.features.entities.chapter import chapter_app
from fabulae.features.entities.character import character_app
from fabulae.features.entities.fragment import fragment_app
from fabulae.features.entities.scene import scene_app
from fabulae.features.entities.stanza import stanza_app
from fabulae.features.entities.world import world_app

__all__ = [
    "beat_app",
    "chapter_app",
    "character_app",
    "fragment_app",
    "scene_app",
    "stanza_app",
    "world_app",
]
