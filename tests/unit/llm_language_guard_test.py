"""Unit tests for the shared language guard."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import pytest

from fabulae.llm import language_guard


@dataclass
class DummyOutput:
    text: str


@dataclass
class CallTracker:
    runner: int = 0
    reprompts: list[int] | None = None

    def __post_init__(self) -> None:
        if self.reprompts is None:
            self.reprompts = []


def _run_guard(
    runner: Callable[[], DummyOutput | Awaitable[DummyOutput]],
    extract_text: Callable[[DummyOutput], str],
    expected_language: str,
    config: language_guard.LanguageGuardConfig | None = None,
    reprompt: Callable[[int], None] | None = None,
) -> tuple[DummyOutput, language_guard.LanguageGuardResult]:
    return asyncio.run(
        language_guard.run_with_language_guard(
            runner,
            extract_text,
            expected_language,
            config=config,
            reprompt=reprompt,
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
