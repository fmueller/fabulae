"""Unit tests for the shared language guard."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import pytest

from fabulae.llm import language_guard


@dataclass
class DummyOutput:
    text: str


@dataclass
class CallTracker:
    runner: int = 0
    reprompts: list[int] = field(default_factory=list)
    corrections: list[tuple[int, str]] = field(default_factory=list)


def _run_guard(
    runner: Callable[[], DummyOutput | Awaitable[DummyOutput]],
    extract_text: Callable[[DummyOutput], str],
    expected_language: str,
    config: language_guard.LanguageGuardConfig | None = None,
    reprompt: Callable[[int], None] | None = None,
    correct: Callable[[int, DummyOutput], DummyOutput | Awaitable[DummyOutput]] | None = None,
) -> tuple[DummyOutput, language_guard.LanguageGuardResult]:
    return asyncio.run(
        language_guard.run_with_language_guard(
            runner,
            extract_text,
            expected_language,
            config=config,
            reprompt=reprompt,
            correct=correct,
        )
    )


def test_skip_on_unsupported_language_code(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_detect(_: str) -> tuple[str | None, float | None]:
        raise AssertionError("detect_language should not be called for unsupported language")

    monkeypatch.setattr(language_guard, "detect_language", fail_detect)

    async def runner() -> DummyOutput:
        return DummyOutput(text="Hello world" * 20)

    output, result = _run_guard(runner, lambda value: value.text, "zz")
    assert output.text.startswith("Hello world")
    assert result.skipped is True
    assert result.reason == "unsupported_language"


def test_skip_on_short_text(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_detect(_: str) -> tuple[str | None, float | None]:
        raise AssertionError("detect_language should not be called for short text")

    monkeypatch.setattr(language_guard, "detect_language", fail_detect)

    async def runner() -> DummyOutput:
        return DummyOutput(text="Too short.")

    config = language_guard.LanguageGuardConfig(min_chars=50)
    _, result = _run_guard(runner, lambda value: value.text, "en", config=config)
    assert result.skipped is True
    assert result.reason == "text_too_short"


def test_retries_on_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    detections = [("fr", 0.9), ("fr", 0.9), ("en", 0.9)]

    def fake_detect(_: str) -> tuple[str | None, float | None]:
        return detections.pop(0)

    monkeypatch.setattr(language_guard, "detect_language", fake_detect)

    calls = CallTracker()

    async def runner() -> DummyOutput:
        calls.runner += 1
        return DummyOutput(text="x" * 10)

    def reprompt(attempt: int) -> None:
        if calls.reprompts is not None:
            calls.reprompts.append(attempt)

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=2)
    _, result = _run_guard(
        runner,
        lambda value: value.text,
        "en",
        config=config,
        reprompt=reprompt,
    )
    assert calls.runner == 3
    assert calls.reprompts == [1, 2]
    assert result.passed is True
    assert result.detected == "en"


def test_accepts_match(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(language_guard, "detect_language", lambda _: ("en", 0.95))

    async def runner() -> DummyOutput:
        return DummyOutput(text="x" * 10)

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=2)
    _, result = _run_guard(runner, lambda value: value.text, "en", config=config)
    assert result.passed is True
    assert result.skipped is False


def test_enforces_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    detections = [("fr", 0.9), ("fr", 0.9)]
    monkeypatch.setattr(language_guard, "detect_language", lambda _: detections.pop(0))

    calls = CallTracker()

    async def runner() -> DummyOutput:
        calls.runner += 1
        return DummyOutput(text="x" * 10)

    def reprompt(attempt: int) -> None:
        if calls.reprompts is not None:
            calls.reprompts.append(attempt)

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=1)
    _, result = _run_guard(
        runner,
        lambda value: value.text,
        "en",
        config=config,
        reprompt=reprompt,
    )
    assert calls.runner == 2
    assert calls.reprompts == [1]
    assert result.passed is False
    assert result.reason == "language_mismatch"


def test_correct_callback_called_with_previous_output(monkeypatch: pytest.MonkeyPatch) -> None:
    """correct callback receives the wrong-language output for correction."""
    # First detection: French (mismatch), then correction returns German (match)
    detections = [("fr", 0.9), ("de", 0.9)]

    def fake_detect(_: str) -> tuple[str | None, float | None]:
        return detections.pop(0)

    monkeypatch.setattr(language_guard, "detect_language", fake_detect)

    calls = CallTracker()

    async def runner() -> DummyOutput:
        calls.runner += 1
        return DummyOutput(text="Bonjour le monde" * 5)

    async def correct(attempt: int, previous: DummyOutput) -> DummyOutput:
        calls.corrections.append((attempt, previous.text))
        return DummyOutput(text="Hallo Welt " * 10)

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=2)
    output, result = _run_guard(
        runner,
        lambda value: value.text,
        "de",
        config=config,
        correct=correct,
    )

    assert calls.runner == 1  # Only one initial call
    assert len(calls.corrections) == 1
    assert calls.corrections[0][0] == 1  # attempt number
    assert "Bonjour" in calls.corrections[0][1]  # received original output
    assert result.passed is True
    assert output.text.startswith("Hallo Welt")


def test_correct_output_reevaluated_for_language(monkeypatch: pytest.MonkeyPatch) -> None:
    """Corrected output is re-evaluated; if still wrong, loop continues."""
    # Initial: French, correction also French, then next runner: French, second correction: German
    detections = [("fr", 0.9), ("fr", 0.9), ("fr", 0.9), ("de", 0.9)]

    def fake_detect(_: str) -> tuple[str | None, float | None]:
        return detections.pop(0)

    monkeypatch.setattr(language_guard, "detect_language", fake_detect)

    calls = CallTracker()

    async def runner() -> DummyOutput:
        calls.runner += 1
        return DummyOutput(text="Bonjour " * 10)

    async def correct(attempt: int, previous: DummyOutput) -> DummyOutput:
        calls.corrections.append((attempt, previous.text))
        # First correction also returns wrong language
        if len(calls.corrections) <= 1:
            return DummyOutput(text="Encore français " * 10)
        return DummyOutput(text="Hallo Welt " * 10)

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=3)
    output, result = _run_guard(
        runner,
        lambda value: value.text,
        "de",
        config=config,
        correct=correct,
    )

    # Runner called twice, first correction failed, second correction succeeds
    assert calls.runner == 2
    assert len(calls.corrections) == 2
    assert result.passed is True


def test_correct_takes_precedence_over_reprompt(monkeypatch: pytest.MonkeyPatch) -> None:
    """When both correct and reprompt are provided, correct is used."""
    detections = [("fr", 0.9), ("de", 0.9)]

    def fake_detect(_: str) -> tuple[str | None, float | None]:
        return detections.pop(0)

    monkeypatch.setattr(language_guard, "detect_language", fake_detect)

    calls = CallTracker()

    async def runner() -> DummyOutput:
        calls.runner += 1
        return DummyOutput(text="Bonjour " * 10)

    def reprompt(attempt: int) -> None:
        calls.reprompts.append(attempt)

    async def correct(attempt: int, previous: DummyOutput) -> DummyOutput:
        calls.corrections.append((attempt, previous.text))
        return DummyOutput(text="Hallo Welt " * 10)

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=2)
    output, result = _run_guard(
        runner,
        lambda value: value.text,
        "de",
        config=config,
        reprompt=reprompt,
        correct=correct,
    )

    assert len(calls.corrections) == 1  # correct was called
    assert len(calls.reprompts) == 0  # reprompt was NOT called
    assert result.passed is True


def test_backward_compat_reprompt_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Existing reprompt-only callers still work without correct callback."""
    detections = [("fr", 0.9), ("en", 0.9)]

    def fake_detect(_: str) -> tuple[str | None, float | None]:
        return detections.pop(0)

    monkeypatch.setattr(language_guard, "detect_language", fake_detect)

    calls = CallTracker()

    async def runner() -> DummyOutput:
        calls.runner += 1
        return DummyOutput(text="x" * 10)

    def reprompt(attempt: int) -> None:
        calls.reprompts.append(attempt)

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=2)
    _, result = _run_guard(
        runner,
        lambda value: value.text,
        "en",
        config=config,
        reprompt=reprompt,
    )

    assert calls.runner == 2
    assert calls.reprompts == [1]
    assert result.passed is True


@dataclass
class CorrectionNotification:
    expected: str
    detected: str
    attempt: int


@dataclass
class NotificationTracker:
    notifications: list[CorrectionNotification] = field(default_factory=list)


def _run_guard_with_on_correction(
    runner: Callable[[], DummyOutput | Awaitable[DummyOutput]],
    extract_text: Callable[[DummyOutput], str],
    expected_language: str,
    config: language_guard.LanguageGuardConfig | None = None,
    reprompt: Callable[[int], None] | None = None,
    correct: Callable[[int, DummyOutput], DummyOutput | Awaitable[DummyOutput]] | None = None,
    on_correction: Callable[[str, str, int], None] | None = None,
) -> tuple[DummyOutput, language_guard.LanguageGuardResult]:
    return asyncio.run(
        language_guard.run_with_language_guard(
            runner,
            extract_text,
            expected_language,
            config=config,
            reprompt=reprompt,
            correct=correct,
            on_correction=on_correction,
        )
    )


def test_on_correction_callback_invoked(monkeypatch: pytest.MonkeyPatch) -> None:
    """on_correction callback is invoked with (expected, detected, attempt) before correction."""
    detections = [("fr", 0.9), ("de", 0.9)]

    def fake_detect(_: str) -> tuple[str | None, float | None]:
        return detections.pop(0)

    monkeypatch.setattr(language_guard, "detect_language", fake_detect)

    tracker = NotificationTracker()

    async def runner() -> DummyOutput:
        return DummyOutput(text="Bonjour le monde" * 5)

    async def correct(attempt: int, previous: DummyOutput) -> DummyOutput:
        return DummyOutput(text="Hallo Welt " * 10)

    def on_correction(expected: str, detected: str, attempt: int) -> None:
        tracker.notifications.append(CorrectionNotification(expected, detected, attempt))

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=2)
    _, result = _run_guard_with_on_correction(
        runner,
        lambda value: value.text,
        "de",
        config=config,
        correct=correct,
        on_correction=on_correction,
    )

    assert len(tracker.notifications) == 1
    notification = tracker.notifications[0]
    assert notification.expected == "de"
    assert notification.detected == "fr"
    assert notification.attempt == 1
    assert result.passed is True


def test_on_correction_not_called_when_match(monkeypatch: pytest.MonkeyPatch) -> None:
    """on_correction callback is not invoked when language matches on first attempt."""
    monkeypatch.setattr(language_guard, "detect_language", lambda _: ("en", 0.95))

    tracker = NotificationTracker()

    async def runner() -> DummyOutput:
        return DummyOutput(text="x" * 10)

    def on_correction(expected: str, detected: str, attempt: int) -> None:
        tracker.notifications.append(CorrectionNotification(expected, detected, attempt))

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=2)
    _, result = _run_guard_with_on_correction(
        runner,
        lambda value: value.text,
        "en",
        config=config,
        on_correction=on_correction,
    )

    assert len(tracker.notifications) == 0
    assert result.passed is True


def test_on_correction_called_on_each_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    """on_correction callback is invoked before each retry attempt."""
    # First: French, correction: French, second runner: French, second correction: German
    detections = [("fr", 0.9), ("fr", 0.9), ("fr", 0.9), ("de", 0.9)]

    def fake_detect(_: str) -> tuple[str | None, float | None]:
        return detections.pop(0)

    monkeypatch.setattr(language_guard, "detect_language", fake_detect)

    tracker = NotificationTracker()
    correction_count = 0

    async def runner() -> DummyOutput:
        return DummyOutput(text="Bonjour " * 10)

    async def correct(attempt: int, previous: DummyOutput) -> DummyOutput:
        nonlocal correction_count
        correction_count += 1
        if correction_count <= 1:
            return DummyOutput(text="Encore français " * 10)
        return DummyOutput(text="Hallo Welt " * 10)

    def on_correction(expected: str, detected: str, attempt: int) -> None:
        tracker.notifications.append(CorrectionNotification(expected, detected, attempt))

    config = language_guard.LanguageGuardConfig(min_chars=1, min_confidence=0.5, max_retries=3)
    _, result = _run_guard_with_on_correction(
        runner,
        lambda value: value.text,
        "de",
        config=config,
        correct=correct,
        on_correction=on_correction,
    )

    # Should have been called twice: once before each correction attempt
    assert len(tracker.notifications) == 2
    assert tracker.notifications[0].attempt == 1
    assert tracker.notifications[1].attempt == 2
    assert result.passed is True
