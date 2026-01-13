"""Tests for Story Shape models."""

from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from fabulae.models import (
    CharacterSlot,
    RequiredBeat,
    SettingSlot,
    StoryShape,
    VariationPoint,
)


class TestCharacterSlot:
    """Tests for CharacterSlot model."""

    def test_character_slot_required_fields(self) -> None:
        """Test CharacterSlot validates required fields."""
        slot = CharacterSlot(
            slot="hero",
            needs="A brave protagonist who drives the story",
        )
        assert slot.slot == "hero"
        assert slot.needs == "A brave protagonist who drives the story"
        assert slot.can_merge_with == []
        assert slot.optional is False

    def test_character_slot_with_merge_options(self) -> None:
        """Test CharacterSlot with can_merge_with list."""
        slot = CharacterSlot(
            slot="mentor",
            needs="A wise guide",
            can_merge_with=["threshold-guardian", "herald"],
            optional=True,
        )
        assert slot.can_merge_with == ["threshold-guardian", "herald"]
        assert slot.optional is True

    def test_character_slot_missing_slot_raises_error(self) -> None:
        """Test CharacterSlot requires slot field."""
        with pytest.raises(ValidationError):
            CharacterSlot(needs="Some needs")  # type: ignore[call-arg]

    def test_character_slot_empty_slot_raises_error(self) -> None:
        """Test CharacterSlot requires non-empty slot."""
        with pytest.raises(ValidationError):
            CharacterSlot(slot="", needs="Some needs")

    def test_character_slot_missing_needs_raises_error(self) -> None:
        """Test CharacterSlot requires needs field."""
        with pytest.raises(ValidationError):
            CharacterSlot(slot="hero")  # type: ignore[call-arg]


class TestSettingSlot:
    """Tests for SettingSlot model."""

    def test_setting_slot_required_fields(self) -> None:
        """Test SettingSlot validates required fields."""
        slot = SettingSlot(
            slot="ordinary-world",
            needs="The hero's familiar everyday environment",
        )
        assert slot.slot == "ordinary-world"
        assert slot.needs == "The hero's familiar everyday environment"
        assert slot.used_in == []
        assert slot.optional is False

    def test_setting_slot_with_usage_list(self) -> None:
        """Test SettingSlot with used_in list."""
        slot = SettingSlot(
            slot="special-world",
            needs="The unfamiliar realm of adventure",
            used_in=["threshold", "tests", "ordeal", "return"],
            optional=False,
        )
        assert slot.used_in == ["threshold", "tests", "ordeal", "return"]

    def test_setting_slot_optional(self) -> None:
        """Test SettingSlot optional field."""
        slot = SettingSlot(
            slot="innermost-cave",
            needs="The most dangerous place",
            optional=True,
        )
        assert slot.optional is True

    def test_setting_slot_missing_slot_raises_error(self) -> None:
        """Test SettingSlot requires slot field."""
        with pytest.raises(ValidationError):
            SettingSlot(needs="Some needs")  # type: ignore[call-arg]

    def test_setting_slot_empty_needs_raises_error(self) -> None:
        """Test SettingSlot requires non-empty needs."""
        with pytest.raises(ValidationError):
            SettingSlot(slot="location", needs="")


class TestRequiredBeat:
    """Tests for RequiredBeat model."""

    def test_required_beat_minimal(self) -> None:
        """Test RequiredBeat with minimal fields."""
        beat = RequiredBeat(
            type="call-to-adventure",
            description="The hero receives a challenge or quest",
        )
        assert beat.type == "call-to-adventure"
        assert beat.description == "The hero receives a challenge or quest"
        assert beat.position == "anywhere"
        assert beat.flexibility == "flexible"

    def test_required_beat_position_literals(self) -> None:
        """Test RequiredBeat position accepts valid literals."""
        positions: list[Any] = ["early", "middle", "late", "climax", "anywhere"]
        for position in positions:
            beat = RequiredBeat(
                type="test",
                description="Test beat",
                position=position,
            )
            assert beat.position == position

    def test_required_beat_invalid_position_raises_error(self) -> None:
        """Test RequiredBeat rejects invalid position."""
        with pytest.raises(ValidationError):
            RequiredBeat(
                type="test",
                description="Test beat",
                position="invalid-position",  # type: ignore[arg-type]
            )

    def test_required_beat_flexibility_literals(self) -> None:
        """Test RequiredBeat flexibility accepts valid literals."""
        flexibilities: list[Any] = ["fixed", "flexible", "very-flexible"]
        for flexibility in flexibilities:
            beat = RequiredBeat(
                type="test",
                description="Test beat",
                flexibility=flexibility,
            )
            assert beat.flexibility == flexibility

    def test_required_beat_invalid_flexibility_raises_error(self) -> None:
        """Test RequiredBeat rejects invalid flexibility."""
        with pytest.raises(ValidationError):
            RequiredBeat(
                type="test",
                description="Test beat",
                flexibility="super-flexible",  # type: ignore[arg-type]
            )

    def test_required_beat_full_specification(self) -> None:
        """Test RequiredBeat with all fields specified."""
        beat = RequiredBeat(
            type="ordeal",
            description="The hero faces their greatest fear",
            position="late",
            flexibility="fixed",
        )
        assert beat.type == "ordeal"
        assert beat.description == "The hero faces their greatest fear"
        assert beat.position == "late"
        assert beat.flexibility == "fixed"


class TestVariationPoint:
    """Tests for VariationPoint model."""

    def test_variation_point_minimal(self) -> None:
        """Test VariationPoint with minimal fields."""
        vp = VariationPoint(
            type="complication",
            description="An unexpected obstacle appears",
            probability=0.5,
        )
        assert vp.type == "complication"
        assert vp.description == "An unexpected obstacle appears"
        assert vp.probability == 0.5
        assert vp.position == "anywhere"

    def test_variation_point_probability_bounds(self) -> None:
        """Test VariationPoint enforces probability bounds."""
        # Valid probabilities
        for prob in [0.0, 0.25, 0.5, 0.75, 1.0]:
            vp = VariationPoint(
                type="test",
                description="Test variation",
                probability=prob,
            )
            assert vp.probability == prob

    def test_variation_point_probability_too_low_raises_error(self) -> None:
        """Test VariationPoint rejects probability below 0.0."""
        with pytest.raises(ValidationError):
            VariationPoint(
                type="test",
                description="Test variation",
                probability=-0.1,
            )

    def test_variation_point_probability_too_high_raises_error(self) -> None:
        """Test VariationPoint rejects probability above 1.0."""
        with pytest.raises(ValidationError):
            VariationPoint(
                type="test",
                description="Test variation",
                probability=1.1,
            )

    def test_variation_point_position_literals(self) -> None:
        """Test VariationPoint position accepts valid literals."""
        positions: list[Any] = ["early", "middle", "late", "climax", "anywhere"]
        for position in positions:
            vp = VariationPoint(
                type="test",
                description="Test variation",
                probability=0.5,
                position=position,
            )
            assert vp.position == position

    def test_variation_point_full_specification(self) -> None:
        """Test VariationPoint with all fields specified."""
        vp = VariationPoint(
            type="character-moment",
            description="A character reveals inner conflict",
            probability=0.8,
            position="middle",
        )
        assert vp.type == "character-moment"
        assert vp.description == "A character reveals inner conflict"
        assert vp.probability == 0.8
        assert vp.position == "middle"


class TestStoryShape:
    """Tests for StoryShape model."""

    def test_story_shape_minimal(self) -> None:
        """Test StoryShape with minimal required fields."""
        shape = StoryShape(
            id="test-shape",
            name="Test Shape",
            description="A simple test story shape",
        )
        assert shape.id == "test-shape"
        assert shape.name == "Test Shape"
        assert shape.description == "A simple test story shape"
        assert shape.character_slots == []
        assert shape.setting_slots == []
        assert shape.required_beats == []
        assert shape.variation_points == []
        assert shape.themes == []
        assert shape.motifs == []
        assert shape.tone is None

    def test_story_shape_invalid_id_raises_error(self) -> None:
        """Test StoryShape rejects invalid ID format."""
        with pytest.raises(ValidationError):
            StoryShape(
                id="Test Shape",  # spaces not allowed
                name="Test Shape",
                description="Description",
            )

    def test_story_shape_full_example(self) -> None:
        """Test StoryShape with full example data."""
        shape = StoryShape(
            id="heros-journey",
            name="Hero's Journey",
            description="The classic monomyth structure",
            character_slots=[
                CharacterSlot(
                    slot="hero",
                    needs="A protagonist who transforms through trials",
                ),
                CharacterSlot(
                    slot="mentor",
                    needs="A wise guide who aids the hero",
                    optional=True,
                ),
            ],
            setting_slots=[
                SettingSlot(
                    slot="ordinary-world",
                    needs="The hero's familiar environment",
                    used_in=["call"],
                ),
                SettingSlot(
                    slot="special-world",
                    needs="The realm of adventure",
                    used_in=["threshold", "tests", "ordeal"],
                ),
            ],
            required_beats=[
                RequiredBeat(
                    type="call-to-adventure",
                    description="The hero receives a quest",
                    position="early",
                    flexibility="flexible",
                ),
                RequiredBeat(
                    type="ordeal",
                    description="The hero faces their greatest fear",
                    position="late",
                    flexibility="fixed",
                ),
            ],
            variation_points=[
                VariationPoint(
                    type="refusal",
                    description="The hero initially refuses the call",
                    probability=0.6,
                    position="early",
                ),
                VariationPoint(
                    type="false-victory",
                    description="A temporary triumph before final ordeal",
                    probability=0.4,
                    position="middle",
                ),
            ],
            themes=["transformation", "courage", "sacrifice"],
            motifs=["threshold-crossing", "death-and-rebirth"],
            tone="epic and mythic",
        )

        assert shape.id == "heros-journey"
        assert shape.name == "Hero's Journey"
        assert len(shape.character_slots) == 2
        assert len(shape.setting_slots) == 2
        assert len(shape.required_beats) == 2
        assert len(shape.variation_points) == 2
        assert shape.themes == ["transformation", "courage", "sacrifice"]
        assert shape.motifs == ["threshold-crossing", "death-and-rebirth"]
        assert shape.tone == "epic and mythic"

        # Verify nested models
        assert shape.character_slots[0].slot == "hero"
        assert shape.character_slots[1].optional is True
        assert shape.setting_slots[0].used_in == ["call"]
        assert shape.required_beats[0].position == "early"
        assert shape.variation_points[0].probability == 0.6

    def test_story_shape_serialization(self) -> None:
        """Test StoryShape can be serialized to dict."""
        shape = StoryShape(
            id="betrayal-arc",
            name="Betrayal Arc",
            description="A story of trust and betrayal",
            character_slots=[
                CharacterSlot(
                    slot="protagonist",
                    needs="Someone capable of deep trust",
                ),
                CharacterSlot(
                    slot="betrayer",
                    needs="Someone with hidden motives",
                ),
            ],
            required_beats=[
                RequiredBeat(
                    type="trust-established",
                    description="Trust is built between characters",
                    position="early",
                ),
                RequiredBeat(
                    type="revelation",
                    description="The betrayal is revealed",
                    position="climax",
                ),
            ],
            themes=["trust", "deception"],
        )

        data = shape.model_dump(exclude_none=True)

        assert data["id"] == "betrayal-arc"
        assert data["name"] == "Betrayal Arc"
        assert len(data["character_slots"]) == 2
        assert data["character_slots"][0]["slot"] == "protagonist"
        assert len(data["required_beats"]) == 2
        assert data["required_beats"][0]["type"] == "trust-established"
        assert data["themes"] == ["trust", "deception"]

    def test_story_shape_deserialization(self) -> None:
        """Test StoryShape can be deserialized from dict."""
        data = {
            "id": "coming-of-age",
            "name": "Coming of Age",
            "description": "A journey from innocence to maturity",
            "character_slots": [
                {
                    "slot": "young-protagonist",
                    "needs": "An inexperienced character ready to grow",
                    "optional": False,
                }
            ],
            "setting_slots": [
                {
                    "slot": "familiar-world",
                    "needs": "The protagonist's sheltered environment",
                    "used_in": ["innocence"],
                }
            ],
            "required_beats": [
                {
                    "type": "innocence",
                    "description": "The protagonist's naive beginning",
                    "position": "early",
                    "flexibility": "flexible",
                }
            ],
            "variation_points": [
                {
                    "type": "mentor-death",
                    "description": "Loss of guidance figure",
                    "probability": 0.5,
                    "position": "middle",
                }
            ],
            "themes": ["growth", "loss-of-innocence"],
            "motifs": ["first-experience", "rite-of-passage"],
            "tone": "bittersweet",
        }

        shape = StoryShape.model_validate(data)

        assert shape.id == "coming-of-age"
        assert shape.name == "Coming of Age"
        assert len(shape.character_slots) == 1
        assert shape.character_slots[0].slot == "young-protagonist"
        assert len(shape.setting_slots) == 1
        assert len(shape.required_beats) == 1
        assert len(shape.variation_points) == 1
        assert shape.themes == ["growth", "loss-of-innocence"]
        assert shape.tone == "bittersweet"

    def test_story_shape_yaml_round_trip(self) -> None:
        """Test StoryShape can round-trip through YAML."""
        original = StoryShape(
            id="mystery-reveal",
            name="Mystery Reveal",
            description="A mystery that unfolds through investigation",
            character_slots=[
                CharacterSlot(
                    slot="detective",
                    needs="An investigator who seeks truth",
                ),
                CharacterSlot(
                    slot="suspect",
                    needs="Someone who may be guilty",
                    can_merge_with=["victim", "witness"],
                ),
            ],
            setting_slots=[
                SettingSlot(
                    slot="crime-scene",
                    needs="The location where the mystery began",
                    used_in=["hook", "investigation"],
                )
            ],
            required_beats=[
                RequiredBeat(
                    type="hook",
                    description="The mystery is introduced",
                    position="early",
                    flexibility="fixed",
                ),
                RequiredBeat(
                    type="clues",
                    description="Evidence is gathered",
                    position="middle",
                    flexibility="very-flexible",
                ),
                RequiredBeat(
                    type="revelation",
                    description="The truth is revealed",
                    position="climax",
                    flexibility="fixed",
                ),
            ],
            variation_points=[
                VariationPoint(
                    type="red-herring",
                    description="A false lead misdirects the investigation",
                    probability=0.7,
                    position="middle",
                )
            ],
            themes=["truth", "justice", "deception"],
            motifs=["investigation", "revelation"],
            tone="suspenseful and cerebral",
        )

        # Serialize to YAML
        yaml_str = yaml.dump(
            original.model_dump(exclude_none=True),
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

        # Deserialize from YAML
        data = yaml.safe_load(yaml_str)
        restored = StoryShape.model_validate(data)

        # Verify round-trip
        assert restored.id == original.id
        assert restored.name == original.name
        assert restored.description == original.description
        assert len(restored.character_slots) == len(original.character_slots)
        assert len(restored.setting_slots) == len(original.setting_slots)
        assert len(restored.required_beats) == len(original.required_beats)
        assert len(restored.variation_points) == len(original.variation_points)
        assert restored.themes == original.themes
        assert restored.motifs == original.motifs
        assert restored.tone == original.tone

        # Verify nested model details
        assert restored.character_slots[1].can_merge_with == ["victim", "witness"]
        assert restored.required_beats[1].flexibility == "very-flexible"
        assert restored.variation_points[0].probability == 0.7
