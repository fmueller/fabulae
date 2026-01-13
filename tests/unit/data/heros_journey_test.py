"""Tests for Hero's Journey story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_heros_journey_yaml() -> dict[str, object]:
    """Load the hero's journey YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "heros-journey.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestHerosJourneyYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the hero's journey YAML file exists."""
        shape_path = get_story_shapes_path() / "heros-journey.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_heros_journey_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestHerosJourneyValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_heros_journey_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_heros_journey_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "heros-journey"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_heros_journey_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Hero's Journey"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_heros_journey_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_heros_journey_yaml()
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


class TestHerosJourneyRequiredFields:
    """Tests that all required fields are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the hero's journey shape."""
        data = load_heros_journey_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have at least hero and shadow"

    def test_has_hero_character_slot(self, shape: StoryShape) -> None:
        """Test that the hero character slot exists."""
        hero_slots = [s for s in shape.character_slots if s.slot == "hero"]
        assert len(hero_slots) == 1, "Should have exactly one hero slot"
        assert hero_slots[0].optional is False, "Hero should be required"

    def test_has_mentor_character_slot(self, shape: StoryShape) -> None:
        """Test that the mentor character slot exists."""
        mentor_slots = [s for s in shape.character_slots if s.slot == "mentor"]
        assert len(mentor_slots) == 1, "Should have a mentor slot"

    def test_has_shadow_character_slot(self, shape: StoryShape) -> None:
        """Test that the shadow (antagonist) character slot exists."""
        shadow_slots = [s for s in shape.character_slots if s.slot == "shadow"]
        assert len(shadow_slots) == 1, "Should have a shadow slot"
        assert shadow_slots[0].optional is False, "Shadow should be required"

    def test_has_ally_character_slot(self, shape: StoryShape) -> None:
        """Test that the ally character slot exists."""
        ally_slots = [s for s in shape.character_slots if s.slot == "ally"]
        assert len(ally_slots) == 1, "Should have an ally slot"

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 3, "Should have key locations"

    def test_has_ordinary_world_setting(self, shape: StoryShape) -> None:
        """Test that the ordinary world setting exists."""
        ordinary_world = [s for s in shape.setting_slots if s.slot == "ordinary-world"]
        assert len(ordinary_world) == 1, "Should have ordinary world"
        assert ordinary_world[0].optional is False, "Ordinary world should be required"

    def test_has_special_world_setting(self, shape: StoryShape) -> None:
        """Test that the special world setting exists."""
        special_world = [s for s in shape.setting_slots if s.slot == "special-world"]
        assert len(special_world) == 1, "Should have special world"

    def test_has_innermost_cave_setting(self, shape: StoryShape) -> None:
        """Test that the innermost cave setting exists."""
        cave = [s for s in shape.setting_slots if s.slot == "innermost-cave"]
        assert len(cave) == 1, "Should have innermost cave"

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (8-12 expected)."""
        assert 8 <= len(shape.required_beats) <= 15, f"Expected 8-15 required beats, got {len(shape.required_beats)}"

    def test_has_call_to_adventure_beat(self, shape: StoryShape) -> None:
        """Test that the call to adventure beat exists."""
        call_beats = [b for b in shape.required_beats if b.type == "call-to-adventure"]
        assert len(call_beats) == 1, "Should have call to adventure"
        assert call_beats[0].position == "early"

    def test_has_crossing_threshold_beat(self, shape: StoryShape) -> None:
        """Test that the crossing threshold beat exists."""
        threshold_beats = [b for b in shape.required_beats if b.type == "crossing-threshold"]
        assert len(threshold_beats) == 1, "Should have crossing threshold"
        assert threshold_beats[0].position == "early"

    def test_has_ordeal_beat(self, shape: StoryShape) -> None:
        """Test that the ordeal beat exists."""
        ordeal_beats = [b for b in shape.required_beats if b.type == "ordeal"]
        assert len(ordeal_beats) == 1, "Should have ordeal"
        assert ordeal_beats[0].position == "late"
        assert ordeal_beats[0].flexibility == "fixed"

    def test_has_reward_beat(self, shape: StoryShape) -> None:
        """Test that the reward beat exists."""
        reward_beats = [b for b in shape.required_beats if b.type == "reward"]
        assert len(reward_beats) == 1, "Should have reward"

    def test_has_resurrection_beat(self, shape: StoryShape) -> None:
        """Test that the resurrection beat exists."""
        resurrection_beats = [b for b in shape.required_beats if b.type == "resurrection"]
        assert len(resurrection_beats) == 1, "Should have resurrection"
        assert resurrection_beats[0].position == "climax"

    def test_has_return_with_elixir_beat(self, shape: StoryShape) -> None:
        """Test that the return with elixir beat exists."""
        return_beats = [b for b in shape.required_beats if b.type == "return-with-elixir"]
        assert len(return_beats) == 1, "Should have return with elixir"

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 3, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 3, "Should have several themes"
        assert "transformation" in shape.themes, "Should include transformation theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 3, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestHerosJourneyBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the hero's journey shape."""
        data = load_heros_journey_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 3, "Should have several early beats"

        early_types = {b.type for b in early_beats}
        expected_early = {"ordinary-world-establishment", "call-to-adventure", "crossing-threshold"}
        assert expected_early.issubset(early_types), f"Missing expected early beats: {expected_early - early_types}"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 1, "Should have middle beats for development"

    def test_late_beats_for_crisis(self, shape: StoryShape) -> None:
        """Test that late beats exist for story crisis."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 2, "Should have late beats for crisis"

        late_types = {b.type for b in late_beats}
        assert "ordeal" in late_types, "Ordeal should be in late position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "resurrection" in climax_types, "Resurrection should be in climax position"


class TestHerosJourneyCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the hero's journey shape."""
        data = load_heros_journey_yaml()
        return StoryShape.model_validate(data)

    def test_mentor_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that mentor has merge options."""
        mentor = next(s for s in shape.character_slots if s.slot == "mentor")
        assert len(mentor.can_merge_with) > 0, "Mentor should have merge options"

    def test_shapeshifter_can_merge_with_ally_or_shadow(self, shape: StoryShape) -> None:
        """Test that shapeshifter can merge appropriately."""
        shapeshifter_slots = [s for s in shape.character_slots if s.slot == "shapeshifter"]
        if shapeshifter_slots:
            shapeshifter = shapeshifter_slots[0]
            # Shapeshifter should be able to merge with ally or shadow
            possible_merges = {"ally", "shadow"}
            assert any(m in possible_merges for m in shapeshifter.can_merge_with), (
                "Shapeshifter should be able to merge with ally or shadow"
            )

    def test_all_slots_have_needs_description(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestHerosJourneySettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the hero's journey shape."""
        data = load_heros_journey_yaml()
        return StoryShape.model_validate(data)

    def test_ordinary_world_used_in_beats(self, shape: StoryShape) -> None:
        """Test that ordinary world has usage mappings."""
        ordinary = next(s for s in shape.setting_slots if s.slot == "ordinary-world")
        assert len(ordinary.used_in) > 0, "Ordinary world should specify usage"

    def test_innermost_cave_used_in_ordeal(self, shape: StoryShape) -> None:
        """Test that innermost cave is used in ordeal-related beats."""
        cave = next(s for s in shape.setting_slots if s.slot == "innermost-cave")
        # The cave should be used in at least the ordeal or approach
        ordeal_related = {"ordeal", "approach-innermost-cave", "reward"}
        assert any(usage in ordeal_related for usage in cave.used_in), (
            "Innermost cave should be used in ordeal-related scenes"
        )

    def test_all_settings_have_needs_description(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"
