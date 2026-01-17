"""Generation state container for graceful shutdown.

This module provides a state container that tracks in-progress generation
state for graceful shutdown handling. When the program is interrupted,
the state can be written to disk for debugging and potential resumption.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from fabulae.features.create.schemas import StyleOutput
    from fabulae.models import Character, Fragment, Scene, Stanza, WorldFact


@dataclass
class GenerationState:
    """Holds in-progress generation state for graceful shutdown.

    This class tracks all generated content during a create operation,
    allowing partial results to be saved when the program is interrupted.
    """

    idea: str = ""
    format_name: str = ""
    premise: str | None = None
    style: StyleOutput | None = None
    characters: list[Character] = field(default_factory=list)
    locations: list[WorldFact] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    chapters: list[dict[str, object]] = field(default_factory=list)
    fragments: list[Fragment] = field(default_factory=list)
    stanzas: list[Stanza] = field(default_factory=list)
    current_stage: str = "initializing"

    def write_partial(self, output_dir: Path) -> Path:
        """Write current state to partial output directory.

        Args:
            output_dir: The base output directory for the project.

        Returns:
            Path to the partial output directory.
        """
        partial_dir = output_dir / ".fabulae" / "create" / "partial"
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
                "scenes": len(self.scenes),
                "chapters": len(self.chapters),
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

        if self.scenes:
            scenes_data = [s.model_dump(exclude_none=True) for s in self.scenes]
            (partial_dir / "scenes.yml").write_text(yaml.safe_dump(scenes_data, default_flow_style=False))

        if self.chapters:
            (partial_dir / "chapters.yml").write_text(yaml.safe_dump(self.chapters, default_flow_style=False))

        if self.fragments:
            fragments_data = [f.model_dump(exclude_none=True) for f in self.fragments]
            (partial_dir / "fragments.yml").write_text(yaml.safe_dump(fragments_data, default_flow_style=False))

        if self.stanzas:
            stanzas_data = [s.model_dump(exclude_none=True) for s in self.stanzas]
            (partial_dir / "stanzas.yml").write_text(yaml.safe_dump(stanzas_data, default_flow_style=False))

        return partial_dir


__all__ = ["GenerationState"]
