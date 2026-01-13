"""Generation state container for graceful shutdown.

This module provides a dataclass to track in-progress generation state,
enabling partial results to be saved when the program is interrupted.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from fabulae.features.create.schemas import StyleOutput
    from fabulae.models import Chapter, Character, Fragment, Scene, Stanza, WorldFact


@dataclass
class GenerationState:
    """Holds in-progress generation state for graceful shutdown.

    This dataclass accumulates generated content as the pipeline progresses,
    enabling partial results to be saved if generation is interrupted.
    """

    idea: str = ""
    format_name: str = ""
    premise: str | None = None
    style: StyleOutput | None = None
    characters: list[Character] = field(default_factory=list)
    locations: list[WorldFact] = field(default_factory=list)
    world_facts: list[WorldFact] = field(default_factory=list)
    chapters: list[Chapter] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    fragments: list[Fragment] = field(default_factory=list)
    stanzas: list[Stanza] = field(default_factory=list)
    current_stage: str = "initializing"

    def write_partial(self, output_dir: Path) -> Path:
        """Write current state to partial output directory.

        Args:
            output_dir: Base directory for output files

        Returns:
            Path to the partial output directory
        """
        partial_dir = output_dir / ".fabulae-create" / "partial"
        partial_dir.mkdir(parents=True, exist_ok=True)

        # Write state.yml with current progress
        state_file = partial_dir / "state.yml"
        state_data = {
            "idea": self.idea,
            "format": self.format_name,
            "current_stage": self.current_stage,
            "progress": {
                "premise": self.premise is not None,
                "style": self.style is not None,
                "characters": len(self.characters),
                "locations": len(self.locations),
                "world_facts": len(self.world_facts),
                "chapters": len(self.chapters),
                "scenes": len(self.scenes),
                "fragments": len(self.fragments),
                "stanzas": len(self.stanzas),
            },
        }
        state_file.write_text(yaml.safe_dump(state_data, default_flow_style=False))

        # Write entities if they exist
        if self.premise:
            (partial_dir / "premise.yml").write_text(
                yaml.safe_dump({"premise": self.premise}, default_flow_style=False)
            )

        if self.style:
            (partial_dir / "style.yml").write_text(
                yaml.safe_dump(self.style.model_dump(exclude_none=True), default_flow_style=False)
            )

        if self.characters:
            chars_data = [c.model_dump(exclude_none=True) for c in self.characters]
            (partial_dir / "characters.yml").write_text(yaml.safe_dump(chars_data, default_flow_style=False))

        if self.locations:
            locs_data = [loc.model_dump(exclude_none=True) for loc in self.locations]
            (partial_dir / "locations.yml").write_text(yaml.safe_dump(locs_data, default_flow_style=False))

        if self.world_facts:
            facts_data = [f.model_dump(exclude_none=True) for f in self.world_facts]
            (partial_dir / "world_facts.yml").write_text(yaml.safe_dump(facts_data, default_flow_style=False))

        if self.chapters:
            chapters_data = [c.model_dump(exclude_none=True) for c in self.chapters]
            (partial_dir / "chapters.yml").write_text(yaml.safe_dump(chapters_data, default_flow_style=False))

        if self.scenes:
            scenes_data = [s.model_dump(exclude_none=True) for s in self.scenes]
            (partial_dir / "scenes.yml").write_text(yaml.safe_dump(scenes_data, default_flow_style=False))

        if self.fragments:
            fragments_data = [f.model_dump(exclude_none=True) for f in self.fragments]
            (partial_dir / "fragments.yml").write_text(yaml.safe_dump(fragments_data, default_flow_style=False))

        if self.stanzas:
            stanzas_data = [s.model_dump(exclude_none=True) for s in self.stanzas]
            (partial_dir / "stanzas.yml").write_text(yaml.safe_dump(stanzas_data, default_flow_style=False))

        return partial_dir


__all__ = ["GenerationState"]
