"""Tests for story shape loader."""

from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from fabulae.features.create.shapes.loader import (
    ShapeNotFoundError,
    get_shape_ids,
    load_all_shapes,
    load_shape,
    load_shape_from_file,
)
from fabulae.models import StoryShape


class TestGetShapeIds:
    """Tests for get_shape_ids()."""

    def test_returns_list_of_ids(self) -> None:
        """Test that get_shape_ids() returns a list of shape IDs."""
        shape_ids = get_shape_ids()
        assert isinstance(shape_ids, list)
        assert len(shape_ids) > 0
        assert all(isinstance(shape_id, str) for shape_id in shape_ids)

    def test_includes_known_shapes(self) -> None:
        """Test that get_shape_ids() includes known built-in shapes."""
        shape_ids = get_shape_ids()
        # Based on the task description, we should have 10 shapes
        assert "betrayal-arc" in shape_ids
        assert "heros-journey" in shape_ids
        assert "coming-of-age" in shape_ids
        assert "mystery-reveal" in shape_ids
        assert "romance-arc" in shape_ids
        assert "fall-redemption" in shape_ids
        assert "fish-out-of-water" in shape_ids
        assert "revenge-quest" in shape_ids
        assert "forbidden-knowledge" in shape_ids
        assert "transformation" in shape_ids

    def test_returns_sorted_list(self) -> None:
        """Test that get_shape_ids() returns IDs in sorted order."""
        shape_ids = get_shape_ids()
        assert shape_ids == sorted(shape_ids)

    def test_returns_exactly_ten_shapes(self) -> None:
        """Test that there are exactly 10 built-in shapes."""
        shape_ids = get_shape_ids()
        assert len(shape_ids) == 10


class TestLoadShape:
    """Tests for load_shape()."""

    def test_load_betrayal_arc(self) -> None:
        """Test loading the betrayal-arc shape."""
        shape = load_shape("betrayal-arc")
        assert isinstance(shape, StoryShape)
        assert shape.id == "betrayal-arc"
        assert shape.name == "Betrayal Arc"
        assert len(shape.description) > 0
        # Betrayal arc should have character slots
        assert len(shape.character_slots) > 0
        # Should have protagonist and betrayer
        slot_names = [slot.slot for slot in shape.character_slots]
        assert "protagonist" in slot_names
        assert "betrayer" in slot_names

    def test_load_heros_journey(self) -> None:
        """Test loading the heros-journey shape."""
        shape = load_shape("heros-journey")
        assert isinstance(shape, StoryShape)
        assert shape.id == "heros-journey"
        assert shape.name
        assert len(shape.required_beats) > 0

    def test_load_nonexistent_shape_raises_error(self) -> None:
        """Test that loading a non-existent shape raises ShapeNotFoundError."""
        with pytest.raises(ShapeNotFoundError) as exc_info:
            load_shape("nonexistent-shape")

        error_message = str(exc_info.value)
        assert "nonexistent-shape" in error_message
        assert "Available shapes:" in error_message

    def test_all_shapes_have_required_fields(self) -> None:
        """Test that all built-in shapes have required fields."""
        shape_ids = get_shape_ids()
        for shape_id in shape_ids:
            shape = load_shape(shape_id)
            assert shape.id == shape_id
            assert shape.name
            assert shape.description


class TestLoadShapeFromFile:
    """Tests for load_shape_from_file()."""

    def test_load_from_custom_file(self, tmp_path: Path) -> None:
        """Test loading a shape from a custom YAML file."""
        custom_shape_yaml = """
id: test-shape
name: "Test Shape"
description: "A test shape for unit testing"
character_slots:
  - slot: protagonist
    needs: "The main character"
    optional: false
setting_slots:
  - slot: main-location
    needs: "The primary location"
    optional: false
required_beats:
  - type: opening
    description: "The story begins"
    position: early
    flexibility: flexible
variation_points:
  - type: twist
    description: "A potential plot twist"
    probability: 0.5
    position: middle
themes:
  - courage
  - friendship
motifs:
  - journey
  - transformation
tone: "hopeful"
"""
        temp_file = tmp_path / "test-shape.yml"
        temp_file.write_text(custom_shape_yaml)

        shape = load_shape_from_file(temp_file)
        assert isinstance(shape, StoryShape)
        assert shape.id == "test-shape"
        assert shape.name == "Test Shape"
        assert len(shape.character_slots) == 1
        assert len(shape.setting_slots) == 1
        assert len(shape.required_beats) == 1
        assert len(shape.variation_points) == 1
        assert "courage" in shape.themes
        assert "journey" in shape.motifs
        assert shape.tone == "hopeful"

    def test_load_from_nonexistent_file_raises_error(self, tmp_path: Path) -> None:
        """Test that loading from a non-existent file raises FileNotFoundError."""
        nonexistent_path = tmp_path / "nonexistent-shape-file.yml"
        with pytest.raises(FileNotFoundError):
            load_shape_from_file(nonexistent_path)

    def test_load_invalid_yaml_raises_error(self, tmp_path: Path) -> None:
        """Test that loading invalid YAML raises an error."""
        invalid_yaml = """
id: invalid-shape
name: "Invalid Shape"
this is not valid yaml: {{{
"""
        temp_file = tmp_path / "invalid.yml"
        temp_file.write_text(invalid_yaml)

        with pytest.raises(yaml.YAMLError):
            load_shape_from_file(temp_file)

    def test_load_missing_required_field_raises_error(self, tmp_path: Path) -> None:
        """Test that loading shape with missing required fields raises ValidationError."""
        incomplete_yaml = """
id: incomplete-shape
# Missing 'name' and 'description' required fields
character_slots: []
"""
        temp_file = tmp_path / "incomplete.yml"
        temp_file.write_text(incomplete_yaml)

        with pytest.raises(ValidationError):
            load_shape_from_file(temp_file)


class TestLoadAllShapes:
    """Tests for load_all_shapes()."""

    def test_loads_all_shapes(self) -> None:
        """Test that load_all_shapes() returns all 10 shapes."""
        shapes = load_all_shapes()
        assert isinstance(shapes, list)
        assert len(shapes) == 10
        assert all(isinstance(shape, StoryShape) for shape in shapes)

    def test_all_shapes_are_valid(self) -> None:
        """Test that all loaded shapes are valid StoryShape instances."""
        shapes = load_all_shapes()
        for shape in shapes:
            assert shape.id
            assert shape.name
            assert shape.description

    def test_shape_ids_match(self) -> None:
        """Test that loaded shapes have IDs matching get_shape_ids()."""
        shapes = load_all_shapes()
        shape_ids = get_shape_ids()

        loaded_ids = {shape.id for shape in shapes}
        expected_ids = set(shape_ids)

        assert loaded_ids == expected_ids

    def test_no_duplicate_ids(self) -> None:
        """Test that there are no duplicate shape IDs."""
        shapes = load_all_shapes()
        shape_ids = [shape.id for shape in shapes]
        assert len(shape_ids) == len(set(shape_ids))
