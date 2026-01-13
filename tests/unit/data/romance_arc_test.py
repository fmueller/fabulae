"""Tests for Romance Arc story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_romance_arc_yaml() -> dict[str, object]:
    """Load the romance arc YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "romance-arc.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestRomanceArcYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the romance arc YAML file exists."""
        shape_path = get_story_shapes_path() / "romance-arc.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_romance_arc_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestRomanceArcValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_romance_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_romance_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "romance-arc"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_romance_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Romance Arc"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_romance_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_romance_arc_yaml()
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


class TestRomanceArcRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have at least lover-a and lover-b"

    def test_has_lover_a_character_slot(self, shape: StoryShape) -> None:
        """Test that the lover-a character slot exists."""
        lover_a_slots = [s for s in shape.character_slots if s.slot == "lover-a"]
        assert len(lover_a_slots) == 1, "Should have exactly one lover-a slot"
        assert lover_a_slots[0].optional is False, "Lover-a should be required"

    def test_has_lover_b_character_slot(self, shape: StoryShape) -> None:
        """Test that the lover-b character slot exists."""
        lover_b_slots = [s for s in shape.character_slots if s.slot == "lover-b"]
        assert len(lover_b_slots) == 1, "Should have exactly one lover-b slot"
        assert lover_b_slots[0].optional is False, "Lover-b should be required"

    def test_has_rival_character_slot(self, shape: StoryShape) -> None:
        """Test that the rival character slot exists."""
        rival_slots = [s for s in shape.character_slots if s.slot == "rival"]
        assert len(rival_slots) == 1, "Should have a rival slot"
        assert rival_slots[0].optional is True, "Rival should be optional"

    def test_has_confidant_character_slot(self, shape: StoryShape) -> None:
        """Test that the confidant character slot exists."""
        confidant_slots = [s for s in shape.character_slots if s.slot == "confidant"]
        assert len(confidant_slots) == 1, "Should have a confidant slot"
        assert confidant_slots[0].optional is True, "Confidant should be optional"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestRomanceArcRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 2, "Should have key locations"

    def test_has_meeting_place_setting(self, shape: StoryShape) -> None:
        """Test that the meeting-place setting exists."""
        meeting_place = [s for s in shape.setting_slots if s.slot == "meeting-place"]
        assert len(meeting_place) == 1, "Should have meeting-place"
        assert meeting_place[0].optional is False, "Meeting-place should be required"

    def test_has_intimacy_space_setting(self, shape: StoryShape) -> None:
        """Test that the intimacy-space setting exists."""
        intimacy_space = [s for s in shape.setting_slots if s.slot == "intimacy-space"]
        assert len(intimacy_space) == 1, "Should have intimacy-space"
        assert intimacy_space[0].optional is False, "Intimacy-space should be required"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestRomanceArcRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (6-8 expected)."""
        assert 6 <= len(shape.required_beats) <= 10, f"Expected 6-10 required beats, got {len(shape.required_beats)}"

    def test_has_meet_beat(self, shape: StoryShape) -> None:
        """Test that the meet beat exists."""
        meet_beats = [b for b in shape.required_beats if b.type == "meet"]
        assert len(meet_beats) == 1, "Should have meet"
        assert meet_beats[0].position == "early"
        assert meet_beats[0].flexibility == "fixed"

    def test_has_attraction_beat(self, shape: StoryShape) -> None:
        """Test that the attraction beat exists."""
        attraction_beats = [b for b in shape.required_beats if b.type == "attraction"]
        assert len(attraction_beats) == 1, "Should have attraction"
        assert attraction_beats[0].position == "early"

    def test_has_obstacle_beat(self, shape: StoryShape) -> None:
        """Test that the obstacle beat exists."""
        obstacle_beats = [b for b in shape.required_beats if b.type == "obstacle"]
        assert len(obstacle_beats) == 1, "Should have obstacle"
        assert obstacle_beats[0].position == "middle"

    def test_has_crisis_beat(self, shape: StoryShape) -> None:
        """Test that the crisis beat exists."""
        crisis_beats = [b for b in shape.required_beats if b.type == "crisis"]
        assert len(crisis_beats) == 1, "Should have crisis"
        assert crisis_beats[0].position == "late"
        assert crisis_beats[0].flexibility == "fixed"

    def test_has_declaration_beat(self, shape: StoryShape) -> None:
        """Test that the declaration beat exists."""
        declaration_beats = [b for b in shape.required_beats if b.type == "declaration"]
        assert len(declaration_beats) == 1, "Should have declaration"
        assert declaration_beats[0].position == "late"

    def test_has_union_beat(self, shape: StoryShape) -> None:
        """Test that the union beat exists."""
        union_beats = [b for b in shape.required_beats if b.type == "union"]
        assert len(union_beats) == 1, "Should have union"
        assert union_beats[0].position == "climax"


class TestRomanceArcBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "meet" in early_types, "Meet should be in early position"
        assert "attraction" in early_types, "Attraction should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 1, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "obstacle" in middle_types, "Obstacle should be in middle position"

    def test_late_beats_for_crisis(self, shape: StoryShape) -> None:
        """Test that late beats exist for story crisis."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 1, "Should have late beats for crisis"

        late_types = {b.type for b in late_beats}
        assert "crisis" in late_types, "Crisis should be in late position"
        assert "declaration" in late_types, "Declaration should be in late position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "union" in climax_types, "Union should be in climax position"


class TestRomanceArcVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 5, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_enemies_to_lovers_variation(self, shape: StoryShape) -> None:
        """Test that the enemies-to-lovers variation exists."""
        enemies = [vp for vp in shape.variation_points if vp.type == "enemies-to-lovers"]
        assert len(enemies) == 1, "Should have enemies-to-lovers variation"

    def test_has_love_triangle_variation(self, shape: StoryShape) -> None:
        """Test that the love-triangle variation exists."""
        triangle = [vp for vp in shape.variation_points if vp.type == "love-triangle"]
        assert len(triangle) == 1, "Should have love-triangle variation"

    def test_has_grand_gesture_variation(self, shape: StoryShape) -> None:
        """Test that the grand-gesture variation exists."""
        gesture = [vp for vp in shape.variation_points if vp.type == "grand-gesture"]
        assert len(gesture) == 1, "Should have grand-gesture variation"


class TestRomanceArcThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 5, "Should have several themes"
        assert "love" in shape.themes, "Should include love theme"
        assert "vulnerability" in shape.themes, "Should include vulnerability theme"
        assert "trust" in shape.themes, "Should include trust theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 4, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 50  # Should be a meaningful description


class TestRomanceArcCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_rival_can_merge_with_antagonist(self, shape: StoryShape) -> None:
        """Test that rival has merge option with antagonist."""
        rival = next((s for s in shape.character_slots if s.slot == "rival"), None)
        assert rival is not None
        assert "antagonist" in rival.can_merge_with, "Rival should be able to merge with antagonist"

    def test_confidant_can_merge_with_matchmaker(self, shape: StoryShape) -> None:
        """Test that confidant has merge option with matchmaker."""
        confidant = next((s for s in shape.character_slots if s.slot == "confidant"), None)
        if confidant:
            assert "matchmaker" in confidant.can_merge_with, "Confidant should be able to merge with matchmaker"


class TestRomanceArcSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the romance arc shape."""
        data = load_romance_arc_yaml()
        return StoryShape.model_validate(data)

    def test_meeting_place_used_in_beats(self, shape: StoryShape) -> None:
        """Test that meeting-place has usage mappings."""
        meeting_place = next(s for s in shape.setting_slots if s.slot == "meeting-place")
        assert len(meeting_place.used_in) > 0, "Meeting-place should specify usage"
        assert "meet" in meeting_place.used_in, "Meeting-place should be used in meet"
        assert "attraction" in meeting_place.used_in, "Meeting-place should be used in attraction"

    def test_intimacy_space_used_in_declaration(self, shape: StoryShape) -> None:
        """Test that intimacy-space is used in intimacy-related beats."""
        intimacy_space = next(s for s in shape.setting_slots if s.slot == "intimacy-space")
        assert "attraction" in intimacy_space.used_in, "Intimacy-space should be used in attraction"
        assert "declaration" in intimacy_space.used_in, "Intimacy-space should be used in declaration"
        assert "union" in intimacy_space.used_in, "Intimacy-space should be used in union"
