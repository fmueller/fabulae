"""Loader for story shape files."""

from __future__ import annotations

from pathlib import Path

import yaml

from fabulae.models import StoryShape


class ShapeNotFoundError(Exception):
    """Raised when a requested shape is not found."""

    pass


def _get_shapes_directory() -> Path:
    """Get the directory containing built-in story shapes."""
    # Story shapes are in src/fabulae/data/story_shapes/
    # This module is in src/fabulae/features/create/shapes/
    # So we need to go up to src/fabulae/ and then to data/story_shapes/
    module_path = Path(__file__).parent  # .../features/create/shapes/
    fabulae_root = module_path.parent.parent.parent  # .../fabulae/
    shapes_dir = fabulae_root / "data" / "story_shapes"
    return shapes_dir


def get_shape_ids() -> list[str]:
    """
    Get a list of all available built-in shape IDs.

    Returns:
        List of shape IDs (e.g., ["betrayal-arc", "heros-journey", ...])
    """
    shapes_dir = _get_shapes_directory()
    if not shapes_dir.exists():
        return []

    shape_ids = []
    for shape_file in sorted(shapes_dir.glob("*.yml")):
        # Skip __init__.py or any non-YAML files
        if shape_file.name.startswith("__"):
            continue
        # Extract the ID from the filename (e.g., "betrayal-arc.yml" -> "betrayal-arc")
        shape_id = shape_file.stem
        shape_ids.append(shape_id)

    return shape_ids


def load_shape_from_file(path: Path) -> StoryShape:
    """
    Load a story shape from a custom YAML file.

    Args:
        path: Path to the YAML file containing the shape definition

    Returns:
        StoryShape instance

    Raises:
        FileNotFoundError: If the file does not exist
        yaml.YAMLError: If the YAML is invalid
        pydantic.ValidationError: If the shape data is invalid
    """
    if not path.exists():
        raise FileNotFoundError(f"Shape file not found: {path}")

    with open(path, encoding="utf-8") as f:
        shape_data = yaml.safe_load(f)

    return StoryShape.model_validate(shape_data)


def load_shape(shape_id: str) -> StoryShape:
    """
    Load a built-in story shape by ID.

    Args:
        shape_id: The shape ID (e.g., "betrayal-arc", "heros-journey")

    Returns:
        StoryShape instance

    Raises:
        ShapeNotFoundError: If the shape ID is not found
        yaml.YAMLError: If the YAML is invalid
        pydantic.ValidationError: If the shape data is invalid
    """
    shapes_dir = _get_shapes_directory()
    shape_file = shapes_dir / f"{shape_id}.yml"

    if not shape_file.exists():
        available_shapes = get_shape_ids()
        raise ShapeNotFoundError(f"Shape '{shape_id}' not found. Available shapes: {', '.join(available_shapes)}")

    return load_shape_from_file(shape_file)


def load_all_shapes() -> list[StoryShape]:
    """
    Load all available built-in story shapes.

    Returns:
        List of StoryShape instances

    Raises:
        yaml.YAMLError: If any YAML is invalid
        pydantic.ValidationError: If any shape data is invalid
    """
    shape_ids = get_shape_ids()
    shapes = []

    for shape_id in shape_ids:
        shape = load_shape(shape_id)
        shapes.append(shape)

    return shapes
