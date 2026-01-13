"""Tests to verify prompts provide assigned IDs to the LLM."""

from __future__ import annotations

from fabulae.features.create import prompts


def test_character_prompt_includes_assigned_id() -> None:
    """Verify character prompt includes the assigned ID."""
    assigned_id = "character-05"
    prompt = prompts.build_character_prompt("novel", None, "None", assigned_id)

    # Check that the assigned ID is in the prompt
    assert assigned_id in prompt
    # Check that instruction to use the ID is present
    assert "Use this ID exactly" in prompt
    assert "Do not change or generate a different ID" in prompt


def test_world_fact_prompt_includes_assigned_id() -> None:
    """Verify world fact prompt includes the assigned ID."""
    assigned_id = "location-03"
    prompt = prompts.build_world_fact_prompt("novel", None, "None", assigned_id)

    # Check that the assigned ID is in the prompt
    assert assigned_id in prompt
    # Check that instruction to use the ID is present
    assert "Use this ID exactly" in prompt
    assert "Do not change or generate a different ID" in prompt


def test_scene_prompt_includes_assigned_id() -> None:
    """Verify scene prompt includes the assigned ID."""
    assigned_id = "scene-07"
    prompt = prompts.build_scene_prompt("novel", None, "character-01", "location-01", "None", assigned_id)

    # Check that the assigned ID is in the prompt
    assert assigned_id in prompt
    # Check that instruction to use the ID is present
    assert "Use this ID exactly" in prompt
    assert "Do not change or generate a different ID" in prompt


def test_fragment_prompt_includes_assigned_id() -> None:
    """Verify fragment prompt includes the assigned ID."""
    assigned_id = "fragment-02"
    prompt = prompts.build_fragment_prompt("micro-prose", None, "None", assigned_id)

    # Check that the assigned ID is in the prompt
    assert assigned_id in prompt
    # Check that instruction to use the ID is present
    assert "Use this ID exactly" in prompt
    assert "Do not change or generate a different ID" in prompt


def test_stanza_prompt_includes_assigned_id() -> None:
    """Verify stanza prompt includes the assigned ID."""
    assigned_id = "stanza-03"
    prompt = prompts.build_stanza_prompt("poem", None, "None", assigned_id)

    # Check that the assigned ID is in the prompt
    assert assigned_id in prompt
    # Check that instruction to use the ID is present
    assert "Use this ID exactly" in prompt
    assert "Do not change or generate a different ID" in prompt


def test_assigned_id_section_appears_before_schema() -> None:
    """Verify assigned ID section appears before the output schema."""
    assigned_id = "character-01"
    prompt = prompts.build_character_prompt("novel", None, "None", assigned_id)

    # Find positions
    assigned_id_pos = prompt.find("Assigned ID")
    schema_pos = prompt.find("Output Schema")

    # Assigned ID should appear before schema
    assert assigned_id_pos != -1, "Assigned ID section not found"
    assert schema_pos != -1, "Output Schema section not found"
    assert assigned_id_pos < schema_pos, "Assigned ID should appear before Output Schema"
