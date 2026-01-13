"""Tests for Forbidden Knowledge story shape file."""

from importlib.resources import files
from pathlib import Path

import pytest
import yaml

from fabulae.models import StoryShape


def get_story_shapes_path() -> Path:
    """Get the path to the story shapes directory."""
    data_files = files("fabulae.data")
    return Path(str(data_files)) / "story_shapes"


def load_forbidden_knowledge_yaml() -> dict[str, object]:
    """Load the forbidden knowledge YAML file and return raw data."""
    shape_path = get_story_shapes_path() / "forbidden-knowledge.yml"
    with shape_path.open("r", encoding="utf-8") as f:
        data: dict[str, object] = yaml.safe_load(f)
        return data


class TestForbiddenKnowledgeYamlLoads:
    """Tests that the YAML file loads without error."""

    def test_yaml_file_exists(self) -> None:
        """Test that the forbidden knowledge YAML file exists."""
        shape_path = get_story_shapes_path() / "forbidden-knowledge.yml"
        assert shape_path.exists(), f"Expected file at {shape_path}"

    def test_yaml_loads_without_error(self) -> None:
        """Test that the YAML file parses correctly."""
        data = load_forbidden_knowledge_yaml()
        assert isinstance(data, dict)
        assert len(data) > 0


class TestForbiddenKnowledgeValidatesAgainstModel:
    """Tests that the YAML validates against the StoryShape model."""

    def test_validates_against_story_shape_model(self) -> None:
        """Test that the YAML data validates as a StoryShape."""
        data = load_forbidden_knowledge_yaml()
        shape = StoryShape.model_validate(data)
        assert shape is not None
        assert isinstance(shape, StoryShape)

    def test_has_correct_id(self) -> None:
        """Test that the shape has the expected ID."""
        data = load_forbidden_knowledge_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.id == "forbidden-knowledge"

    def test_has_correct_name(self) -> None:
        """Test that the shape has the expected name."""
        data = load_forbidden_knowledge_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.name == "Forbidden Knowledge"

    def test_has_description(self) -> None:
        """Test that the shape has a non-empty description."""
        data = load_forbidden_knowledge_yaml()
        shape = StoryShape.model_validate(data)
        assert shape.description
        assert len(shape.description) > 50  # Should be substantial

    def test_can_round_trip_through_yaml(self) -> None:
        """Test that the shape can be serialized and deserialized."""
        data = load_forbidden_knowledge_yaml()
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


class TestForbiddenKnowledgeRequiredCharacterSlots:
    """Tests that all required character slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_has_character_slots(self, shape: StoryShape) -> None:
        """Test that the shape has character slots defined."""
        assert len(shape.character_slots) >= 2, "Should have at least seeker and guardian"

    def test_has_seeker_character_slot(self, shape: StoryShape) -> None:
        """Test that the seeker character slot exists."""
        seeker_slots = [s for s in shape.character_slots if s.slot == "seeker"]
        assert len(seeker_slots) == 1, "Should have exactly one seeker slot"
        assert seeker_slots[0].optional is False, "Seeker should be required"

    def test_has_guardian_character_slot(self, shape: StoryShape) -> None:
        """Test that the guardian character slot exists."""
        guardian_slots = [s for s in shape.character_slots if s.slot == "guardian"]
        assert len(guardian_slots) == 1, "Should have exactly one guardian slot"
        assert guardian_slots[0].optional is False, "Guardian should be required"

    def test_has_predecessor_character_slot(self, shape: StoryShape) -> None:
        """Test that the predecessor character slot exists."""
        predecessor_slots = [s for s in shape.character_slots if s.slot == "predecessor"]
        assert len(predecessor_slots) == 1, "Should have a predecessor slot"
        assert predecessor_slots[0].optional is True, "Predecessor should be optional"

    def test_has_enabler_character_slot(self, shape: StoryShape) -> None:
        """Test that the enabler character slot exists."""
        enabler_slots = [s for s in shape.character_slots if s.slot == "enabler"]
        assert len(enabler_slots) == 1, "Should have an enabler slot"
        assert enabler_slots[0].optional is True, "Enabler should be optional"

    def test_has_tempter_character_slot(self, shape: StoryShape) -> None:
        """Test that the tempter character slot exists."""
        tempter_slots = [s for s in shape.character_slots if s.slot == "tempter"]
        assert len(tempter_slots) == 1, "Should have a tempter slot"
        assert tempter_slots[0].optional is True, "Tempter should be optional"

    def test_all_character_slots_have_needs(self, shape: StoryShape) -> None:
        """Test that all character slots have meaningful needs descriptions."""
        for slot in shape.character_slots:
            assert slot.needs, f"Slot {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Slot {slot.slot} needs should be descriptive"


class TestForbiddenKnowledgeRequiredSettingSlots:
    """Tests that all required setting slots are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_has_setting_slots(self, shape: StoryShape) -> None:
        """Test that the shape has setting slots defined."""
        assert len(shape.setting_slots) >= 3, "Should have key locations"

    def test_has_threshold_setting(self, shape: StoryShape) -> None:
        """Test that the threshold setting exists."""
        threshold = [s for s in shape.setting_slots if s.slot == "threshold"]
        assert len(threshold) == 1, "Should have threshold"
        assert threshold[0].optional is False, "Threshold should be required"

    def test_has_source_setting(self, shape: StoryShape) -> None:
        """Test that the source setting exists."""
        source = [s for s in shape.setting_slots if s.slot == "source"]
        assert len(source) == 1, "Should have source"
        assert source[0].optional is False, "Source should be required"

    def test_has_crucible_setting(self, shape: StoryShape) -> None:
        """Test that the crucible setting exists."""
        crucible = [s for s in shape.setting_slots if s.slot == "crucible"]
        assert len(crucible) == 1, "Should have crucible"
        assert crucible[0].optional is False, "Crucible should be required"

    def test_has_sanctuary_setting(self, shape: StoryShape) -> None:
        """Test that the sanctuary setting exists."""
        sanctuary = [s for s in shape.setting_slots if s.slot == "sanctuary"]
        assert len(sanctuary) == 1, "Should have sanctuary"
        assert sanctuary[0].optional is True, "Sanctuary should be optional"

    def test_all_settings_have_needs(self, shape: StoryShape) -> None:
        """Test that all setting slots have meaningful needs descriptions."""
        for slot in shape.setting_slots:
            assert slot.needs, f"Setting {slot.slot} should have needs"
            assert len(slot.needs) > 20, f"Setting {slot.slot} needs should be descriptive"


class TestForbiddenKnowledgeRequiredBeats:
    """Tests that all required beats are present and valid."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_has_required_beats(self, shape: StoryShape) -> None:
        """Test that the shape has required beats (6 expected)."""
        assert len(shape.required_beats) == 6, f"Expected 6 required beats, got {len(shape.required_beats)}"

    def test_has_curiosity_beat(self, shape: StoryShape) -> None:
        """Test that the curiosity beat exists."""
        curiosity_beats = [b for b in shape.required_beats if b.type == "curiosity"]
        assert len(curiosity_beats) == 1, "Should have curiosity"
        assert curiosity_beats[0].position == "early"

    def test_has_discovery_beat(self, shape: StoryShape) -> None:
        """Test that the discovery beat exists."""
        discovery_beats = [b for b in shape.required_beats if b.type == "discovery"]
        assert len(discovery_beats) == 1, "Should have discovery"
        assert discovery_beats[0].position == "early"

    def test_has_obsession_beat(self, shape: StoryShape) -> None:
        """Test that the obsession beat exists."""
        obsession_beats = [b for b in shape.required_beats if b.type == "obsession"]
        assert len(obsession_beats) == 1, "Should have obsession"
        assert obsession_beats[0].position == "middle"

    def test_has_corruption_beat(self, shape: StoryShape) -> None:
        """Test that the corruption beat exists."""
        corruption_beats = [b for b in shape.required_beats if b.type == "corruption"]
        assert len(corruption_beats) == 1, "Should have corruption"
        assert corruption_beats[0].position == "middle"

    def test_has_choice_beat(self, shape: StoryShape) -> None:
        """Test that the choice beat exists."""
        choice_beats = [b for b in shape.required_beats if b.type == "choice"]
        assert len(choice_beats) == 1, "Should have choice"
        assert choice_beats[0].position == "late"
        assert choice_beats[0].flexibility == "fixed"

    def test_has_consequence_beat(self, shape: StoryShape) -> None:
        """Test that the consequence beat exists."""
        consequence_beats = [b for b in shape.required_beats if b.type == "consequence"]
        assert len(consequence_beats) == 1, "Should have consequence"
        assert consequence_beats[0].position == "climax"


class TestForbiddenKnowledgeBeatPositions:
    """Tests that beats have appropriate position assignments."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_early_beats_come_first(self, shape: StoryShape) -> None:
        """Test that early beats exist for story setup."""
        early_beats = [b for b in shape.required_beats if b.position == "early"]
        assert len(early_beats) >= 1, "Should have early beats"

        early_types = {b.type for b in early_beats}
        assert "curiosity" in early_types, "Curiosity should be in early position"
        assert "discovery" in early_types, "Discovery should be in early position"

    def test_middle_beats_for_development(self, shape: StoryShape) -> None:
        """Test that middle beats exist for story development."""
        middle_beats = [b for b in shape.required_beats if b.position == "middle"]
        assert len(middle_beats) >= 1, "Should have middle beats for development"

        middle_types = {b.type for b in middle_beats}
        assert "obsession" in middle_types, "Obsession should be in middle position"
        assert "corruption" in middle_types, "Corruption should be in middle position"

    def test_late_beats_for_crisis(self, shape: StoryShape) -> None:
        """Test that late beats exist for story crisis."""
        late_beats = [b for b in shape.required_beats if b.position == "late"]
        assert len(late_beats) >= 1, "Should have late beats for crisis"

        late_types = {b.type for b in late_beats}
        assert "choice" in late_types, "Choice should be in late position"

    def test_climax_beats_for_resolution(self, shape: StoryShape) -> None:
        """Test that climax beats exist for story resolution."""
        climax_beats = [b for b in shape.required_beats if b.position == "climax"]
        assert len(climax_beats) >= 1, "Should have climax beats"

        climax_types = {b.type for b in climax_beats}
        assert "consequence" in climax_types, "Consequence should be in climax position"


class TestForbiddenKnowledgeVariationPoints:
    """Tests for variation points."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_has_variation_points(self, shape: StoryShape) -> None:
        """Test that the shape has variation points defined."""
        assert len(shape.variation_points) >= 5, "Should have several variation points"

    def test_variation_points_have_valid_probabilities(self, shape: StoryShape) -> None:
        """Test that all variation points have valid probability values."""
        for vp in shape.variation_points:
            assert 0.0 <= vp.probability <= 1.0, f"{vp.type} has invalid probability"

    def test_has_knowledge_as_entity_variation(self, shape: StoryShape) -> None:
        """Test that the knowledge-as-entity variation exists."""
        entity_variations = [vp for vp in shape.variation_points if vp.type == "knowledge-as-entity"]
        assert len(entity_variations) == 1, "Should have knowledge-as-entity variation"

    def test_has_redemptive_sacrifice_variation(self, shape: StoryShape) -> None:
        """Test that the redemptive-sacrifice variation exists."""
        sacrifice_variations = [vp for vp in shape.variation_points if vp.type == "redemptive-sacrifice"]
        assert len(sacrifice_variations) == 1, "Should have redemptive-sacrifice variation"

    def test_has_cycle_continuation_variation(self, shape: StoryShape) -> None:
        """Test that the cycle-continuation variation exists."""
        cycle_variations = [vp for vp in shape.variation_points if vp.type == "cycle-continuation"]
        assert len(cycle_variations) == 1, "Should have cycle-continuation variation"


class TestForbiddenKnowledgeThematicElements:
    """Tests for themes, motifs, and tone."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_has_themes(self, shape: StoryShape) -> None:
        """Test that the shape has themes defined."""
        assert len(shape.themes) >= 5, "Should have several themes"
        assert "knowledge" in shape.themes, "Should include knowledge theme"
        assert "corruption" in shape.themes, "Should include corruption theme"
        assert "transformation" in shape.themes, "Should include transformation theme"
        assert "hubris" in shape.themes, "Should include hubris theme"

    def test_has_motifs(self, shape: StoryShape) -> None:
        """Test that the shape has motifs defined."""
        assert len(shape.motifs) >= 5, "Should have several motifs"

    def test_has_tone(self, shape: StoryShape) -> None:
        """Test that the shape has a tone defined."""
        assert shape.tone is not None
        assert len(shape.tone) > 10  # Should be a meaningful description


class TestForbiddenKnowledgeCharacterSlotRelationships:
    """Tests that character slots have appropriate relationships."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_guardian_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that guardian has merge options."""
        guardian = next((s for s in shape.character_slots if s.slot == "guardian"), None)
        if guardian:
            assert len(guardian.can_merge_with) > 0, "Guardian should have merge options"

    def test_enabler_can_merge_with_others(self, shape: StoryShape) -> None:
        """Test that enabler has merge options."""
        enabler = next((s for s in shape.character_slots if s.slot == "enabler"), None)
        if enabler:
            assert len(enabler.can_merge_with) > 0, "Enabler should have merge options"


class TestForbiddenKnowledgeSettingSlotUsage:
    """Tests that setting slots have appropriate usage mappings."""

    @pytest.fixture
    def shape(self) -> StoryShape:
        """Load the forbidden knowledge shape."""
        data = load_forbidden_knowledge_yaml()
        return StoryShape.model_validate(data)

    def test_threshold_used_in_beats(self, shape: StoryShape) -> None:
        """Test that threshold has usage mappings."""
        threshold = next(s for s in shape.setting_slots if s.slot == "threshold")
        assert len(threshold.used_in) > 0, "Threshold should specify usage"
        assert "curiosity" in threshold.used_in or "discovery" in threshold.used_in, (
            "Threshold should be used in early beats"
        )

    def test_source_used_in_key_beats(self, shape: StoryShape) -> None:
        """Test that source is used in key beats."""
        source = next(s for s in shape.setting_slots if s.slot == "source")
        assert "discovery" in source.used_in, "Source should be used in discovery"
        assert "obsession" in source.used_in, "Source should be used in obsession"

    def test_crucible_used_in_climax_beats(self, shape: StoryShape) -> None:
        """Test that crucible is used in climax-related beats."""
        crucible = next(s for s in shape.setting_slots if s.slot == "crucible")
        assert "choice" in crucible.used_in or "consequence" in crucible.used_in, (
            "Crucible should be used in late/climax beats"
        )
