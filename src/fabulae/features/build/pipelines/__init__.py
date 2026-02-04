"""Build pipelines for generating narrative output."""

from fabulae.features.build.pipelines.batch import (
    build_chaptered_batch,
    build_micro_prose_batch,
    build_poem_batch,
    build_scenes_batch,
)
from fabulae.features.build.pipelines.context import (
    BuildFragmentContext,
    BuildSceneContext,
    BuildStanzaContext,
)
from fabulae.features.build.pipelines.sequential import (
    build_chaptered_sequential,
    build_micro_prose_sequential,
    build_poem_sequential,
    build_scenes_sequential,
)

__all__ = [
    "BuildFragmentContext",
    "BuildSceneContext",
    "BuildStanzaContext",
    "build_chaptered_batch",
    "build_chaptered_sequential",
    "build_micro_prose_batch",
    "build_micro_prose_sequential",
    "build_poem_batch",
    "build_poem_sequential",
    "build_scenes_batch",
    "build_scenes_sequential",
]
