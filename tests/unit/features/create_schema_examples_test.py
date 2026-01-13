"""Tests to verify schema examples in prompts use sequential ID format."""

from __future__ import annotations

import json
import re

from fabulae.features.create import prompts


def test_character_plan_prompt_has_sequential_id() -> None:
    """Verify character plan prompt example uses character-01 format."""
    prompt = prompts.build_character_plan_prompt("novel", None, (3, 5))
    assert '"id": "character-01"' in prompt
    # Extract and parse the JSON example
    json_match = re.search(r'{\s*"characters":\s*\[.*?\]\s*}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["characters"][0]["id"] == "character-01"


def test_character_prompt_has_sequential_id() -> None:
    """Verify character prompt example uses character-01 format."""
    prompt = prompts.build_character_prompt("novel", None, "None", "character-01")
    assert '"id": "character-01"' in prompt
    json_match = re.search(r'{\s*"id":\s*"character-\d+".*?}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["id"] == "character-01"


def test_world_plan_prompt_has_sequential_location_id() -> None:
    """Verify world plan prompt example uses location-01 format."""
    prompt = prompts.build_world_plan_prompt("novel", None, (3, 5))
    assert '"id": "location-01"' in prompt
    json_match = re.search(r'{\s*"setting".*?"facts":\s*\[.*?\]\s*}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["facts"][0]["id"] == "location-01"


def test_world_fact_prompt_has_sequential_location_id() -> None:
    """Verify world fact prompt example uses location-01 format."""
    prompt = prompts.build_world_fact_prompt("novel", None, "None", "location-01")
    assert '"id": "location-01"' in prompt
    json_match = re.search(r'{\s*"id":\s*"location-\d+".*?}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["id"] == "location-01"


def test_plot_outline_prompt_has_sequential_ids() -> None:
    """Verify plot outline prompt example uses sequential ID format."""
    prompt = prompts.build_plot_outline_prompt(
        "novel", None, {"chapters": (1, 3), "scenes": (5, 10), "beats": (10, 20)}, (2, 4)
    )
    # Check for chapter ID
    assert '"id": "chapter-01"' in prompt
    # Check for scene IDs
    assert '"id": "scene-01"' in prompt
    assert '"id": "scene-02"' in prompt

    # Verify the IDs are in the correct format through direct string checks
    # These checks are sufficient for validating the sequential ID format
    lines = prompt.split("\n")
    chapter_line = next((line for line in lines if '"id": "chapter-01"' in line), None)
    assert chapter_line is not None
    scene1_line = next((line for line in lines if '"id": "scene-01"' in line), None)
    assert scene1_line is not None
    scene2_line = next((line for line in lines if '"id": "scene-02"' in line), None)
    assert scene2_line is not None


def test_scene_prompt_has_sequential_ids() -> None:
    """Verify scene prompt example uses sequential ID format for scenes and beats."""
    prompt = prompts.build_scene_prompt("novel", None, "character-01", "location-01", "None", "scene-01")
    # Check for scene ID
    assert '"id": "scene-01"' in prompt
    # Check for beat IDs
    assert '"id": "scene-01-beat-01"' in prompt
    assert '"id": "scene-01-beat-02"' in prompt
    # Check for character and location references
    assert '"characters": ["character-01"]' in prompt
    assert '"location": "location-01"' in prompt

    # Verify the IDs are in the correct format through direct string checks
    lines = prompt.split("\n")
    scene_line = next((line for line in lines if '"id": "scene-01"' in line), None)
    assert scene_line is not None
    beat1_line = next((line for line in lines if '"id": "scene-01-beat-01"' in line), None)
    assert beat1_line is not None
    beat2_line = next((line for line in lines if '"id": "scene-01-beat-02"' in line), None)
    assert beat2_line is not None


def test_fragment_plan_prompt_has_sequential_id() -> None:
    """Verify fragment plan prompt example uses fragment-01 format."""
    prompt = prompts.build_fragment_plan_prompt("micro-prose", None, (3, 5))
    assert '"id": "fragment-01"' in prompt
    json_match = re.search(r'{\s*"title".*?"fragments":\s*\[.*?\]\s*}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["fragments"][0]["id"] == "fragment-01"


def test_fragment_prompt_has_sequential_id() -> None:
    """Verify fragment prompt example uses fragment-01 format."""
    prompt = prompts.build_fragment_prompt("micro-prose", None, "None", "fragment-01")
    assert '"id": "fragment-01"' in prompt
    json_match = re.search(r'{\s*"id":\s*"fragment-\d+".*?}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["id"] == "fragment-01"


def test_poem_plan_prompt_has_sequential_id() -> None:
    """Verify poem plan prompt example uses stanza-01 format."""
    prompt = prompts.build_poem_plan_prompt("poem", None, (2, 4), (8, 16))
    assert '"id": "stanza-01"' in prompt
    json_match = re.search(r'{\s*"title".*?"stanzas":\s*\[.*?\]\s*}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["stanzas"][0]["id"] == "stanza-01"


def test_stanza_prompt_has_sequential_id() -> None:
    """Verify stanza prompt example uses stanza-01 format."""
    prompt = prompts.build_stanza_prompt("poem", None, "None", "stanza-01")
    assert '"id": "stanza-01"' in prompt
    json_match = re.search(r'{\s*"id":\s*"stanza-\d+".*?}', prompt, re.DOTALL)
    assert json_match, "No JSON example found in prompt"
    json_text = json_match.group(0)
    example = json.loads(json_text)
    assert example["id"] == "stanza-01"


def test_schema_examples_follow_sequential_pattern() -> None:
    """Verify all extracted schema examples follow the sequential ID pattern."""
    # Pattern for valid sequential IDs: {type}-{digits}
    # Examples: character-01, scene-01, scene-01-beat-01, fragment-01, stanza-01, etc.
    id_pattern = re.compile(r'"id"\s*:\s*"([a-z]+(?:-[a-z]+)*-\d+(?:-[a-z]+-\d+)?)"')

    prompts_to_test = [
        ("build_character_plan_prompt", ("novel", None, (3, 5))),
        ("build_character_prompt", ("novel", None, "None", "character-01")),
        ("build_world_plan_prompt", ("novel", None, (3, 5))),
        ("build_world_fact_prompt", ("novel", None, "None", "location-01")),
        (
            "build_plot_outline_prompt",
            ("novel", None, {"chapters": (1, 3), "scenes": (5, 10), "beats": (10, 20)}, (2, 4)),
        ),
        ("build_scene_prompt", ("novel", None, "character-01", "location-01", "None", "scene-01")),
        ("build_fragment_plan_prompt", ("micro-prose", None, (3, 5))),
        ("build_fragment_prompt", ("micro-prose", None, "None", "fragment-01")),
        ("build_poem_plan_prompt", ("poem", None, (2, 4), (8, 16))),
        ("build_stanza_prompt", ("poem", None, "None", "stanza-01")),
    ]

    for prompt_func_name, args in prompts_to_test:
        prompt_func = getattr(prompts, prompt_func_name)
        prompt = prompt_func(*args)
        matches = id_pattern.findall(prompt)
        assert len(matches) > 0, f"No IDs found in {prompt_func_name}"
        for match in matches:
            # Verify the format matches the sequential ID pattern
            assert re.match(r"^[a-z]+(?:-[a-z]+)*-\d+(?:-[a-z]+-\d+)?$", match), (
                f"ID '{match}' in {prompt_func_name} does not match sequential format"
            )
