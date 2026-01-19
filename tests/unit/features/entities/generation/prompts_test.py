"""Tests for shared entity generation prompts."""

from __future__ import annotations

from fabulae.features.entities.generation.prompts import (
    build_beat_prompt,
    build_character_prompt,
    build_fragment_prompt,
    build_scene_prompt,
    build_stanza_prompt,
    build_world_fact_prompt,
)
from fabulae.models import Beat, Character, Fragment, Stanza, WorldFact


class TestBuildCharacterPrompt:
    """Tests for build_character_prompt."""

    def test_minimal_prompt(self) -> None:
        """Test prompt with minimal arguments."""
        prompt = build_character_prompt()
        assert "Create a character for a story" in prompt
        assert '"id":' in prompt
        assert '"name":' in prompt
        assert '"role":' in prompt

    def test_with_premise(self) -> None:
        """Test prompt includes premise."""
        prompt = build_character_prompt(premise="A detective solves mysteries")
        assert "A detective solves mysteries" in prompt
        assert "Story Premise" in prompt

    def test_with_role_hint(self) -> None:
        """Test prompt includes role hint."""
        prompt = build_character_prompt(role_hint="protagonist")
        assert "protagonist" in prompt
        assert "role of protagonist" in prompt

    def test_with_guidance(self) -> None:
        """Test prompt includes user guidance."""
        prompt = build_character_prompt(guidance="a mysterious mentor figure")
        assert "a mysterious mentor figure" in prompt
        assert "User Guidance" in prompt

    def test_with_assigned_id(self) -> None:
        """Test prompt includes assigned ID."""
        prompt = build_character_prompt(assigned_id="character-01")
        assert "character-01" in prompt
        assert "Assigned ID" in prompt
        assert "Use this exact ID" in prompt

    def test_with_existing_characters(self) -> None:
        """Test prompt includes existing characters."""
        existing = [
            Character(id="char-01", name="Alice", role="protagonist"),
            Character(id="char-02", name="Bob", role="antagonist", desire="Power"),
        ]
        prompt = build_character_prompt(existing_characters=existing)
        assert "Alice" in prompt
        assert "Bob" in prompt
        assert "protagonist" in prompt
        assert "Power" in prompt

    def test_with_language(self) -> None:
        """Test prompt includes language instruction."""
        prompt = build_character_prompt(language="German")
        assert "German" in prompt
        assert "Language" in prompt


class TestBuildWorldFactPrompt:
    """Tests for build_world_fact_prompt."""

    def test_minimal_prompt(self) -> None:
        """Test prompt with minimal arguments."""
        prompt = build_world_fact_prompt()
        assert "Create a world-building element" in prompt
        assert '"id":' in prompt
        assert '"type":' in prompt
        assert '"name":' in prompt

    def test_with_fact_type(self) -> None:
        """Test prompt with specific fact type."""
        prompt = build_world_fact_prompt(fact_type="location")
        assert "location" in prompt
        assert "Required Type" in prompt

    def test_with_assigned_id(self) -> None:
        """Test prompt includes assigned ID."""
        prompt = build_world_fact_prompt(assigned_id="location-01")
        assert "location-01" in prompt
        assert "Assigned ID" in prompt

    def test_with_existing_facts(self) -> None:
        """Test prompt includes existing world facts."""
        existing = [
            WorldFact(id="loc-01", type="location", name="Tavern", facts=["Dark interior"]),
        ]
        prompt = build_world_fact_prompt(existing_facts=existing)
        assert "Tavern" in prompt
        assert "location" in prompt


class TestBuildScenePrompt:
    """Tests for build_scene_prompt."""

    def test_minimal_prompt(self) -> None:
        """Test prompt with minimal arguments."""
        prompt = build_scene_prompt()
        assert "Create a scene for a story" in prompt
        assert '"id":' in prompt
        assert '"summary":' in prompt

    def test_with_characters(self) -> None:
        """Test prompt includes available characters."""
        chars = [
            Character(id="char-01", name="Alice", role="protagonist"),
        ]
        prompt = build_scene_prompt(available_characters=chars)
        assert "Alice" in prompt
        assert "char-01" in prompt

    def test_with_locations(self) -> None:
        """Test prompt includes available locations."""
        locs = [
            WorldFact(id="loc-01", type="location", name="Tavern", facts=["Cozy"]),
        ]
        prompt = build_scene_prompt(available_locations=locs)
        assert "Tavern" in prompt
        assert "loc-01" in prompt

    def test_with_beats(self) -> None:
        """Test prompt with beat generation."""
        prompt = build_scene_prompt(include_beats=True, beat_count=3)
        assert "Include 3 beats" in prompt
        assert '"beats"' in prompt


class TestBuildBeatPrompt:
    """Tests for build_beat_prompt."""

    def test_minimal_prompt(self) -> None:
        """Test prompt with minimal arguments."""
        prompt = build_beat_prompt(scene_id="scene-01")
        assert "scene-01" in prompt
        assert '"kind":' in prompt
        assert '"summary":' in prompt

    def test_with_scene_context(self) -> None:
        """Test prompt includes scene context."""
        prompt = build_beat_prompt(
            scene_id="scene-01",
            scene_summary="Hero confronts villain",
        )
        assert "Hero confronts villain" in prompt

    def test_with_existing_beats(self) -> None:
        """Test prompt includes existing beats."""
        existing = [
            Beat(id="beat-01", kind="dialogue", summary="Hero questions villain"),
        ]
        prompt = build_beat_prompt(scene_id="scene-01", existing_beats=existing)
        assert "beat-01" in prompt
        assert "dialogue" in prompt


class TestBuildFragmentPrompt:
    """Tests for build_fragment_prompt."""

    def test_minimal_prompt(self) -> None:
        """Test prompt with minimal arguments."""
        prompt = build_fragment_prompt()
        assert "flash fiction" in prompt
        assert '"content":' in prompt

    def test_with_position(self) -> None:
        """Test prompt includes position info."""
        prompt = build_fragment_prompt(position=2, total_fragments=5)
        assert "3 of 5" in prompt  # 0-indexed position + 1

    def test_with_existing_fragments(self) -> None:
        """Test prompt includes existing fragments."""
        existing = [
            Fragment(id="frag-01", content="The rain fell softly..."),
        ]
        prompt = build_fragment_prompt(existing_fragments=existing)
        assert "frag-01" in prompt


class TestBuildStanzaPrompt:
    """Tests for build_stanza_prompt."""

    def test_minimal_prompt(self) -> None:
        """Test prompt with minimal arguments."""
        prompt = build_stanza_prompt()
        assert "stanza" in prompt
        assert '"lines":' in prompt

    def test_with_line_count(self) -> None:
        """Test prompt includes target line count."""
        prompt = build_stanza_prompt(target_line_count=6)
        assert "6 lines" in prompt

    def test_with_poem_form(self) -> None:
        """Test prompt includes poem form."""
        prompt = build_stanza_prompt(poem_form="sonnet")
        assert "sonnet" in prompt
        assert "Poem Form" in prompt

    def test_with_existing_stanzas(self) -> None:
        """Test prompt includes existing stanzas."""
        existing = [
            Stanza(id="stanza-01", lines=["First line of verse"]),
        ]
        prompt = build_stanza_prompt(existing_stanzas=existing)
        assert "stanza-01" in prompt
