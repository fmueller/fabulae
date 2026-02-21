"""Project loading helpers for the TUI."""

from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError

from fabulae.models import (
    CharactersFile,
    Plot,
    Project,
    ProjectConfig,
    ProjectPaths,
    Style,
    World,
    load_yaml_file,
)


def load_project_relaxed(project_path: Path) -> Project:
    """Load a project without enforcing full validation.

    This is used by the TUI to open incomplete or partially-invalid projects
    without crashing.
    """
    config_path = project_path / "fabulae.yml"
    config_data = load_yaml_file(config_path) if config_path.exists() else {"version": "0.1.0"}
    try:
        config = ProjectConfig.model_validate(config_data)
    except ValidationError:
        config = ProjectConfig(version="0.1.0")

    paths = config.paths or ProjectPaths()

    plot_path = project_path / paths.plot
    plot = _safe_load_plot(plot_path)

    characters_path = project_path / paths.characters
    if characters_path.exists():
        try:
            characters_data = CharactersFile.model_validate(load_yaml_file(characters_path))
            characters = characters_data.characters
        except ValidationError:
            characters = []
    else:
        characters = []

    world_path = project_path / paths.world
    if world_path.exists():
        try:
            world = World.model_validate(load_yaml_file(world_path))
        except ValidationError:
            world = None
    else:
        world = None

    style_path = project_path / paths.style
    if style_path.exists():
        try:
            style = Style.model_validate(load_yaml_file(style_path))
        except ValidationError:
            style = None
    else:
        style = None

    return Project(
        config=config,
        plot=plot,
        characters=characters,
        world=world,
        style=style,
    )


def _safe_load_plot(plot_path: Path) -> Plot:
    if not plot_path.exists():
        return Plot(format="novel", premise="Untitled premise")

    try:
        return Plot.model_validate(load_yaml_file(plot_path))
    except ValidationError:
        return Plot(format="novel", premise="Untitled premise")
