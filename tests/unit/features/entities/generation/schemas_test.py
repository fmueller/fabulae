"""Tests for shared entity generation schemas."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from fabulae.features.entities.generation.schemas import (
    BeatSuggestionOutput,
    CharacterSuggestionOutput,
    FragmentSuggestionOutput,
    SceneSuggestionOutput,
    StanzaSuggestionOutput,
    WorldFactSuggestionOutput,
)


class TestCharacterSuggestionOutput:
    """Tests for CharacterSuggestionOutput schema."""

    def test_valid_character(self) -> None:
        """Test valid character data parses correctly."""
        data = {
            "id": "detective-chen",
            "name": "Detective Chen",
            "role": "protagonist",
            "desire": "To solve the case",
            "need": "To let go of the past",
            "flaw": "Obsessive",
            "secret": "Lost her partner years ago",
            "traits": ["determined", "methodical"],
        }
        char = CharacterSuggestionOutput.model_validate(data)
        assert char.id == "detective-chen"
        assert char.name == "Detective Chen"
        assert char.role == "protagonist"
        assert char.traits == ["determined", "methodical"]

    def test_minimal_character(self) -> None:
        """Test character with only required fields."""
        data = {"id": "char-01", "name": "Test Character"}
        char = CharacterSuggestionOutput.model_validate(data)
        assert char.id == "char-01"
        assert char.name == "Test Character"
        assert char.role is None
        assert char.traits == []

    def test_whitespace_stripping(self) -> None:
        """Test that whitespace is stripped from string fields."""
        data = {
            "id": "char-01",
            "name": "  Test Character  ",
            "role": "  protagonist  ",
            "desire": "  To win  ",
        }
        char = CharacterSuggestionOutput.model_validate(data)
        assert char.name == "Test Character"
        assert char.role == "protagonist"
        assert char.desire == "To win"


class TestWorldFactSuggestionOutput:
    """Tests for WorldFactSuggestionOutput schema."""

    def test_valid_location(self) -> None:
        """Test valid location data parses correctly."""
        data = {
            "id": "tavern-golden",
            "type": "location",
            "name": "The Golden Tankard",
            "facts": ["Smoky atmosphere", "Worn wooden furniture"],
        }
        fact = WorldFactSuggestionOutput.model_validate(data)
        assert fact.id == "tavern-golden"
        assert fact.type == "location"
        assert fact.name == "The Golden Tankard"
        assert len(fact.facts) == 2

    def test_valid_types(self) -> None:
        """Test all valid types parse correctly."""
        for fact_type in ["location", "culture", "history", "rule", "object"]:
            data = {"id": "fact-01", "type": fact_type, "name": "Test"}
            fact = WorldFactSuggestionOutput.model_validate(data)
            assert fact.type == fact_type

    def test_invalid_type_rejected(self) -> None:
        """Test invalid type is rejected."""
        data = {"id": "fact-01", "type": "invalid", "name": "Test"}
        with pytest.raises(ValidationError):
            WorldFactSuggestionOutput.model_validate(data)


class TestBeatSuggestionOutput:
    """Tests for BeatSuggestionOutput schema."""

    def test_valid_beat(self) -> None:
        """Test valid beat data parses correctly."""
        data = {
            "id": "beat-confrontation",
            "kind": "action",
            "summary": "Hero draws weapon",
            "goal": "Stop the villain",
            "conflict": "Villain is stronger",
            "outcome": "Hero is wounded",
        }
        beat = BeatSuggestionOutput.model_validate(data)
        assert beat.id == "beat-confrontation"
        assert beat.kind == "action"
        assert beat.summary == "Hero draws weapon"

    def test_minimal_beat(self) -> None:
        """Test beat with only required fields."""
        data = {"id": "beat-01", "kind": "dialogue"}
        beat = BeatSuggestionOutput.model_validate(data)
        assert beat.id == "beat-01"
        assert beat.kind == "dialogue"
        assert beat.summary is None


class TestSceneSuggestionOutput:
    """Tests for SceneSuggestionOutput schema."""

    def test_valid_scene(self) -> None:
        """Test valid scene data parses correctly."""
        data = {
            "id": "scene-confrontation",
            "summary": "Hero faces villain in the throne room",
            "goal": "Defeat the villain",
            "conflict": "Villain has hostages",
            "outcome": "Villain escapes",
            "characters": ["hero-01", "villain-01"],
            "location": "throne-room",
            "time": "midnight",
        }
        scene = SceneSuggestionOutput.model_validate(data)
        assert scene.id == "scene-confrontation"
        assert scene.characters == ["hero-01", "villain-01"]
        assert scene.location == "throne-room"

    def test_scene_with_beats(self) -> None:
        """Test scene with nested beats."""
        data = {
            "id": "scene-01",
            "summary": "Test scene",
            "beats": [
                {"id": "beat-01", "kind": "dialogue", "summary": "Characters talk"},
                {"id": "beat-02", "kind": "action", "summary": "Action happens"},
            ],
        }
        scene = SceneSuggestionOutput.model_validate(data)
        assert len(scene.beats) == 2
        assert scene.beats[0].kind == "dialogue"


class TestFragmentSuggestionOutput:
    """Tests for FragmentSuggestionOutput schema."""

    def test_valid_fragment(self) -> None:
        """Test valid fragment data parses correctly."""
        data = {
            "id": "fragment-03",
            "content": "The rain fell softly on the cobblestones.",
            "target_words": 100,
            "notes": "Atmospheric opening",
        }
        fragment = FragmentSuggestionOutput.model_validate(data)
        assert fragment.id == "fragment-03"
        assert fragment.content == "The rain fell softly on the cobblestones."
        assert fragment.target_words == 100

    def test_fragment_requires_content(self) -> None:
        """Test that content is required."""
        data = {"id": "fragment-01"}
        with pytest.raises(ValidationError):
            FragmentSuggestionOutput.model_validate(data)


class TestStanzaSuggestionOutput:
    """Tests for StanzaSuggestionOutput schema."""

    def test_valid_stanza(self) -> None:
        """Test valid stanza data parses correctly."""
        data = {
            "id": "stanza-01",
            "lines": [
                "In autumn's golden light we stand",
                "With crimson leaves beneath our feet",
                "The wind whispers through the land",
                "Where memories and seasons meet",
            ],
            "meter": "iambic tetrameter",
            "rhyme_scheme": "ABAB",
        }
        stanza = StanzaSuggestionOutput.model_validate(data)
        assert stanza.id == "stanza-01"
        assert len(stanza.lines) == 4
        assert stanza.meter == "iambic tetrameter"
        assert stanza.rhyme_scheme == "ABAB"

    def test_minimal_stanza(self) -> None:
        """Test stanza with only required fields."""
        data = {"id": "stanza-01"}
        stanza = StanzaSuggestionOutput.model_validate(data)
        assert stanza.id == "stanza-01"
        assert stanza.lines == []
        assert stanza.meter is None
