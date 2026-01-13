"""Tests for Mystery Reveal story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_mystery_reveal_yaml() -> dict[str, object]:
    """Load the mystery reveal YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "mystery-reveal.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestMysteryRevealYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the mystery reveal YAML file exists."""
        shape_path = get_story_shapes_path() / "mystery-reveal.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_mystery_reveal_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestMysteryRevealValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_mystery_reveal_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_mystery_reveal_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "mystery-reveal"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_mystery_reveal_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Mystery Reveal"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_mystery_reveal_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_mystery_reveal_yaml()
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


class TestMysteryRevealRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 3, "Should have at least investigator, suspect, and victim"

    def test_has_investigator_character_slot(self, shape: StoryShape) -> None:
        """Test that the investigator character slot exists."""
        investigator_slots = [s for s in shape.character_slots if s.slot == "investigator"]
        assert len(investigator_slots) == 1, "Should have exactly one investigator slot"
        assert investigator_slots[0].optional is False, "Investigator should be required"

    def test_has_suspect_character_slot(self, shape: StoryShape) -> None:
        """Test that the suspect character slot exists."""
        suspect_slots = [s for s in shape.character_slots if s.slot == "suspect"]
        assert len(suspect_slots) == 1, "Should have exactly one suspect slot"
        assert suspect_slots[0].optional is False, "Suspect should be required"

    def test_has_victim_character_slot(self, shape: StoryShape) -> None:
        """Test that the victim character slot exists."""
        victim_slots = [s for s in shape.character_slots if s.slot == "victim"]
        assert len(victim_slots) == 1, "Should have exactly one victim slot"
        assert victim_slots[0].optional is False, "Victim should be required"

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


class TestMysteryRevealRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 3, "Should have key locations"

    def test_has_crime_scene_setting(self, shape: StoryShape) -> None:
        """Test that the crime-scene setting exists."""
        crime_scene = [s for s in shape.setting_slots if s.slot == "crime-scene"]
        assert len(crime_scene) == 1, "Should have crime-scene"
        assert crime_scene[0].optional is False, "Crime-scene should be required"

    def test_has_investigation_hub_setting(self, shape: StoryShape) -> None:
        """Test that the investigation-hub setting exists."""
        investigation_hub = [s for s in shape.setting_slots if s.slot == "investigation-hub"]
        assert len(investigation_hub) == 1, "Should have investigation-hub"
        assert investigation_hub[0].optional is False, "Investigation-hub should be required"

    def test_has_revelation_space_setting(self, shape: StoryShape) -> None:
        """Test that the revelation-space setting exists."""
        revelation_space = [s for s in shape.setting_slots if s.slot == "revelation-space"]
        assert len(revelation_space) == 1, "Should have revelation-space"
        assert revelation_space[0].optional is False, "Revelation-space should be required"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestMysteryRevealRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (6-8 expected)."""
        assert 6 <= len(shape.required_beats) <= 10, f"Expected 6-10 required beats, got {len(shape.required_beats)}"

    def test_has_hook_beat(self, shape: StoryShape) -> None:
        """Test that the hook beat exists."""
        hook_beats = [b for b in shape.required_beats if b.type == "hook"]
        assert len(hook_beats) == 1, "Should have hook"
        assert hook_beats[0].position == "early"
        assert hook_beats[0].flexibility == "fixed"

    def test_has_investigation_beat(self, shape: StoryShape) -> None:
        """Test that the investigation beat exists."""
        investigation_beats = [b for b in shape.required_beats if b.type == "investigation"]
        assert len(investigation_beats) == 1, "Should have investigation"
        assert investigation_beats[0].position == "early"

    def test_has_clues_beat(self, shape: StoryShape) -> None:
        """Test that the clues beat exists."""
        clues_beats = [b for b in shape.required_beats if b.type == "clues"]
        assert len(clues_beats) == 1, "Should have clues"
        assert clues_beats[0].position == "middle"

    def test_has_red_herring_beat(self, shape: StoryShape) -> None:
        """Test that the red-herring beat exists."""
        red_herring_beats = [b for b in shape.required_beats if b.type == "red-herring"]
        assert len(red_herring_beats) == 1, "Should have red-herring"
        assert red_herring_beats[0].position == "middle"

    def test_has_revelation_beat(self, shape: StoryShape) -> None:
        """Test that the revelation beat exists."""
        revelation_beats = [b for b in shape.required_beats if b.type == "revelation"]
        assert len(revelation_beats) == 1, "Should have revelation"
        assert revelation_beats[0].position == "late"
        assert revelation_beats[0].flexibility == "fixed"

    def test_has_resolution_beat(self, shape: StoryShape) -> None:
        """Test that the resolution beat exists."""
        resolution_beats = [b for b in shape.required_beats if b.type == "resolution"]
        assert len(resolution_beats) == 1, "Should have resolution"
        assert resolution_beats[0].position == "climax"


class TestMysteryRevealBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "hook" in early_types, "Hook should be in early position"
        assert "investigation" in early_types, "Investigation should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 2, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "clues" in middle_types, "Clues should be in middle position"
        assert "red-herring" in middle_types, "Red-herring should be in middle position"

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
        assert "resolution" in climax_types, "Resolution should be in climax position"


class TestMysteryRevealVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 5, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_unreliable_witness_variation(self, shape: StoryShape) -> None:
        """Test that the unreliable witness variation exists."""
        unreliable = [vp for vp in shape.variation_points if vp.type == "unreliable-witness"]
        assert len(unreliable) == 1, "Should have unreliable-witness variation"

    def test_has_sympathetic_culprit_variation(self, shape: StoryShape) -> None:
        """Test that the sympathetic culprit variation exists."""
        sympathetic = [vp for vp in shape.variation_points if vp.type == "sympathetic-culprit"]
        assert len(sympathetic) == 1, "Should have sympathetic-culprit variation"

    def test_has_false_solution_variation(self, shape: StoryShape) -> None:
        """Test that the false solution variation exists."""
        false_solution = [vp for vp in shape.variation_points if vp.type == "false-solution"]
        assert len(false_solution) == 1, "Should have false-solution variation"


class TestMysteryRevealThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 5, "Should have several themes"
        assert "truth" in shape.themes, "Should include truth theme"
        assert "justice" in shape.themes, "Should include justice theme"
        assert "deception" in shape.themes, "Should include deception theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 4, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 50  # Should be a meaningful description


class TestMysteryRevealCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_victim_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that victim has merge options."""
        victim = next((s for s in shape.character_slots if s.slot == "victim"), None)
        assert victim is not None
        assert len(victim.can_merge_with) > 0, "Victim should have merge options"

    def test_witness_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that witness has merge options."""
        witness = next((s for s in shape.character_slots if s.slot == "witness"), None)
        if witness:
            assert len(witness.can_merge_with) > 0, "Witness should have merge options"


class TestMysteryRevealSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the mystery reveal shape."""
        data = load_mystery_reveal_yaml()
        return StoryShape.model_validate(data)

    def test_crime_scene_used_in_beats(self, shape: StoryShape) -> None:
        """Test that crime-scene has usage mappings."""
        crime_scene = next(s for s in shape.setting_slots if s.slot == "crime-scene")
        assert len(crime_scene.used_in) > 0, "Crime-scene should specify usage"
        assert "hook" in crime_scene.used_in, "Crime-scene should be used in hook"
        assert "investigation" in crime_scene.used_in, "Crime-scene should be used in investigation"

    def test_revelation_space_used_in_revelation(self, shape: StoryShape) -> None:
        """Test that revelation-space is used in revelation-related beats."""
        revelation_space = next(s for s in shape.setting_slots if s.slot == "revelation-space")
        assert "revelation" in revelation_space.used_in, "Revelation-space should be used in revelation"
        assert "resolution" in revelation_space.used_in, "Revelation-space should be used in resolution"

    def test_investigation_hub_used_in_investigation(self, shape: StoryShape) -> None:
        """Test that investigation-hub is used in investigation-related beats."""
        hub = next(s for s in shape.setting_slots if s.slot == "investigation-hub")
        assert "investigation" in hub.used_in, "Investigation-hub should be used in investigation"
        assert "clues" in hub.used_in, "Investigation-hub should be used in clues"
