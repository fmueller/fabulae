"""Tests for Fall and Redemption story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_fall_redemption_yaml() -> dict[str, object]:
    """Load the fall and redemption YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "fall-redemption.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestFallRedemptionYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the fall and redemption YAML file exists."""
        shape_path = get_story_shapes_path() / "fall-redemption.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_fall_redemption_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestFallRedemptionValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_fall_redemption_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_fall_redemption_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "fall-redemption"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_fall_redemption_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Fall and Redemption"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_fall_redemption_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_fall_redemption_yaml()
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


class TestFallRedemptionRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 1, "Should have at least the fallen protagonist"

    def test_has_fallen_protagonist_character_slot(self, shape: StoryShape) -> None:
        """Test that the fallen protagonist character slot exists."""
        protagonist_slots = [s for s in shape.character_slots if s.slot == "fallen-protagonist"]
        assert len(protagonist_slots) == 1, "Should have exactly one fallen protagonist slot"
        assert protagonist_slots[0].optional is False, "Fallen protagonist should be required"

    def test_has_tempter_character_slot(self, shape: StoryShape) -> None:
        """Test that the tempter character slot exists."""
        tempter_slots = [s for s in shape.character_slots if s.slot == "tempter"]
        assert len(tempter_slots) == 1, "Should have a tempter slot"

    def test_has_victim_character_slot(self, shape: StoryShape) -> None:
        """Test that the victim character slot exists."""
        victim_slots = [s for s in shape.character_slots if s.slot == "victim"]
        assert len(victim_slots) == 1, "Should have a victim slot"

    def test_has_redeemer_character_slot(self, shape: StoryShape) -> None:
        """Test that the redeemer character slot exists."""
        redeemer_slots = [s for s in shape.character_slots if s.slot == "redeemer"]
        assert len(redeemer_slots) == 1, "Should have a redeemer slot"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestFallRedemptionRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 3, "Should have key locations"

    def test_has_heights_setting(self, shape: StoryShape) -> None:
        """Test that the heights setting exists."""
        heights = [s for s in shape.setting_slots if s.slot == "heights"]
        assert len(heights) == 1, "Should have heights"
        assert heights[0].optional is False, "Heights should be required"

    def test_has_descent_space_setting(self, shape: StoryShape) -> None:
        """Test that the descent-space setting exists."""
        descent_space = [s for s in shape.setting_slots if s.slot == "descent-space"]
        assert len(descent_space) == 1, "Should have descent-space"
        assert descent_space[0].optional is False, "Descent-space should be required"

    def test_has_bottom_setting(self, shape: StoryShape) -> None:
        """Test that the bottom setting exists."""
        bottom = [s for s in shape.setting_slots if s.slot == "bottom"]
        assert len(bottom) == 1, "Should have bottom"
        assert bottom[0].optional is False, "Bottom should be required"

    def test_has_recovery_ground_setting(self, shape: StoryShape) -> None:
        """Test that the recovery-ground setting exists."""
        recovery_ground = [s for s in shape.setting_slots if s.slot == "recovery-ground"]
        assert len(recovery_ground) == 1, "Should have recovery-ground"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestFallRedemptionRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (7 expected)."""
        assert len(shape.required_beats) == 7, f"Expected 7 required beats, got {len(shape.required_beats)}"

    def test_has_status_beat(self, shape: StoryShape) -> None:
        """Test that the status beat exists."""
        status_beats = [b for b in shape.required_beats if b.type == "status"]
        assert len(status_beats) == 1, "Should have status"
        assert status_beats[0].position == "early"

    def test_has_temptation_beat(self, shape: StoryShape) -> None:
        """Test that the temptation beat exists."""
        temptation_beats = [b for b in shape.required_beats if b.type == "temptation"]
        assert len(temptation_beats) == 1, "Should have temptation"
        assert temptation_beats[0].position == "early"
        assert temptation_beats[0].flexibility == "fixed"

    def test_has_fall_beat(self, shape: StoryShape) -> None:
        """Test that the fall beat exists."""
        fall_beats = [b for b in shape.required_beats if b.type == "fall"]
        assert len(fall_beats) == 1, "Should have fall"
        assert fall_beats[0].position == "middle"

    def test_has_bottom_beat(self, shape: StoryShape) -> None:
        """Test that the bottom beat exists."""
        bottom_beats = [b for b in shape.required_beats if b.type == "bottom"]
        assert len(bottom_beats) == 1, "Should have bottom"
        assert bottom_beats[0].position == "late"
        assert bottom_beats[0].flexibility == "fixed"

    def test_has_catalyst_beat(self, shape: StoryShape) -> None:
        """Test that the catalyst beat exists."""
        catalyst_beats = [b for b in shape.required_beats if b.type == "catalyst"]
        assert len(catalyst_beats) == 1, "Should have catalyst"
        assert catalyst_beats[0].position == "late"

    def test_has_climb_beat(self, shape: StoryShape) -> None:
        """Test that the climb beat exists."""
        climb_beats = [b for b in shape.required_beats if b.type == "climb"]
        assert len(climb_beats) == 1, "Should have climb"
        assert climb_beats[0].position == "climax"

    def test_has_redemption_beat(self, shape: StoryShape) -> None:
        """Test that the redemption beat exists."""
        redemption_beats = [b for b in shape.required_beats if b.type == "redemption"]
        assert len(redemption_beats) == 1, "Should have redemption"
        assert redemption_beats[0].position == "climax"


class TestFallRedemptionBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "status" in early_types, "Status should be in early position"
        assert "temptation" in early_types, "Temptation should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 1, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "fall" in middle_types, "Fall should be in middle position"

    def test_late_beats_for_crisis(self, shape: StoryShape) -> None:
        """Test that late beats exist for story crisis."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 1, "Should have late beats for crisis"

        late_types = {b.type for b in late_beats}
        assert "bottom" in late_types, "Bottom should be in late position"
        assert "catalyst" in late_types, "Catalyst should be in late position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "climb" in climax_types, "Climb should be in climax position"
        assert "redemption" in climax_types, "Redemption should be in climax position"


class TestFallRedemptionVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 3, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_relapse_risk_variation(self, shape: StoryShape) -> None:
        """Test that the relapse-risk variation exists."""
        relapse = [vp for vp in shape.variation_points if vp.type == "relapse-risk"]
        assert len(relapse) == 1, "Should have relapse-risk variation"

    def test_has_victim_confrontation_variation(self, shape: StoryShape) -> None:
        """Test that the victim-confrontation variation exists."""
        confrontation = [vp for vp in shape.variation_points if vp.type == "victim-confrontation"]
        assert len(confrontation) == 1, "Should have victim-confrontation variation"

    def test_has_incomplete_redemption_variation(self, shape: StoryShape) -> None:
        """Test that the incomplete-redemption variation exists."""
        incomplete = [vp for vp in shape.variation_points if vp.type == "incomplete-redemption"]
        assert len(incomplete) == 1, "Should have incomplete-redemption variation"


class TestFallRedemptionThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 3, "Should have several themes"
        assert "redemption" in shape.themes, "Should include redemption theme"
        assert "consequences" in shape.themes, "Should include consequences theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 3, "Should have several motifs"
        assert "descent-and-ascent" in shape.motifs, "Should include descent-and-ascent motif"
        assert "rock-bottom" in shape.motifs, "Should include rock-bottom motif"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestFallRedemptionCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_tempter_can_merge_with_enabler(self, shape: StoryShape) -> None:
        """Test that tempter can merge with enabler."""
        tempter = next((s for s in shape.character_slots if s.slot == "tempter"), None)
        if tempter:
            assert "enabler" in tempter.can_merge_with, "Tempter should be able to merge with enabler"

    def test_redeemer_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that redeemer has merge options."""
        redeemer = next((s for s in shape.character_slots if s.slot == "redeemer"), None)
        if redeemer:
            assert len(redeemer.can_merge_with) > 0, "Redeemer should have merge options"


class TestFallRedemptionSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the fall and redemption shape."""
        data = load_fall_redemption_yaml()
        return StoryShape.model_validate(data)

    def test_heights_used_in_beats(self, shape: StoryShape) -> None:
        """Test that heights has usage mappings."""
        heights = next(s for s in shape.setting_slots if s.slot == "heights")
        assert len(heights.used_in) > 0, "Heights should specify usage"
        assert "status" in heights.used_in, "Heights should be used in status"
        assert "redemption" in heights.used_in, "Heights should be used in redemption"

    def test_bottom_used_in_bottom_beat(self, shape: StoryShape) -> None:
        """Test that bottom setting is used in bottom beat."""
        bottom = next(s for s in shape.setting_slots if s.slot == "bottom")
        assert "bottom" in bottom.used_in, "Bottom setting should be used in bottom beat"
        assert "catalyst" in bottom.used_in, "Bottom setting should be used in catalyst beat"

    def test_descent_space_used_in_fall(self, shape: StoryShape) -> None:
        """Test that descent-space is used in fall-related beats."""
        descent_space = next(s for s in shape.setting_slots if s.slot == "descent-space")
        assert "fall" in descent_space.used_in, "Descent-space should be used in fall"
