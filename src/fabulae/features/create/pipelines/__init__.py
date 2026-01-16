"""Format-specific generation pipelines for narrative creation.

This module contains the pipeline implementations for different narrative formats:
- prose: Novel, novella, and short-story formats with full structure
- outline: Outline-only mode for prose (without --full flag)
- micro_prose: Flash fiction with fragments
- poem: Poetry with stanzas

Each pipeline is responsible for end-to-end generation for its format, dispatched from
the main create service based on the project's format and options.
"""

from fabulae.features.create.pipelines.micro_prose import generate_micro_prose
from fabulae.features.create.pipelines.outline import generate_outline_only
from fabulae.features.create.pipelines.poem import generate_poem
from fabulae.features.create.pipelines.prose import generate_prose

__all__ = ["generate_prose", "generate_micro_prose", "generate_poem", "generate_outline_only"]
