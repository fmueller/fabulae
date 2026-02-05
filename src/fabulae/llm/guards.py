"""Composed guards for LLM outputs: JSON guard (inner) + Language guard (outer)."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar, cast

from fabulae.llm import LLMConfig
from fabulae.llm.json_guard import (
    JsonErrorType,
    JsonGuardConfig,
    JsonGuardResult,
    classify_json_error,
    is_non_retryable_error,
)
from fabulae.llm.language_guard import (
    LanguageGuardConfig,
    LanguageGuardResult,
    run_with_language_guard,
)

T = TypeVar("T")


@dataclass(frozen=True)
class GuardsConfig:
    """Configuration for the composed guards."""

    language: LanguageGuardConfig | None = None
    json: JsonGuardConfig | None = None


@dataclass(frozen=True)
class GuardsResult:
    """Combined result from running all guards."""

    language: LanguageGuardResult
    json: JsonGuardResult


def _skipped_language_result(reason: str) -> LanguageGuardResult:
    """Create a skipped language guard result."""
    return LanguageGuardResult(
        expected="",
        detected=None,
        confidence=None,
        passed=True,
        skipped=True,
        reason=reason,
    )


def _skipped_json_result() -> JsonGuardResult:
    """Create a skipped JSON guard result."""
    return JsonGuardResult(
        passed=True,
        skipped=True,
        error_type=None,
        error_message=None,
        attempts=1,
    )


async def _maybe_await(value: T | Awaitable[T]) -> T:
    """Await a value if it's awaitable, otherwise return it directly."""
    if inspect.isawaitable(value):
        return await cast(Awaitable[T], value)
    return value


async def run_with_guards(
    runner: Callable[[], T | Awaitable[T]],
    result_type: type[T],  # noqa: ARG001
    system_prompt: str,  # noqa: ARG001
    user_prompt: str,  # noqa: ARG001
    llm_config: LLMConfig,  # noqa: ARG001
    extract_text: Callable[[T], str],
    expected_language: str | None = None,
    config: GuardsConfig | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> tuple[T, GuardsResult]:
    """Run LLM call with language guard (outer) and JSON guard (inner).

    Guard order: Language Guard (outer) -> JSON Guard (inner)

    Flow:
    1. Language guard wraps the JSON-guarded runner
    2. JSON guard catches Pydantic AI parse exceptions, retries with correction
    3. Once JSON is valid, language guard checks content
    4. If language incorrect, language guard retries (going through JSON guard again)
    5. Returns final Pydantic model

    Args:
        runner: Callable that produces LLM output (Pydantic model).
        result_type: The expected Pydantic model type.
        system_prompt: The original system prompt.
        user_prompt: The original user prompt.
        llm_config: LLM configuration.
        extract_text: Function to extract text from output for language detection.
        expected_language: ISO 639-1 code for the target language.
        config: Guards configuration (language and JSON guard configs).
        on_language_correction: Optional callback for language corrections.
        on_json_error: Optional callback for JSON errors.

    Returns:
        A tuple of (output, GuardsResult).
    """
    resolved_config = config or GuardsConfig()

    # Track JSON guard state
    json_attempts = 0
    json_last_error_type: JsonErrorType | None = None
    json_last_error_message: str | None = None
    json_passed = True

    # Create the JSON-guarded runner
    async def json_guarded_runner() -> T:
        nonlocal json_attempts, json_last_error_type, json_last_error_message, json_passed

        json_config = resolved_config.json or JsonGuardConfig()
        max_retries = json_config.max_retries

        local_attempt = 0
        last_error: Exception | None = None

        while local_attempt <= max_retries:
            try:
                output = await _maybe_await(runner())
                json_attempts = local_attempt + 1
                json_passed = True
                return output
            except Exception as exc:
                last_error = exc
                error_type, error_message = classify_json_error(exc)
                json_last_error_type = error_type
                json_last_error_message = error_message
                json_passed = False

                # Non-retryable errors exit immediately
                if is_non_retryable_error(error_type):
                    raise last_error from last_error

                # Notify callback
                if on_json_error is not None:
                    on_json_error(error_type, error_message, local_attempt + 1)

                local_attempt += 1
                if local_attempt > max_retries:
                    json_attempts = local_attempt
                    raise last_error from last_error

        # Should not reach here
        raise last_error if last_error else RuntimeError("Unexpected state")

    # If no language expected, skip language guard
    if expected_language is None:
        # If no JSON config, just run directly
        if resolved_config.json is None:
            output = await _maybe_await(runner())
            return output, GuardsResult(
                language=_skipped_language_result("missing_expected_language"),
                json=_skipped_json_result(),
            )

        # Run with JSON guard only
        output = await json_guarded_runner()
        return output, GuardsResult(
            language=_skipped_language_result("missing_expected_language"),
            json=JsonGuardResult(
                passed=json_passed,
                skipped=False,
                error_type=json_last_error_type,
                error_message=json_last_error_message,
                attempts=json_attempts,
            ),
        )

    # Run with language guard (which wraps JSON guard)
    language_config = resolved_config.language or LanguageGuardConfig()

    output, language_result = await run_with_language_guard(
        runner=json_guarded_runner,
        extract_text=extract_text,
        expected_language=expected_language,
        config=language_config,
        on_correction=on_language_correction,
    )

    # Build final JSON result
    json_result = JsonGuardResult(
        passed=json_passed,
        skipped=resolved_config.json is None,
        error_type=json_last_error_type if not json_passed else None,
        error_message=json_last_error_message if not json_passed else None,
        attempts=json_attempts if json_attempts > 0 else 1,
    )

    return output, GuardsResult(
        language=language_result,
        json=json_result,
    )


__all__ = [
    "GuardsConfig",
    "GuardsResult",
    "run_with_guards",
]
