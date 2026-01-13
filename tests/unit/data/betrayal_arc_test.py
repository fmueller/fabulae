"""Tests for Betrayal Arc story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_betrayal_arc_yaml() -> dict[str, object]:
    """Load the betrayal arc YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "betrayal-arc.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestBetrayalArcYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the betrayal arc YAML file exists."""
        shape_path = get_story_shapes_path() / "betrayal-arc.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_betrayal_arc_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestBetrayalArcValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_betrayal_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_betrayal_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "betrayal-arc"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_betrayal_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Betrayal Arc"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_betrayal_arc_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_betrayal_arc_yaml()
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


class TestBetrayalArcRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have at least protagonist and betrayer"

    def test_has_protagonist_character_slot(self, shape: StoryShape) -> None:
        """Test that the protagonist character slot exists."""
        protagonist_slots = [s for s in shape.character_slots if s.slot == "protagonist"]
        assert len(protagonist_slots) == 1, "Should have exactly one protagonist slot"
        assert protagonist_slots[0].optional is False, "Protagonist should be required"

    def test_has_betrayer_character_slot(self, shape: StoryShape) -> None:
        """Test that the betrayer character slot exists."""
        betrayer_slots = [s for s in shape.character_slots if s.slot == "betrayer"]
        assert len(betrayer_slots) == 1, "Should have exactly one betrayer slot"
        assert betrayer_slots[0].optional is False, "Betrayer should be required"

    def test_has_witness_character_slot(self, shape: StoryShape) -> None:
        """Test that the witness character slot exists."""
        witness_slots = [s for s in shape.character_slots if s.slot == "witness"]
        assert len(witness_slots) == 1, "Should have a witness slot"
        assert witness_slots[0].optional is True, "Witness should be optional"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestBetrayalArcRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 2, "Should have key locations"

    def test_has_trust_space_setting(self, shape: StoryShape) -> None:
        """Test that the trust-space setting exists."""
        trust_space = [s for s in shape.setting_slots if s.slot == "trust-space"]
        assert len(trust_space) == 1, "Should have trust-space"
        assert trust_space[0].optional is False, "Trust-space should be required"

    def test_has_revelation_space_setting(self, shape: StoryShape) -> None:
        """Test that the revelation-space setting exists."""
        revelation_space = [s for s in shape.setting_slots if s.slot == "revelation-space"]
        assert len(revelation_space) == 1, "Should have revelation-space"
        assert revelation_space[0].optional is False, "Revelation-space should be required"

    def test_has_confrontation_space_setting(self, shape: StoryShape) -> None:
        """Test that the confrontation-space setting exists."""
        confrontation_space = [s for s in shape.setting_slots if s.slot == "confrontation-space"]
        assert len(confrontation_space) == 1, "Should have confrontation-space"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestBetrayalArcRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (5-10 expected)."""
        assert 5 <= len(shape.required_beats) <= 10, f"Expected 5-10 required beats, got {len(shape.required_beats)}"

    def test_has_trust_building_beat(self, shape: StoryShape) -> None:
        """Test that the trust-building beat exists."""
        trust_beats = [b for b in shape.required_beats if b.type == "trust-building"]
        assert len(trust_beats) == 1, "Should have trust-building"
        assert trust_beats[0].position == "early"

    def test_has_seeds_of_doubt_beat(self, shape: StoryShape) -> None:
        """Test that the seeds-of-doubt beat exists."""
        doubt_beats = [b for b in shape.required_beats if b.type == "seeds-of-doubt"]
        assert len(doubt_beats) == 1, "Should have seeds-of-doubt"
        assert doubt_beats[0].position == "middle"

    def test_has_revelation_beat(self, shape: StoryShape) -> None:
        """Test that the revelation beat exists."""
        revelation_beats = [b for b in shape.required_beats if b.type == "revelation"]
        assert len(revelation_beats) == 1, "Should have revelation"
        assert revelation_beats[0].position == "late"
        assert revelation_beats[0].flexibility == "fixed"

    def test_has_confrontation_beat(self, shape: StoryShape) -> None:
        """Test that the confrontation beat exists."""
        confrontation_beats = [b for b in shape.required_beats if b.type == "confrontation"]
        assert len(confrontation_beats) == 1, "Should have confrontation"
        assert confrontation_beats[0].position == "climax"
        assert confrontation_beats[0].flexibility == "fixed"

    def test_has_aftermath_beat(self, shape: StoryShape) -> None:
        """Test that the aftermath beat exists."""
        aftermath_beats = [b for b in shape.required_beats if b.type == "aftermath"]
        assert len(aftermath_beats) == 1, "Should have aftermath"
        assert aftermath_beats[0].position == "climax"


class TestBetrayalArcBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "trust-building" in early_types, "Trust-building should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 1, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "seeds-of-doubt" in middle_types, "Seeds of doubt should be in middle position"

    def test_late_beats_for_crisis(self, shape: StoryShape) -> None:
        """Test that late beats exist for story crisis."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 1, "Should have late beats for crisis"

        late_types = {b.type for b in late_beats}
        assert "revelation" in late_types, "Revelation should be in late position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "confrontation" in climax_types, "Confrontation should be in climax position"


class TestBetrayalArcVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 3, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_betrayer_perspective_variation(self, shape: StoryShape) -> None:
        """Test that the betrayer perspective variation exists."""
        perspectives = [vp for vp in shape.variation_points if vp.type == "betrayer-perspective"]
        assert len(perspectives) == 1, "Should have betrayer-perspective variation"

    def test_has_reconciliation_attempt_variation(self, shape: StoryShape) -> None:
        """Test that the reconciliation attempt variation exists."""
        reconciliation = [vp for vp in shape.variation_points if vp.type == "reconciliation-attempt"]
        assert len(reconciliation) == 1, "Should have reconciliation-attempt variation"


class TestBetrayalArcThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 3, "Should have several themes"
        assert "trust" in shape.themes, "Should include trust theme"
        assert "deception" in shape.themes, "Should include deception theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 3, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestBetrayalArcCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_witness_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that witness has merge options."""
        witness = next((s for s in shape.character_slots if s.slot == "witness"), None)
        if witness:
            assert len(witness.can_merge_with) > 0, "Witness should have merge options"

    def test_ally_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that ally has merge options."""
        ally = next((s for s in shape.character_slots if s.slot == "ally"), None)
        if ally:
            assert len(ally.can_merge_with) > 0, "Ally should have merge options"


class TestBetrayalArcSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the betrayal arc shape."""
        data = load_betrayal_arc_yaml()
        return StoryShape.model_validate(data)

    def test_trust_space_used_in_beats(self, shape: StoryShape) -> None:
        """Test that trust-space has usage mappings."""
        trust_space = next(s for s in shape.setting_slots if s.slot == "trust-space")
        assert len(trust_space.used_in) > 0, "Trust-space should specify usage"
        assert "trust-building" in trust_space.used_in, "Trust-space should be used in trust-building"

    def test_revelation_space_used_in_revelation(self, shape: StoryShape) -> None:
        """Test that revelation-space is used in revelation-related beats."""
        revelation_space = next(s for s in shape.setting_slots if s.slot == "revelation-space")
        assert "revelation" in revelation_space.used_in, "Revelation-space should be used in revelation"
