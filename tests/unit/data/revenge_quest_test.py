"""Tests for Revenge Quest story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_revenge_quest_yaml() -> dict[str, object]:
    """Load the revenge quest YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "revenge-quest.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestRevengeQuestYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the revenge quest YAML file exists."""
        shape_path = get_story_shapes_path() / "revenge-quest.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_revenge_quest_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestRevengeQuestValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_revenge_quest_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_revenge_quest_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "revenge-quest"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_revenge_quest_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Revenge Quest"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_revenge_quest_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_revenge_quest_yaml()
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


class TestRevengeQuestRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have at least avenger and target"

    def test_has_avenger_character_slot(self, shape: StoryShape) -> None:
        """Test that the avenger character slot exists."""
        avenger_slots = [s for s in shape.character_slots if s.slot == "avenger"]
        assert len(avenger_slots) == 1, "Should have exactly one avenger slot"
        assert avenger_slots[0].optional is False, "Avenger should be required"

    def test_has_target_character_slot(self, shape: StoryShape) -> None:
        """Test that the target character slot exists."""
        target_slots = [s for s in shape.character_slots if s.slot == "target"]
        assert len(target_slots) == 1, "Should have exactly one target slot"
        assert target_slots[0].optional is False, "Target should be required"

    def test_has_innocent_victim_character_slot(self, shape: StoryShape) -> None:
        """Test that the innocent-victim character slot exists."""
        victim_slots = [s for s in shape.character_slots if s.slot == "innocent-victim"]
        assert len(victim_slots) == 1, "Should have an innocent-victim slot"
        assert victim_slots[0].optional is True, "Innocent-victim should be optional"

    def test_has_reluctant_ally_character_slot(self, shape: StoryShape) -> None:
        """Test that the reluctant-ally character slot exists."""
        ally_slots = [s for s in shape.character_slots if s.slot == "reluctant-ally"]
        assert len(ally_slots) == 1, "Should have a reluctant-ally slot"
        assert ally_slots[0].optional is True, "Reluctant-ally should be optional"

    def test_has_moral_compass_character_slot(self, shape: StoryShape) -> None:
        """Test that the moral-compass character slot exists."""
        compass_slots = [s for s in shape.character_slots if s.slot == "moral-compass"]
        assert len(compass_slots) == 1, "Should have a moral-compass slot"
        assert compass_slots[0].optional is True, "Moral-compass should be optional"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestRevengeQuestRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 3, "Should have key locations"

    def test_has_site_of_wrong_setting(self, shape: StoryShape) -> None:
        """Test that the site-of-wrong setting exists."""
        site_slots = [s for s in shape.setting_slots if s.slot == "site-of-wrong"]
        assert len(site_slots) == 1, "Should have site-of-wrong"
        assert site_slots[0].optional is False, "Site-of-wrong should be required"

    def test_has_hunting_ground_setting(self, shape: StoryShape) -> None:
        """Test that the hunting-ground setting exists."""
        hunting_slots = [s for s in shape.setting_slots if s.slot == "hunting-ground"]
        assert len(hunting_slots) == 1, "Should have hunting-ground"
        assert hunting_slots[0].optional is False, "Hunting-ground should be required"

    def test_has_reckoning_place_setting(self, shape: StoryShape) -> None:
        """Test that the reckoning-place setting exists."""
        reckoning_slots = [s for s in shape.setting_slots if s.slot == "reckoning-place"]
        assert len(reckoning_slots) == 1, "Should have reckoning-place"
        assert reckoning_slots[0].optional is False, "Reckoning-place should be required"

    def test_has_sanctuary_setting(self, shape: StoryShape) -> None:
        """Test that the sanctuary setting exists."""
        sanctuary_slots = [s for s in shape.setting_slots if s.slot == "sanctuary"]
        assert len(sanctuary_slots) == 1, "Should have sanctuary"
        assert sanctuary_slots[0].optional is True, "Sanctuary should be optional"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestRevengeQuestRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (6-10 expected)."""
        assert 6 <= len(shape.required_beats) <= 10, f"Expected 6-10 required beats, got {len(shape.required_beats)}"

    def test_has_wrong_beat(self, shape: StoryShape) -> None:
        """Test that the wrong beat exists."""
        wrong_beats = [b for b in shape.required_beats if b.type == "wrong"]
        assert len(wrong_beats) == 1, "Should have wrong beat"
        assert wrong_beats[0].position == "early"
        assert wrong_beats[0].flexibility == "fixed"

    def test_has_vow_beat(self, shape: StoryShape) -> None:
        """Test that the vow beat exists."""
        vow_beats = [b for b in shape.required_beats if b.type == "vow"]
        assert len(vow_beats) == 1, "Should have vow beat"
        assert vow_beats[0].position == "early"

    def test_has_pursuit_beat(self, shape: StoryShape) -> None:
        """Test that the pursuit beat exists."""
        pursuit_beats = [b for b in shape.required_beats if b.type == "pursuit"]
        assert len(pursuit_beats) == 1, "Should have pursuit beat"
        assert pursuit_beats[0].position == "middle"

    def test_has_cost_beat(self, shape: StoryShape) -> None:
        """Test that the cost beat exists."""
        cost_beats = [b for b in shape.required_beats if b.type == "cost"]
        assert len(cost_beats) == 1, "Should have cost beat"
        assert cost_beats[0].position == "middle"

    def test_has_reckoning_beat(self, shape: StoryShape) -> None:
        """Test that the reckoning beat exists."""
        reckoning_beats = [b for b in shape.required_beats if b.type == "reckoning"]
        assert len(reckoning_beats) == 1, "Should have reckoning beat"
        assert reckoning_beats[0].position == "climax"
        assert reckoning_beats[0].flexibility == "fixed"

    def test_has_aftermath_beat(self, shape: StoryShape) -> None:
        """Test that the aftermath beat exists."""
        aftermath_beats = [b for b in shape.required_beats if b.type == "aftermath"]
        assert len(aftermath_beats) == 1, "Should have aftermath beat"
        assert aftermath_beats[0].position == "climax"


class TestRevengeQuestBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 2, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "wrong" in early_types, "Wrong should be in early position"
        assert "vow" in early_types, "Vow should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 2, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "pursuit" in middle_types, "Pursuit should be in middle position"
        assert "cost" in middle_types, "Cost should be in middle position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "reckoning" in climax_types, "Reckoning should be in climax position"


class TestRevengeQuestVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 5, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_target_perspective_variation(self, shape: StoryShape) -> None:
        """Test that the target perspective variation exists."""
        perspectives = [vp for vp in shape.variation_points if vp.type == "target-perspective"]
        assert len(perspectives) == 1, "Should have target-perspective variation"

    def test_has_becoming_the_monster_variation(self, shape: StoryShape) -> None:
        """Test that the becoming-the-monster variation exists."""
        monster = [vp for vp in shape.variation_points if vp.type == "becoming-the-monster"]
        assert len(monster) == 1, "Should have becoming-the-monster variation"

    def test_has_mercy_choice_variation(self, shape: StoryShape) -> None:
        """Test that the mercy-choice variation exists."""
        mercy = [vp for vp in shape.variation_points if vp.type == "mercy-choice"]
        assert len(mercy) == 1, "Should have mercy-choice variation"

    def test_has_hollow_victory_variation(self, shape: StoryShape) -> None:
        """Test that the hollow-victory variation exists."""
        hollow = [vp for vp in shape.variation_points if vp.type == "hollow-victory"]
        assert len(hollow) == 1, "Should have hollow-victory variation"


class TestRevengeQuestThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 5, "Should have several themes"
        assert "justice" in shape.themes, "Should include justice theme"
        assert "obsession" in shape.themes, "Should include obsession theme"
        assert "transformation" in shape.themes, "Should include transformation theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 5, "Should have several motifs"
        assert "the-hunt" in shape.motifs, "Should include the-hunt motif"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestRevengeQuestCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_innocent_victim_can_merge_with_avenger(self, shape: StoryShape) -> None:
        """Test that innocent-victim can merge with avenger."""
        victim = next((s for s in shape.character_slots if s.slot == "innocent-victim"), None)
        if victim:
            assert "avenger" in victim.can_merge_with, "Victim should merge with avenger"

    def test_reluctant_ally_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that reluctant-ally has merge options."""
        ally = next((s for s in shape.character_slots if s.slot == "reluctant-ally"), None)
        if ally:
            assert len(ally.can_merge_with) > 0, "Reluctant-ally should have merge options"

    def test_moral_compass_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that moral-compass has merge options."""
        compass = next((s for s in shape.character_slots if s.slot == "moral-compass"), None)
        if compass:
            assert len(compass.can_merge_with) > 0, "Moral-compass should have merge options"


class TestRevengeQuestSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the revenge quest shape."""
        data = load_revenge_quest_yaml()
        return StoryShape.model_validate(data)

    def test_site_of_wrong_used_in_beats(self, shape: StoryShape) -> None:
        """Test that site-of-wrong has usage mappings."""
        site = next(s for s in shape.setting_slots if s.slot == "site-of-wrong")
        assert len(site.used_in) > 0, "Site-of-wrong should specify usage"
        assert "wrong" in site.used_in, "Site-of-wrong should be used in wrong beat"
        assert "vow" in site.used_in, "Site-of-wrong should be used in vow beat"

    def test_hunting_ground_used_in_pursuit(self, shape: StoryShape) -> None:
        """Test that hunting-ground is used in pursuit-related beats."""
        hunting_ground = next(s for s in shape.setting_slots if s.slot == "hunting-ground")
        assert "pursuit" in hunting_ground.used_in, "Hunting-ground should be used in pursuit"
        assert "cost" in hunting_ground.used_in, "Hunting-ground should be used in cost"

    def test_reckoning_place_used_in_reckoning(self, shape: StoryShape) -> None:
        """Test that reckoning-place is used in reckoning beat."""
        reckoning_place = next(s for s in shape.setting_slots if s.slot == "reckoning-place")
        assert "reckoning" in reckoning_place.used_in, "Reckoning-place should be used in reckoning"
