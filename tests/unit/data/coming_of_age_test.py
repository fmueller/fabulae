"""Tests for Coming of Age story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_coming_of_age_yaml() -> dict[str, object]:
    """Load the coming-of-age YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "coming-of-age.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestComingOfAgeYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the coming-of-age YAML file exists."""
        shape_path = get_story_shapes_path() / "coming-of-age.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_coming_of_age_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestComingOfAgeValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_coming_of_age_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_coming_of_age_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "coming-of-age"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_coming_of_age_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Coming of Age"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_coming_of_age_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_coming_of_age_yaml()
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


class TestComingOfAgeRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have at least young-protagonist and one supporting character"

    def test_has_young_protagonist_slot(self, shape: StoryShape) -> None:
        """Test that the young protagonist character slot exists."""
        protagonist_slots = [s for s in shape.character_slots if s.slot == "young-protagonist"]
        assert len(protagonist_slots) == 1, "Should have exactly one young-protagonist slot"
        assert protagonist_slots[0].optional is False, "Young protagonist should be required"

    def test_has_guide_figure_slot(self, shape: StoryShape) -> None:
        """Test that the guide figure character slot exists."""
        guide_slots = [s for s in shape.character_slots if s.slot == "guide-figure"]
        assert len(guide_slots) == 1, "Should have guide-figure slot"

    def test_has_peer_slot(self, shape: StoryShape) -> None:
        """Test that the peer character slot exists."""
        peer_slots = [s for s in shape.character_slots if s.slot == "peer"]
        assert len(peer_slots) == 1, "Should have peer slot"

    def test_has_antagonist_slot(self, shape: StoryShape) -> None:
        """Test that the antagonist character slot exists."""
        antagonist_slots = [s for s in shape.character_slots if s.slot == "antagonist"]
        assert len(antagonist_slots) == 1, "Should have antagonist slot"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestComingOfAgeRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 2, "Should have key locations"

    def test_has_sanctuary_setting(self, shape: StoryShape) -> None:
        """Test that the sanctuary setting exists."""
        sanctuary = [s for s in shape.setting_slots if s.slot == "sanctuary"]
        assert len(sanctuary) == 1, "Should have sanctuary"
        assert sanctuary[0].optional is False, "Sanctuary should be required"

    def test_has_testing_ground_setting(self, shape: StoryShape) -> None:
        """Test that the testing-ground setting exists."""
        testing_ground = [s for s in shape.setting_slots if s.slot == "testing-ground"]
        assert len(testing_ground) == 1, "Should have testing-ground"
        assert testing_ground[0].optional is False, "Testing-ground should be required"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestComingOfAgeRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (5-10 expected)."""
        assert 5 <= len(shape.required_beats) <= 10, f"Expected 5-10 required beats, got {len(shape.required_beats)}"

    def test_has_innocence_beat(self, shape: StoryShape) -> None:
        """Test that the innocence beat exists."""
        innocence_beats = [b for b in shape.required_beats if b.type == "innocence"]
        assert len(innocence_beats) == 1, "Should have innocence"
        assert innocence_beats[0].position == "early"

    def test_has_challenge_beat(self, shape: StoryShape) -> None:
        """Test that the challenge beat exists."""
        challenge_beats = [b for b in shape.required_beats if b.type == "challenge"]
        assert len(challenge_beats) == 1, "Should have challenge"
        assert challenge_beats[0].position == "middle"

    def test_has_failure_beat(self, shape: StoryShape) -> None:
        """Test that the failure beat exists."""
        failure_beats = [b for b in shape.required_beats if b.type == "failure"]
        assert len(failure_beats) == 1, "Should have failure"
        assert failure_beats[0].position == "middle"
        assert failure_beats[0].flexibility == "fixed"

    def test_has_growth_beat(self, shape: StoryShape) -> None:
        """Test that the growth beat exists."""
        growth_beats = [b for b in shape.required_beats if b.type == "growth"]
        assert len(growth_beats) == 1, "Should have growth"
        assert growth_beats[0].position == "late"

    def test_has_maturity_beat(self, shape: StoryShape) -> None:
        """Test that the maturity beat exists."""
        maturity_beats = [b for b in shape.required_beats if b.type == "maturity"]
        assert len(maturity_beats) == 1, "Should have maturity"
        assert maturity_beats[0].position == "climax"


class TestComingOfAgeBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "innocence" in early_types, "Innocence should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 2, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "challenge" in middle_types, "Challenge should be in middle position"
        assert "failure" in middle_types, "Failure should be in middle position"

    def test_late_beats_for_growth(self, shape: StoryShape) -> None:
        """Test that late beats exist for growth."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 1, "Should have late beats for growth"

        late_types = {b.type for b in late_beats}
        assert "growth" in late_types, "Growth should be in late position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "maturity" in climax_types, "Maturity should be in climax position"


class TestComingOfAgeVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 3, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_first_love_variation(self, shape: StoryShape) -> None:
        """Test that the first-love variation exists."""
        first_love = [vp for vp in shape.variation_points if vp.type == "first-love"]
        assert len(first_love) == 1, "Should have first-love variation"

    def test_has_leaving_home_variation(self, shape: StoryShape) -> None:
        """Test that the leaving-home variation exists."""
        leaving_home = [vp for vp in shape.variation_points if vp.type == "leaving-home"]
        assert len(leaving_home) == 1, "Should have leaving-home variation"


class TestComingOfAgeThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 3, "Should have several themes"
        assert "identity" in shape.themes, "Should include identity theme"
        assert "self-discovery" in shape.themes, "Should include self-discovery theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 3, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestComingOfAgeCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_guide_figure_can_merge_with_parent(self, shape: StoryShape) -> None:
        """Test that guide-figure has merge options."""
        guide = next((s for s in shape.character_slots if s.slot == "guide-figure"), None)
        if guide:
            assert len(guide.can_merge_with) > 0, "Guide-figure should have merge options"
            assert "parent-figure" in guide.can_merge_with, "Guide can merge with parent-figure"

    def test_peer_can_merge_with_rival(self, shape: StoryShape) -> None:
        """Test that peer has merge options."""
        peer = next((s for s in shape.character_slots if s.slot == "peer"), None)
        if peer:
            assert len(peer.can_merge_with) > 0, "Peer should have merge options"
            assert "rival" in peer.can_merge_with, "Peer can merge with rival"


class TestComingOfAgeSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the coming-of-age shape."""
        data = load_coming_of_age_yaml()
        return StoryShape.model_validate(data)

    def test_sanctuary_used_in_beats(self, shape: StoryShape) -> None:
        """Test that sanctuary has usage mappings."""
        sanctuary = next(s for s in shape.setting_slots if s.slot == "sanctuary")
        assert len(sanctuary.used_in) > 0, "Sanctuary should specify usage"
        assert "innocence" in sanctuary.used_in, "Sanctuary should be used in innocence"

    def test_testing_ground_used_in_development(self, shape: StoryShape) -> None:
        """Test that testing-ground is used in development beats."""
        testing_ground = next(s for s in shape.setting_slots if s.slot == "testing-ground")
        assert "challenge" in testing_ground.used_in, "Testing-ground should be used in challenge"
