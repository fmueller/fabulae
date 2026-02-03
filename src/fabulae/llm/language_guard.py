"""Language guard for LLM outputs written into projects."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TypeVar, cast

from lingua import IsoCode639_1, Language, LanguageDetectorBuilder

T = TypeVar("T")

_DETECTOR = LanguageDetectorBuilder.from_all_languages().build()


@dataclass(frozen=True)
class LanguageGuardResult:
    expected: str
    detected: str | None
    confidence: float | None
    passed: bool
    skipped: bool
    reason: str | None = None


@dataclass(frozen=True)
class LanguageGuardConfig:
    min_chars: int = 200
    min_confidence: float = 0.7
    max_retries: int = 2


def _language_to_iso_code(language: Language) -> str | None:
    iso_code = language.iso_code_639_1
    if iso_code is None:
        return None
    return iso_code.name.lower()


def _resolve_expected_language(expected_language: str) -> tuple[str, Language] | None:
    normalized = expected_language.strip().lower()
    if not normalized:
        return None
    try:
        iso_code = IsoCode639_1.from_str(normalized)
        language = Language.from_iso_code_639_1(iso_code)
    except ValueError:
        return None
    return normalized, language


def detect_language(text: str) -> tuple[str | None, float | None]:
    if not text.strip():
        return None, None
    confidences = _DETECTOR.compute_language_confidence_values(text)
    if not confidences:
        return None, None
    top = confidences[0]
    detected = _language_to_iso_code(top.language)
    if detected is None:
        return None, None
    return detected, float(top.value)


def _evaluate_text(
    text: str,
    expected_language: str,
    config: LanguageGuardConfig,
) -> LanguageGuardResult:
    cleaned = text.strip()
    if len(cleaned) < config.min_chars:
        return LanguageGuardResult(
            expected=expected_language,
            detected=None,
            confidence=None,
            passed=True,
            skipped=True,
            reason="text_too_short",
        )
    detected, confidence = detect_language(cleaned)
    if detected is None or confidence is None:
        return LanguageGuardResult(
            expected=expected_language,
            detected=None,
            confidence=None,
            passed=True,
            skipped=True,
            reason="language_undetected",
        )
    if confidence < config.min_confidence:
        return LanguageGuardResult(
            expected=expected_language,
            detected=detected,
            confidence=confidence,
            passed=True,
            skipped=True,
            reason="low_confidence",
        )
    if detected != expected_language:
        return LanguageGuardResult(
            expected=expected_language,
            detected=detected,
            confidence=confidence,
            passed=False,
            skipped=False,
            reason="language_mismatch",
        )
    return LanguageGuardResult(
        expected=expected_language,
        detected=detected,
        confidence=confidence,
        passed=True,
        skipped=False,
        reason=None,
    )


async def _maybe_await(value: T | Awaitable[T]) -> T:
    if inspect.isawaitable(value):
        return await cast(Awaitable[T], value)
    return value


async def run_with_language_guard(
    runner: Callable[[], T | Awaitable[T]],
    extract_text: Callable[[T], str],
    expected_language: str | None,
    config: LanguageGuardConfig | None = None,
    reprompt: Callable[[int], None] | None = None,
    correct: Callable[[int, T], T | Awaitable[T]] | None = None,
    on_correction: Callable[[str, str, int], None] | None = None,
) -> tuple[T, LanguageGuardResult]:
    """Run an LLM call and enforce project language, retrying if needed.

    Args:
        runner: Callable that produces LLM output.
        extract_text: Extracts narrative text from the output for language detection.
        expected_language: ISO 639-1 code for the target language.
        config: Language guard configuration (thresholds, retries).
        reprompt: Legacy callback that modifies the system prompt for re-generation.
        correct: Correction callback that receives the wrong-language output and
            returns a corrected version. Takes precedence over ``reprompt``.
        on_correction: Optional callback invoked before each correction attempt
            with ``(expected_code, detected_code, attempt)``.
    """
    resolved_config = config or LanguageGuardConfig()
    if expected_language is None or not expected_language.strip():
        output = await _maybe_await(runner())
        result = LanguageGuardResult(
            expected=expected_language or "",
            detected=None,
            confidence=None,
            passed=True,
            skipped=True,
            reason="missing_expected_language",
        )
        return output, result

    resolved = _resolve_expected_language(expected_language)
    if resolved is None:
        output = await _maybe_await(runner())
        result = LanguageGuardResult(
            expected=expected_language.strip().lower(),
            detected=None,
            confidence=None,
            passed=True,
            skipped=True,
            reason="unsupported_language",
        )
        return output, result

    expected_code, _ = resolved
    attempt = 0
    while True:
        output = await _maybe_await(runner())
        text = extract_text(output)
        result = _evaluate_text(text, expected_code, resolved_config)
        if result.passed or result.skipped or attempt >= resolved_config.max_retries:
            return output, result
        attempt += 1
        if on_correction is not None and result.detected is not None:
            on_correction(expected_code, result.detected, attempt)
        if correct is not None:
            output = await _maybe_await(correct(attempt, output))
            text = extract_text(output)
            result = _evaluate_text(text, expected_code, resolved_config)
            if result.passed or result.skipped or attempt >= resolved_config.max_retries:
                return output, result
        elif reprompt is not None:
            reprompt(attempt)


__all__ = [
    "LanguageGuardConfig",
    "LanguageGuardResult",
    "detect_language",
    "run_with_language_guard",
]
