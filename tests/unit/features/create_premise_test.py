"""Tests for premise expansion."""

from fabulae.features.create.prompts import build_premise_expansion_prompt
from fabulae.features.create.prompts_v2 import build_premise_prompt_v2
from fabulae.features.create.schemas import PremiseOutput, StyleOutput


def test_premise_output_schema() -> None:
    """Test PremiseOutput schema validation."""
    output = PremiseOutput(premise="A compelling premise about...")
    assert output.premise == "A compelling premise about..."


def test_premise_output_with_title() -> None:
    """Test PremiseOutput schema with title field."""
    output = PremiseOutput(title="A Great Story", premise="A compelling premise about...")
    assert output.title == "A Great Story"
    assert output.premise == "A compelling premise about..."


def test_premise_output_title_is_optional() -> None:
    """Test PremiseOutput title field is optional."""
    output = PremiseOutput(premise="A compelling premise about...")
    assert output.title is None
    assert output.premise == "A compelling premise about..."


def test_premise_output_strips_whitespace() -> None:
    """Test PremiseOutput strips whitespace from premise."""
    output = PremiseOutput(premise="  A premise with whitespace  ")
    assert output.premise == "A premise with whitespace"


def test_premise_output_strips_title_whitespace() -> None:
    """Test PremiseOutput strips whitespace from title."""
    output = PremiseOutput(title="  A Title with Whitespace  ", premise="A premise")
    assert output.title == "A Title with Whitespace"


def test_premise_output_strips_newlines() -> None:
    """Test PremiseOutput strips leading/trailing newlines."""
    output = PremiseOutput(premise="\n\nA premise with newlines\n\n")
    assert output.premise == "A premise with newlines"


def test_build_premise_expansion_prompt() -> None:
    """Test premise expansion prompt builder."""
    prompt = build_premise_expansion_prompt("novel", "en")
    assert "premise" in prompt.lower()
    assert "2-4 sentence" in prompt.lower()
    assert '"title"' in prompt


def test_build_premise_expansion_prompt_without_language() -> None:
    """Test premise expansion prompt builder without language."""
    prompt = build_premise_expansion_prompt("novel", None)
    assert "premise" in prompt.lower()
    assert "2-4 sentence" in prompt.lower()
    # Language section should not be present
    assert "Expected Language" not in prompt


def test_build_premise_expansion_prompt_with_language() -> None:
    """Test premise expansion prompt includes language when provided."""
    prompt = build_premise_expansion_prompt("novel", "en")
    assert "Expected Language" in prompt
    assert "ISO 639-1: en" in prompt


def test_build_premise_expansion_prompt_includes_format() -> None:
    """Test premise expansion prompt includes format."""
    prompt = build_premise_expansion_prompt("novella", "en")
    assert "novella" in prompt.lower()


def test_build_premise_prompt_v2_includes_title() -> None:
    """Test premise prompt v2 requests a title in the output schema."""
    style = StyleOutput(language="en", pov="third", tense="past")
    prompt = build_premise_prompt_v2("novel", "A story about a dragon", style)
    assert '"title"' in prompt
    assert "premise" in prompt.lower()


def test_build_premise_prompt_v2_includes_format() -> None:
    """Test premise prompt v2 includes format."""
    style = StyleOutput(language="en", pov="third", tense="past")
    prompt = build_premise_prompt_v2("short-story", "A quick tale", style)
    assert "short-story" in prompt.lower()


def test_build_premise_prompt_v2_includes_idea() -> None:
    """Test premise prompt v2 includes the original idea."""
    style = StyleOutput(language="en", pov="third", tense="past")
    prompt = build_premise_prompt_v2("novel", "A story about dragons and knights", style)
    assert "A story about dragons and knights" in prompt
