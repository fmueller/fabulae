"""Tests for Transformation story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_transformation_yaml() -> dict[str, object]:
    """Load the transformation YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "transformation.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestTransformationYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the transformation YAML file exists."""
        shape_path = get_story_shapes_path() / "transformation.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_transformation_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestTransformationValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_transformation_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_transformation_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "transformation"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_transformation_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Transformation"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_transformation_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_transformation_yaml()
        shape = StoryShape.model_validate(data)

        # Serialize back to dict then to YAML string
        yaml_str = yaml.dump(
            shape.model_dump(exclude_none=True),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        # Parse the YAML string back
        restored_data = yaml.safe_load(yaml_str)
        restored_shape = StoryShape.model_validate(restored_data)

        # Verify key properties survived
        assert restored_shape.id == shape.id
        assert restored_shape.name == shape.name
        assert len(restored_shape.character_slots) == len(shape.character_slots)
        assert len(restored_shape.setting_slots) == len(shape.setting_slots)
        assert len(restored_shape.required_beats) == len(shape.required_beats)
        assert len(restored_shape.variation_points) == len(shape.variation_points)


class TestTransformationRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have transforming-protagonist and supporting characters"

    def test_has_transforming_protagonist_slot(self, shape: StoryShape) -> None:
        """Test that the transforming protagonist character slot exists."""
        protagonist_slots = [s for s in shape.character_slots if s.slot == "transforming-protagonist"]
        assert len(protagonist_slots) == 1, "Should have exactly one transforming-protagonist slot"
        assert protagonist_slots[0].optional is False, "Transforming protagonist should be required"

    def test_has_catalyst_figure_slot(self, shape: StoryShape) -> None:
        """Test that the catalyst figure character slot exists."""
        catalyst_slots = [s for s in shape.character_slots if s.slot == "catalyst-figure"]
        assert len(catalyst_slots) == 1, "Should have catalyst-figure slot"

    def test_has_guide_slot(self, shape: StoryShape) -> None:
        """Test that the guide character slot exists."""
        guide_slots = [s for s in shape.character_slots if s.slot == "guide"]
        assert len(guide_slots) == 1, "Should have guide slot"

    def test_has_anchor_figure_slot(self, shape: StoryShape) -> None:
        """Test that the anchor figure character slot exists."""
        anchor_slots = [s for s in shape.character_slots if s.slot == "anchor-figure"]
        assert len(anchor_slots) == 1, "Should have anchor-figure slot"

    def test_has_witness_slot(self, shape: StoryShape) -> None:
        """Test that the witness character slot exists."""
        witness_slots = [s for s in shape.character_slots if s.slot == "witness"]
        assert len(witness_slots) == 1, "Should have witness slot"

    def test_has_mirror_character_slot(self, shape: StoryShape) -> None:
        """Test that the mirror character slot exists."""
        mirror_slots = [s for s in shape.character_slots if s.slot == "mirror-character"]
        assert len(mirror_slots) == 1, "Should have mirror-character slot"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestTransformationRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 2, "Should have key locations"

    def test_has_origin_state_setting(self, shape: StoryShape) -> None:
        """Test that the origin-state setting exists."""
        origin_state = [s for s in shape.setting_slots if s.slot == "origin-state"]
        assert len(origin_state) == 1, "Should have origin-state"
        assert origin_state[0].optional is False, "Origin-state should be required"

    def test_has_liminal_space_setting(self, shape: StoryShape) -> None:
        """Test that the liminal-space setting exists."""
        liminal_space = [s for s in shape.setting_slots if s.slot == "liminal-space"]
        assert len(liminal_space) == 1, "Should have liminal-space"
        assert liminal_space[0].optional is False, "Liminal-space should be required"

    def test_has_crucible_setting(self, shape: StoryShape) -> None:
        """Test that the crucible setting exists."""
        crucible = [s for s in shape.setting_slots if s.slot == "crucible"]
        assert len(crucible) == 1, "Should have crucible"

    def test_has_emergence_ground_setting(self, shape: StoryShape) -> None:
        """Test that the emergence-ground setting exists."""
        emergence_ground = [s for s in shape.setting_slots if s.slot == "emergence-ground"]
        assert len(emergence_ground) == 1, "Should have emergence-ground"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestTransformationRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (5-10 expected)."""
        assert 5 <= len(shape.required_beats) <= 10, f"Expected 5-10 required beats, got {len(shape.required_beats)}"

    def test_has_stasis_beat(self, shape: StoryShape) -> None:
        """Test that the stasis beat exists."""
        stasis_beats = [b for b in shape.required_beats if b.type == "stasis"]
        assert len(stasis_beats) == 1, "Should have stasis"
        assert stasis_beats[0].position == "early"

    def test_has_catalyst_beat(self, shape: StoryShape) -> None:
        """Test that the catalyst beat exists."""
        catalyst_beats = [b for b in shape.required_beats if b.type == "catalyst"]
        assert len(catalyst_beats) == 1, "Should have catalyst"
        assert catalyst_beats[0].position == "early"
        assert catalyst_beats[0].flexibility == "fixed"

    def test_has_resistance_beat(self, shape: StoryShape) -> None:
        """Test that the resistance beat exists."""
        resistance_beats = [b for b in shape.required_beats if b.type == "resistance"]
        assert len(resistance_beats) == 1, "Should have resistance"
        assert resistance_beats[0].position == "middle"

    def test_has_struggle_beat(self, shape: StoryShape) -> None:
        """Test that the struggle beat exists."""
        struggle_beats = [b for b in shape.required_beats if b.type == "struggle"]
        assert len(struggle_beats) == 1, "Should have struggle"
        assert struggle_beats[0].position == "middle"

    def test_has_surrender_beat(self, shape: StoryShape) -> None:
        """Test that the surrender beat exists."""
        surrender_beats = [b for b in shape.required_beats if b.type == "surrender"]
        assert len(surrender_beats) == 1, "Should have surrender"
        assert surrender_beats[0].position == "late"
        assert surrender_beats[0].flexibility == "fixed"

    def test_has_emergence_beat(self, shape: StoryShape) -> None:
        """Test that the emergence beat exists."""
        emergence_beats = [b for b in shape.required_beats if b.type == "emergence"]
        assert len(emergence_beats) == 1, "Should have emergence"
        assert emergence_beats[0].position == "climax"


class TestTransformationBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "stasis" in early_types, "Stasis should be in early position"
        assert "catalyst" in early_types, "Catalyst should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 2, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "resistance" in middle_types, "Resistance should be in middle position"
        assert "struggle" in middle_types, "Struggle should be in middle position"

    def test_late_beats_for_surrender(self, shape: StoryShape) -> None:
        """Test that late beats exist for surrender."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 1, "Should have late beats"

        late_types = {b.type for b in late_beats}
        assert "surrender" in late_types, "Surrender should be in late position"

    def test_climax_beats_for_emergence(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "emergence" in climax_types, "Emergence should be in climax position"


class TestTransformationVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 3, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_physical_transformation_variation(self, shape: StoryShape) -> None:
        """Test that the physical-transformation variation exists."""
        physical_transformation = [vp for vp in shape.variation_points if vp.type == "physical-transformation"]
        assert len(physical_transformation) == 1, "Should have physical-transformation variation"

    def test_has_transformation_cost_variation(self, shape: StoryShape) -> None:
        """Test that the transformation-cost variation exists."""
        transformation_cost = [vp for vp in shape.variation_points if vp.type == "transformation-cost"]
        assert len(transformation_cost) == 1, "Should have transformation-cost variation"

    def test_has_return_to_origin_variation(self, shape: StoryShape) -> None:
        """Test that the return-to-origin variation exists."""
        return_to_origin = [vp for vp in shape.variation_points if vp.type == "return-to-origin"]
        assert len(return_to_origin) == 1, "Should have return-to-origin variation"

    def test_has_incomplete_transformation_variation(self, shape: StoryShape) -> None:
        """Test that the incomplete-transformation variation exists."""
        incomplete_transformation = [vp for vp in shape.variation_points if vp.type == "incomplete-transformation"]
        assert len(incomplete_transformation) == 1, "Should have incomplete-transformation variation"


class TestTransformationThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 3, "Should have several themes"
        assert "metamorphosis" in shape.themes, "Should include metamorphosis theme"
        assert "identity" in shape.themes, "Should include identity theme"
        assert "becoming" in shape.themes, "Should include becoming theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 3, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestTransformationCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_catalyst_figure_can_merge_with_guide(self, shape: StoryShape) -> None:
        """Test that catalyst-figure has merge options."""
        catalyst = next((s for s in shape.character_slots if s.slot == "catalyst-figure"), None)
        if catalyst:
            assert len(catalyst.can_merge_with) > 0, "Catalyst-figure should have merge options"
            assert "guide" in catalyst.can_merge_with, "Catalyst can merge with guide"

    def test_guide_can_merge_with_mirror_character(self, shape: StoryShape) -> None:
        """Test that guide has merge options."""
        guide = next((s for s in shape.character_slots if s.slot == "guide"), None)
        if guide:
            assert len(guide.can_merge_with) > 0, "Guide should have merge options"
            assert "mirror-character" in guide.can_merge_with, "Guide can merge with mirror-character"

    def test_anchor_figure_can_merge_with_witness(self, shape: StoryShape) -> None:
        """Test that anchor-figure has merge options."""
        anchor = next((s for s in shape.character_slots if s.slot == "anchor-figure"), None)
        if anchor:
            assert len(anchor.can_merge_with) > 0, "Anchor-figure should have merge options"
            assert "witness" in anchor.can_merge_with, "Anchor-figure can merge with witness"


class TestTransformationSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the transformation shape."""
        data = load_transformation_yaml()
        return StoryShape.model_validate(data)

    def test_origin_state_used_in_beats(self, shape: StoryShape) -> None:
        """Test that origin-state has usage mappings."""
        origin_state = next(s for s in shape.setting_slots if s.slot == "origin-state")
        assert len(origin_state.used_in) > 0, "Origin-state should specify usage"
        assert "stasis" in origin_state.used_in, "Origin-state should be used in stasis"
        assert "catalyst" in origin_state.used_in, "Origin-state should be used in catalyst"

    def test_liminal_space_used_in_transformation(self, shape: StoryShape) -> None:
        """Test that liminal-space is used in transformation beats."""
        liminal_space = next(s for s in shape.setting_slots if s.slot == "liminal-space")
        assert "resistance" in liminal_space.used_in, "Liminal-space should be used in resistance"
        assert "struggle" in liminal_space.used_in, "Liminal-space should be used in struggle"
        assert "surrender" in liminal_space.used_in, "Liminal-space should be used in surrender"

    def test_crucible_used_in_key_moments(self, shape: StoryShape) -> None:
        """Test that crucible is used in key transformation moments."""
        crucible = next(s for s in shape.setting_slots if s.slot == "crucible")
        assert "struggle" in crucible.used_in, "Crucible should be used in struggle"
        assert "surrender" in crucible.used_in, "Crucible should be used in surrender"

    def test_emergence_ground_used_in_emergence(self, shape: StoryShape) -> None:
        """Test that emergence-ground is used in emergence."""
        emergence_ground = next(s for s in shape.setting_slots if s.slot == "emergence-ground")
        assert "emergence" in emergence_ground.used_in, "Emergence-ground should be used in emergence"
