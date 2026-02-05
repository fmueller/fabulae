"""JSON output guard for LLM responses with structured output."""

from __future__ import annotations

import inspect
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar, cast

from fabulae.prompts.json import JsonErrorType

T = TypeVar("T")


@dataclass(frozen=True)
class JsonGuardConfig:
    """Configuration for the JSON guard."""

    max_retries: int = 2


@dataclass(frozen=True)
class JsonGuardResult:
    """Result from running the JSON guard."""

    passed: bool
    skipped: bool
    error_type: JsonErrorType | None
    error_message: str | None
    attempts: int


# Patterns for classifying error messages
_TRUNCATED_PATTERNS = [
    r"unexpected end",
    r"unterminated string",
    r"expecting .* but got end",
    r"incomplete",
    r"eof",
    r"premature end",
]

_MARKDOWN_PATTERNS = [
    r"```",
    r"markdown",
    r"code fence",
    r"unexpected token [`'\"]`",
]

_SCHEMA_PATTERNS = [
    r"field required",
    r"missing required",
    r"input should be",
    r"expected .* got",
    r"wrong type",
    r"type error",
]

_VALIDATION_PATTERNS = [
    r"validation error",
    r"validationerror",
]


def classify_json_error(exc: Exception) -> tuple[JsonErrorType, str]:
    """Classify a JSON-related exception into error type and message.

    Args:
        exc: The exception to classify.

    Returns:
        A tuple of (error_type, error_message).
    """
    error_str = str(exc).lower()
    error_message = str(exc)

    # Check for validation errors first (most specific)
    for pattern in _VALIDATION_PATTERNS:
        if re.search(pattern, error_str):
            return JsonErrorType.VALIDATION_ERROR, error_message

    # Check for schema mismatches
    for pattern in _SCHEMA_PATTERNS:
        if re.search(pattern, error_str):
            return JsonErrorType.SCHEMA_MISMATCH, error_message

    # Check for truncated output
    for pattern in _TRUNCATED_PATTERNS:
        if re.search(pattern, error_str):
            return JsonErrorType.TRUNCATED, error_message

    # Check for markdown wrapping
    for pattern in _MARKDOWN_PATTERNS:
        if re.search(pattern, error_str):
            return JsonErrorType.MARKDOWN_WRAPPED, error_message

    # Default to invalid syntax
    return JsonErrorType.INVALID_SYNTAX, error_message


async def _maybe_await(value: T | Awaitable[T]) -> T:
    """Await a value if it's awaitable, otherwise return it directly."""
    if inspect.isawaitable(value):
        return await cast(Awaitable[T], value)
    return value


async def run_with_json_guard(
    runner: Callable[[], T | Awaitable[T]],
    result_type: type[T],  # noqa: ARG001
    system_prompt: str,  # noqa: ARG001
    user_prompt: str,  # noqa: ARG001
    config: JsonGuardConfig | None = None,
    on_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> tuple[T, JsonGuardResult]:
    """Run an LLM call with JSON validation and retry.

    This wraps the runner function and catches JSON-related exceptions.
    On failure, it classifies the error and retries by calling the runner again.

    Note: The current implementation simply retries by calling the runner again.
    For full correction prompt support, use the composed guards.py module.

    Args:
        runner: Callable that produces LLM output.
        result_type: The expected Pydantic model type (for future use).
        system_prompt: The original system prompt (for future use).
        user_prompt: The original user prompt (for future use).
        config: JSON guard configuration (thresholds, retries).
        on_error: Optional callback invoked on each error with
            ``(error_type, error_message, attempt)``.

    Returns:
        A tuple of (output, JsonGuardResult).

    Raises:
        Exception: Re-raises the last exception if max retries exceeded.
    """
    resolved_config = config or JsonGuardConfig()

    attempt = 0
    last_error: Exception | None = None
    last_error_type: JsonErrorType | None = None
    last_error_message: str | None = None

    while attempt <= resolved_config.max_retries:
        try:
            output = await _maybe_await(runner())
            return output, JsonGuardResult(
                passed=True,
                skipped=False,
                error_type=None,
                error_message=None,
                attempts=attempt + 1,
            )
        except Exception as exc:
            last_error = exc
            last_error_type, last_error_message = classify_json_error(exc)

            # Notify callback if provided
            if on_error is not None:
                on_error(last_error_type, last_error_message, attempt + 1)

            attempt += 1
            if attempt > resolved_config.max_retries:
                # Re-raise the original exception
                raise last_error from last_error

            # Build correction prompt for next attempt
            # Note: For the test implementation, we don't actually modify
            # the runner behavior - that's handled in the real integration.
            # The runner will be called again and is expected to succeed
            # (or fail again and retry continues).

    # Should not reach here, but for type safety
    raise last_error if last_error else RuntimeError("Unexpected state in JSON guard")


# Re-export types from prompts.json for convenience
__all__ = [
    "JsonErrorType",
    "JsonGuardConfig",
    "JsonGuardResult",
    "classify_json_error",
    "run_with_json_guard",
]
