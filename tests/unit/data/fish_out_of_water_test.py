"""Tests for Fish Out of Water story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_fish_out_of_water_yaml() -> dict[str, object]:
    """Load the fish-out-of-water YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "fish-out-of-water.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestFishOutOfWaterYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the fish-out-of-water YAML file exists."""
        shape_path = get_story_shapes_path() / "fish-out-of-water.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_fish_out_of_water_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestFishOutOfWaterValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_fish_out_of_water_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_fish_out_of_water_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "fish-out-of-water"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_fish_out_of_water_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Fish Out of Water"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_fish_out_of_water_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_fish_out_of_water_yaml()
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


class TestFishOutOfWaterRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have at least displaced-protagonist and supporting characters"

    def test_has_displaced_protagonist_slot(self, shape: StoryShape) -> None:
        """Test that the displaced protagonist character slot exists."""
        protagonist_slots = [s for s in shape.character_slots if s.slot == "displaced-protagonist"]
        assert len(protagonist_slots) == 1, "Should have exactly one displaced-protagonist slot"
        assert protagonist_slots[0].optional is False, "Displaced protagonist should be required"

    def test_has_guide_slot(self, shape: StoryShape) -> None:
        """Test that the guide character slot exists."""
        guide_slots = [s for s in shape.character_slots if s.slot == "guide"]
        assert len(guide_slots) == 1, "Should have guide slot"

    def test_has_antagonist_slot(self, shape: StoryShape) -> None:
        """Test that the antagonist character slot exists."""
        antagonist_slots = [s for s in shape.character_slots if s.slot == "antagonist"]
        assert len(antagonist_slots) == 1, "Should have antagonist slot"

    def test_has_ally_slot(self, shape: StoryShape) -> None:
        """Test that the ally character slot exists."""
        ally_slots = [s for s in shape.character_slots if s.slot == "ally"]
        assert len(ally_slots) == 1, "Should have ally slot"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestFishOutOfWaterRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 2, "Should have key locations"

    def test_has_arrival_point_setting(self, shape: StoryShape) -> None:
        """Test that the arrival-point setting exists."""
        arrival_point = [s for s in shape.setting_slots if s.slot == "arrival-point"]
        assert len(arrival_point) == 1, "Should have arrival-point"
        assert arrival_point[0].optional is False, "Arrival-point should be required"

    def test_has_struggle_arena_setting(self, shape: StoryShape) -> None:
        """Test that the struggle-arena setting exists."""
        struggle_arena = [s for s in shape.setting_slots if s.slot == "struggle-arena"]
        assert len(struggle_arena) == 1, "Should have struggle-arena"
        assert struggle_arena[0].optional is False, "Struggle-arena should be required"

    def test_has_refuge_setting(self, shape: StoryShape) -> None:
        """Test that the refuge setting exists."""
        refuge = [s for s in shape.setting_slots if s.slot == "refuge"]
        assert len(refuge) == 1, "Should have refuge"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestFishOutOfWaterRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (5-10 expected)."""
        assert 5 <= len(shape.required_beats) <= 10, f"Expected 5-10 required beats, got {len(shape.required_beats)}"

    def test_has_displacement_beat(self, shape: StoryShape) -> None:
        """Test that the displacement beat exists."""
        displacement_beats = [b for b in shape.required_beats if b.type == "displacement"]
        assert len(displacement_beats) == 1, "Should have displacement"
        assert displacement_beats[0].position == "early"
        assert displacement_beats[0].flexibility == "fixed"

    def test_has_confusion_beat(self, shape: StoryShape) -> None:
        """Test that the confusion beat exists."""
        confusion_beats = [b for b in shape.required_beats if b.type == "confusion"]
        assert len(confusion_beats) == 1, "Should have confusion"
        assert confusion_beats[0].position == "early"

    def test_has_struggle_beat(self, shape: StoryShape) -> None:
        """Test that the struggle beat exists."""
        struggle_beats = [b for b in shape.required_beats if b.type == "struggle"]
        assert len(struggle_beats) == 1, "Should have struggle"
        assert struggle_beats[0].position == "middle"

    def test_has_adaptation_beat(self, shape: StoryShape) -> None:
        """Test that the adaptation beat exists."""
        adaptation_beats = [b for b in shape.required_beats if b.type == "adaptation"]
        assert len(adaptation_beats) == 1, "Should have adaptation"
        assert adaptation_beats[0].position == "late"

    def test_has_mastery_beat(self, shape: StoryShape) -> None:
        """Test that the mastery beat exists."""
        mastery_beats = [b for b in shape.required_beats if b.type == "mastery"]
        assert len(mastery_beats) == 1, "Should have mastery"
        assert mastery_beats[0].position == "climax"


class TestFishOutOfWaterBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "displacement" in early_types, "Displacement should be in early position"
        assert "confusion" in early_types, "Confusion should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 1, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "struggle" in middle_types, "Struggle should be in middle position"

    def test_late_beats_for_growth(self, shape: StoryShape) -> None:
        """Test that late beats exist for growth."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 1, "Should have late beats for growth"

        late_types = {b.type for b in late_beats}
        assert "adaptation" in late_types, "Adaptation should be in late position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "mastery" in climax_types, "Mastery should be in climax position"


class TestFishOutOfWaterVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 3, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_return_opportunity_variation(self, shape: StoryShape) -> None:
        """Test that the return-opportunity variation exists."""
        return_opportunity = [vp for vp in shape.variation_points if vp.type == "return-opportunity"]
        assert len(return_opportunity) == 1, "Should have return-opportunity variation"

    def test_has_discovery_of_advantage_variation(self, shape: StoryShape) -> None:
        """Test that the discovery-of-advantage variation exists."""
        discovery = [vp for vp in shape.variation_points if vp.type == "discovery-of-advantage"]
        assert len(discovery) == 1, "Should have discovery-of-advantage variation"

    def test_has_culture_clash_crisis_variation(self, shape: StoryShape) -> None:
        """Test that the culture-clash-crisis variation exists."""
        culture_clash = [vp for vp in shape.variation_points if vp.type == "culture-clash-crisis"]
        assert len(culture_clash) == 1, "Should have culture-clash-crisis variation"


class TestFishOutOfWaterThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 3, "Should have several themes"
        assert "belonging" in shape.themes, "Should include belonging theme"
        assert "adaptation" in shape.themes, "Should include adaptation theme"
        assert "identity" in shape.themes, "Should include identity theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 3, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestFishOutOfWaterCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_guide_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that guide has merge options."""
        guide = next((s for s in shape.character_slots if s.slot == "guide"), None)
        if guide:
            assert len(guide.can_merge_with) > 0, "Guide should have merge options"
            assert "ally" in guide.can_merge_with, "Guide can merge with ally"

    def test_ally_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that ally has merge options."""
        ally = next((s for s in shape.character_slots if s.slot == "ally"), None)
        if ally:
            assert len(ally.can_merge_with) > 0, "Ally should have merge options"
            assert "guide" in ally.can_merge_with, "Ally can merge with guide"


class TestFishOutOfWaterSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fish-out-of-water shape."""
        data = load_fish_out_of_water_yaml()
        return StoryShape.model_validate(data)

    def test_arrival_point_used_in_beats(self, shape: StoryShape) -> None:
        """Test that arrival-point has usage mappings."""
        arrival_point = next(s for s in shape.setting_slots if s.slot == "arrival-point")
        assert len(arrival_point.used_in) > 0, "Arrival-point should specify usage"
        assert "displacement" in arrival_point.used_in, "Arrival-point should be used in displacement"

    def test_struggle_arena_used_in_struggle(self, shape: StoryShape) -> None:
        """Test that struggle-arena is used in struggle-related beats."""
        struggle_arena = next(s for s in shape.setting_slots if s.slot == "struggle-arena")
        assert "struggle" in struggle_arena.used_in, "Struggle-arena should be used in struggle"
        assert "adaptation" in struggle_arena.used_in, "Struggle-arena should be used in adaptation"
