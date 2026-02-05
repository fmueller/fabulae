"""JSON output guard prompts and correction templates."""

from __future__ import annotations

from enum import Enum, auto


class JsonErrorType(Enum):
    """Classification of JSON-related errors."""

    TRUNCATED = auto()  # Output cut off
    MARKDOWN_WRAPPED = auto()  # ```json blocks
    INVALID_SYNTAX = auto()  # Malformed JSON
    SCHEMA_MISMATCH = auto()  # Wrong structure
    VALIDATION_ERROR = auto()  # Pydantic validation failed


JSON_GUARD_TEMPLATE = """
CRITICAL: Return ONLY valid JSON:
- Start with { and end with }
- Use double quotes for strings
- No trailing commas
- No markdown code blocks
"""

JSON_CORRECTION_TEMPLATES: dict[JsonErrorType, str] = {
    JsonErrorType.TRUNCATED: """
Your output was cut off. Generate a SHORTER, COMPLETE response.
Keep content brief to avoid truncation.

Partial output:
{original_output}

Return complete, valid JSON:
""",
    JsonErrorType.MARKDOWN_WRAPPED: """
Remove markdown formatting. Return ONLY raw JSON.

Your output:
{original_output}

Return raw JSON (no ``` markers):
""",
    JsonErrorType.INVALID_SYNTAX: """
Fix JSON syntax error: {error_message}

Original:
{original_output}

Return valid JSON:
""",
    JsonErrorType.SCHEMA_MISMATCH: """
Fix schema error: {error_message}

Original:
{original_output}

Return valid JSON matching the required schema:
""",
    JsonErrorType.VALIDATION_ERROR: """
Fix validation error: {error_message}

Original:
{original_output}

Return valid JSON matching the required schema:
""",
}


def build_json_guard_prompt() -> str:
    """Build the JSON guard instructions to include in system prompts."""
    return JSON_GUARD_TEMPLATE.strip()


def build_json_correction_prompt(
    error_type: JsonErrorType,
    original_output: str,
    error_message: str,
) -> str:
    """Build a correction prompt for a JSON error.

    Args:
        error_type: The type of JSON error.
        original_output: The original (erroneous) output.
        error_message: The error message from the parser.

    Returns:
        A correction prompt to help the LLM fix the error.
    """
    template = JSON_CORRECTION_TEMPLATES.get(error_type, JSON_CORRECTION_TEMPLATES[JsonErrorType.INVALID_SYNTAX])
    return template.format(
        original_output=original_output,
        error_message=error_message,
    ).strip()


__all__ = [
    "JSON_CORRECTION_TEMPLATES",
    "JSON_GUARD_TEMPLATE",
    "JsonErrorType",
    "build_json_correction_prompt",
    "build_json_guard_prompt",
]
