"""Error context and user-friendly error formatting for create command."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto


class ErrorType(Enum):
    """Classification of LLM errors for retry decisions."""

    # Transient errors - worth retrying with same prompt
    SERVER_ERROR = auto()  # 500 errors, connection issues
    RATE_LIMIT = auto()  # 429 errors
    TIMEOUT = auto()  # Request timeouts

    # JSON-specific errors - retry with simplified prompt hints
    JSON_TRUNCATED = auto()  # Incomplete JSON output
    JSON_PARSE_ERROR = auto()  # Malformed JSON

    # Validation errors - retry with validation feedback
    VALIDATION_ERROR = auto()  # Schema/content validation failed

    # Permanent errors - don't retry
    AUTH_ERROR = auto()  # 401/403 errors
    MODEL_NOT_FOUND = auto()  # Model doesn't exist
    CONTEXT_TOO_LONG = auto()  # Input exceeds context window
    UNKNOWN = auto()  # Unclassified error


# Patterns for classifying error messages
_JSON_TRUNCATED_PATTERNS = [
    r"unexpected end of json",
    r"unterminated string",
    r"expecting .* but got end",
    r"incomplete json",
    r"json parse error.*eof",
]

_JSON_PARSE_PATTERNS = [
    r"invalid json",
    r"json decode",
    r"expecting property name",
    r"expecting value",
    r"trailing comma",
]

_CONTEXT_LENGTH_PATTERNS = [
    r"context.*(length|window|limit)",
    r"max.*(tokens|length)",
    r"input too long",
    r"prompt.*(too long|exceeds)",
]

_RATE_LIMIT_PATTERNS = [
    r"rate.?limit",
    r"too many requests",
    r"quota exceeded",
]


def classify_error(exc: Exception) -> ErrorType:
    """Classify an exception to determine retry strategy.

    Args:
        exc: The exception to classify.

    Returns:
        The ErrorType classification.
    """
    error_str = str(exc).lower()

    # Check for status codes in the error message
    if "status_code: 500" in error_str or "status_code: 502" in error_str or "status_code: 503" in error_str:
        # Check for JSON-specific 500 errors (common with Ollama)
        for pattern in _JSON_TRUNCATED_PATTERNS:
            if re.search(pattern, error_str):
                return ErrorType.JSON_TRUNCATED
        return ErrorType.SERVER_ERROR

    if "status_code: 429" in error_str:
        return ErrorType.RATE_LIMIT

    if "status_code: 401" in error_str or "status_code: 403" in error_str:
        return ErrorType.AUTH_ERROR

    if "status_code: 404" in error_str:
        return ErrorType.MODEL_NOT_FOUND

    # Check for timeout patterns
    if "timeout" in error_str or "timed out" in error_str:
        return ErrorType.TIMEOUT

    # Check for context length issues
    for pattern in _CONTEXT_LENGTH_PATTERNS:
        if re.search(pattern, error_str):
            return ErrorType.CONTEXT_TOO_LONG

    # Check for rate limiting
    for pattern in _RATE_LIMIT_PATTERNS:
        if re.search(pattern, error_str):
            return ErrorType.RATE_LIMIT

    # Check for JSON truncation (without status code)
    for pattern in _JSON_TRUNCATED_PATTERNS:
        if re.search(pattern, error_str):
            return ErrorType.JSON_TRUNCATED

    # Check for JSON parse errors
    for pattern in _JSON_PARSE_PATTERNS:
        if re.search(pattern, error_str):
            return ErrorType.JSON_PARSE_ERROR

    # Check for validation errors (pydantic)
    if "validation error" in error_str or "validationerror" in error_str:
        return ErrorType.VALIDATION_ERROR

    return ErrorType.UNKNOWN


def is_transient_error(error_type: ErrorType) -> bool:
    """Check if an error type is transient and worth retrying."""
    return error_type in {
        ErrorType.SERVER_ERROR,
        ErrorType.RATE_LIMIT,
        ErrorType.TIMEOUT,
        ErrorType.JSON_TRUNCATED,
        ErrorType.JSON_PARSE_ERROR,
        ErrorType.VALIDATION_ERROR,
        ErrorType.UNKNOWN,  # Give unknown errors a chance
    }


def is_json_error(error_type: ErrorType) -> bool:
    """Check if an error is JSON-related."""
    return error_type in {ErrorType.JSON_TRUNCATED, ErrorType.JSON_PARSE_ERROR}


def get_error_guidance(error_type: ErrorType) -> str:
    """Get user-facing guidance for an error type."""
    guidance_map = {
        ErrorType.SERVER_ERROR: "The LLM server returned an error. This is usually temporary.",
        ErrorType.RATE_LIMIT: "Rate limit reached. Wait a moment before retrying.",
        ErrorType.TIMEOUT: "Request timed out. The model may be overloaded.",
        ErrorType.JSON_TRUNCATED: "The model's JSON output was truncated. This often happens with smaller models.",
        ErrorType.JSON_PARSE_ERROR: "The model returned invalid JSON. Try a larger or more capable model.",
        ErrorType.VALIDATION_ERROR: "The model output didn't match the expected format.",
        ErrorType.AUTH_ERROR: "Authentication failed. Check your API key.",
        ErrorType.MODEL_NOT_FOUND: "The specified model was not found on the server.",
        ErrorType.CONTEXT_TOO_LONG: "The prompt is too long for the model's context window.",
        ErrorType.UNKNOWN: "An unexpected error occurred.",
    }
    return guidance_map.get(error_type, "An unexpected error occurred.")


class GenerationStage(Enum):
    """Stages of the project generation pipeline."""

    STYLE = auto()
    PREMISE = auto()
    OUTLINE_STRUCTURE = auto()
    OUTLINE_CONTENT = auto()
    CHARACTERS = auto()
    CHARACTER_PLAN = auto()
    WORLD = auto()
    WORLD_PLAN = auto()
    BEATS = auto()
    SCENES = auto()
    ENRICHMENT = auto()
    FRAGMENT_PLAN = auto()
    FRAGMENTS = auto()
    POEM_PLAN = auto()
    STANZAS = auto()


STAGE_DESCRIPTIONS: dict[GenerationStage, str] = {
    GenerationStage.STYLE: "determining the writing style",
    GenerationStage.PREMISE: "expanding your idea into a premise",
    GenerationStage.OUTLINE_STRUCTURE: "planning the story structure",
    GenerationStage.OUTLINE_CONTENT: "filling in the outline details",
    GenerationStage.CHARACTERS: "developing character details",
    GenerationStage.CHARACTER_PLAN: "planning the cast of characters",
    GenerationStage.WORLD: "building the world details",
    GenerationStage.WORLD_PLAN: "planning the world elements",
    GenerationStage.BEATS: "creating story beats",
    GenerationStage.SCENES: "expanding scenes",
    GenerationStage.ENRICHMENT: "enriching the narrative",
    GenerationStage.FRAGMENT_PLAN: "planning the fragments",
    GenerationStage.FRAGMENTS: "writing fragments",
    GenerationStage.POEM_PLAN: "planning the poem structure",
    GenerationStage.STANZAS: "writing stanzas",
}


@dataclass
class ErrorContext:
    """Context for formatting user-friendly error messages."""

    stage: GenerationStage
    attempt: int
    max_attempts: int
    error_type: ErrorType | None = None
    model_name: str | None = None

    def format_user_message(self, error: Exception | str) -> str:
        """Format a user-friendly error message with context and suggestions."""
        stage_desc = STAGE_DESCRIPTIONS.get(self.stage, "generating content")
        error_str = str(error)

        # Classify error if not already done
        error_type = self.error_type
        if error_type is None and isinstance(error, Exception):
            error_type = classify_error(error)
        elif error_type is None:
            # Try to classify from string
            class _FakeExc(Exception):
                pass

            error_type = classify_error(_FakeExc(error_str))

        # Get error-specific guidance
        guidance = get_error_guidance(error_type) if error_type else "An unexpected error occurred."

        # Build suggestions based on error type
        suggestions = ["  - Try again (this may be a temporary issue)"]

        if error_type == ErrorType.JSON_TRUNCATED:
            suggestions = [
                "  - Use a larger model (small models often truncate JSON)",
                "  - Try with a simpler format (e.g., --format micro-prose)",
                "  - The current model may not support structured output well",
            ]
        elif error_type == ErrorType.JSON_PARSE_ERROR:
            suggestions = [
                "  - Use a more capable model with --model",
                "  - Try a simpler format (e.g., --format short-story)",
                "  - Check that your model supports JSON/structured output",
            ]
        elif error_type == ErrorType.CONTEXT_TOO_LONG:
            suggestions = [
                "  - Use a simpler or shorter idea",
                "  - Try a smaller format (e.g., --format short-story)",
                "  - Use a model with a larger context window",
            ]
        elif error_type in {ErrorType.SERVER_ERROR, ErrorType.TIMEOUT}:
            suggestions = [
                "  - Try again (server errors are often temporary)",
                "  - Check that your LLM server is running: fabulae doctor",
                "  - The model may be overloaded or restarting",
            ]
        elif error_type == ErrorType.RATE_LIMIT:
            suggestions = [
                "  - Wait a few seconds and try again",
                "  - Check your API quota/limits",
            ]
        elif error_type == ErrorType.AUTH_ERROR:
            suggestions = [
                "  - Check your API key configuration",
                "  - Verify FABULAE_LLM_API_KEY or OPENAI_API_KEY is set correctly",
            ]
        elif error_type == ErrorType.MODEL_NOT_FOUND:
            suggestions = [
                "  - Check that the model name is correct",
                "  - List available models with: fabulae doctor",
                "  - The model may need to be downloaded first",
            ]

        lines = [
            f"Error during {stage_desc} (attempt {self.attempt}/{self.max_attempts})",
            "",
            f"What happened: {guidance}",
        ]

        if self.model_name:
            lines.append(f"Model: {self.model_name}")

        lines.extend(
            [
                "",
                "What you can do:",
                *suggestions,
                "",
                f"Technical details: {error_str}",
            ]
        )
        return "\n".join(lines)


def format_json_retry_hint() -> str:
    """Return extra prompt hints for JSON-related errors.

    This is appended to retry prompts when the model fails to produce valid JSON.
    """
    return """
IMPORTANT: Your previous response had JSON formatting issues.
Please ensure your response:
1. Is ONLY valid JSON (no markdown code blocks, no explanations)
2. Starts with '{' and ends with '}'
3. Uses double quotes for all strings
4. Has no trailing commas
5. Keeps the response concise to avoid truncation
"""


__all__ = [
    "ErrorContext",
    "ErrorType",
    "GenerationStage",
    "STAGE_DESCRIPTIONS",
    "classify_error",
    "format_json_retry_hint",
    "get_error_guidance",
    "is_json_error",
    "is_transient_error",
]
