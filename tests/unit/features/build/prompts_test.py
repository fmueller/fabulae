"""Unit tests for build prompt builders."""

from __future__ import annotations

from fabulae.features.build.prompts import build_continuity_prompt, build_continuity_system_prompt


class TestContinuityPrompts:
    """Tests for continuity summary prompt content."""

    def test_system_prompt_mentions_dialogue_threads(self) -> None:
        """System prompt instructs LLM to capture open dialogue threads."""
        prompt = build_continuity_system_prompt()
        assert "dialogue thread" in prompt.lower()

    def test_system_prompt_mentions_emotional_states(self) -> None:
        """System prompt instructs LLM to capture character emotional states."""
        prompt = build_continuity_system_prompt()
        assert "emotional state" in prompt.lower()

    def test_system_prompt_mentions_all_three_fields(self) -> None:
        """System prompt asks for summary, open_threads, and emotional_states."""
        prompt = build_continuity_system_prompt()
        assert "summary" in prompt.lower()
        assert "open_threads" in prompt.lower()
        assert "emotional_states" in prompt.lower()

    def test_user_prompt_includes_scene_content(self) -> None:
        """User prompt includes the scene content to summarize."""
        prompt = build_continuity_prompt("The rain fell heavily on the old house.")
        assert "The rain fell heavily on the old house." in prompt

    def test_user_prompt_asks_for_structured_output(self) -> None:
        """User prompt instructs structured output with all three fields."""
        prompt = build_continuity_prompt("Scene content here.")
        assert "open_threads" in prompt
        assert "emotional_states" in prompt
        assert "summary" in prompt
