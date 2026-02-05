"""Unit tests for the composed guards module."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import BaseModel

from fabulae.llm import LLMConfig
from fabulae.llm.guards import GuardsConfig, GuardsResult, run_with_guards
from fabulae.llm.json_guard import JsonErrorType, JsonGuardConfig
from fabulae.llm.language_guard import LanguageGuardConfig


class SimpleOutput(BaseModel):
    content: str


@dataclass
class CallTracker:
    runner_calls: int = 0
    language_corrections: list[tuple[str, str, int]] = field(default_factory=list)
    json_errors: list[tuple[JsonErrorType, str, int]] = field(default_factory=list)


def _run_guards(
    result_type: type[Any],
    system_prompt: str,
    user_prompt: str,
    llm_config: LLMConfig,
    runner_results: list[Any],
    extract_text: Callable[[Any], str],
    expected_language: str | None = None,
    config: GuardsConfig | None = None,
    on_language_correction: Callable[[str, str, int], None] | None = None,
    on_json_error: Callable[[JsonErrorType, str, int], None] | None = None,
) -> tuple[Any, GuardsResult, CallTracker]:
    """Helper to run the guards synchronously for testing."""
    tracker = CallTracker()
    result_iter = iter(runner_results)

    async def runner() -> Any:
        tracker.runner_calls += 1
        result = next(result_iter)
        if isinstance(result, Exception):
            raise result
        return result

    def _on_language(expected: str, detected: str, attempt: int) -> None:
        tracker.language_corrections.append((expected, detected, attempt))
        if on_language_correction:
            on_language_correction(expected, detected, attempt)

    def _on_json(error_type: JsonErrorType, error_msg: str, attempt: int) -> None:
        tracker.json_errors.append((error_type, error_msg, attempt))
        if on_json_error:
            on_json_error(error_type, error_msg, attempt)

    output, guards_result = asyncio.run(
        run_with_guards(
            runner=runner,
            result_type=result_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_config=llm_config,
            extract_text=extract_text,
            expected_language=expected_language,
            config=config,
            on_language_correction=_on_language,
            on_json_error=_on_json,
        )
    )
    return output, guards_result, tracker


@pytest.fixture
def llm_config() -> LLMConfig:
    """Minimal LLM config for tests."""
    return LLMConfig(model="test-model", base_url="http://localhost:11434/v1")


class TestRunWithGuards:
    """Tests for run_with_guards function."""

    def test_no_guards_configured_passes_through(self, llm_config: LLMConfig) -> None:
        """When no guards are configured, output passes through."""
        output = SimpleOutput(content="Hello world")
        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            expected_language=None,  # No language guard
            config=None,  # Default config
        )
        assert result == output
        assert guards_result.language.skipped is True
        assert guards_result.json.skipped is True
        assert tracker.runner_calls == 1

    def test_json_guard_only_success(self, llm_config: LLMConfig) -> None:
        """JSON guard alone with successful output."""
        output = SimpleOutput(content="Hello")
        config = GuardsConfig(
            language=None,
            json=JsonGuardConfig(max_retries=2),
        )
        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            config=config,
        )
        assert result == output
        assert guards_result.json.passed is True
        assert guards_result.json.attempts == 1

    def test_json_guard_retries_on_error(self, llm_config: LLMConfig) -> None:
        """JSON guard retries on JSON errors."""
        json_error = ValueError("Unexpected end of JSON input")
        success_output = SimpleOutput(content="Fixed")
        config = GuardsConfig(json=JsonGuardConfig(max_retries=2))

        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[json_error, success_output],
            extract_text=lambda o: o.content,
            config=config,
        )

        assert result == success_output
        assert guards_result.json.passed is True
        assert guards_result.json.attempts == 2
        assert len(tracker.json_errors) == 1

    def test_language_guard_only_success(self, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Language guard alone with matching language."""
        from fabulae.llm import language_guard

        monkeypatch.setattr(language_guard, "detect_language", lambda _: ("en", 0.95))

        output = SimpleOutput(content="x" * 300)  # Long enough for detection
        config = GuardsConfig(
            language=LanguageGuardConfig(min_chars=50, min_confidence=0.5),
            json=None,
        )
        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            expected_language="en",
            config=config,
        )

        assert result == output
        assert guards_result.language.passed is True
        assert len(tracker.language_corrections) == 0

    def test_language_guard_skips_when_no_expected_language(self, llm_config: LLMConfig) -> None:
        """Language guard skips when no expected language provided."""
        output = SimpleOutput(content="Hello")
        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            expected_language=None,
        )

        assert result == output
        assert guards_result.language.skipped is True
        assert guards_result.language.reason == "missing_expected_language"

    def test_both_guards_together_success(self, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Both guards work together on successful output."""
        from fabulae.llm import language_guard

        monkeypatch.setattr(language_guard, "detect_language", lambda _: ("en", 0.95))

        output = SimpleOutput(content="x" * 300)
        config = GuardsConfig(
            language=LanguageGuardConfig(min_chars=50, min_confidence=0.5),
            json=JsonGuardConfig(max_retries=2),
        )
        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            expected_language="en",
            config=config,
        )

        assert result == output
        assert guards_result.json.passed is True
        assert guards_result.language.passed is True
        assert tracker.runner_calls == 1

    def test_json_guard_runs_first_then_language(self, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """JSON guard catches errors first, then language checks."""
        from fabulae.llm import language_guard

        monkeypatch.setattr(language_guard, "detect_language", lambda _: ("en", 0.95))

        json_error = ValueError("Unexpected end of JSON input")
        success_output = SimpleOutput(content="x" * 300)
        config = GuardsConfig(
            language=LanguageGuardConfig(min_chars=50, min_confidence=0.5),
            json=JsonGuardConfig(max_retries=2),
        )

        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[json_error, success_output],
            extract_text=lambda o: o.content,
            expected_language="en",
            config=config,
        )

        # JSON error handled first
        assert len(tracker.json_errors) == 1
        # Then language checked on successful result
        assert guards_result.language.passed is True

    def test_callbacks_invoked_in_correct_order(self, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch) -> None:
        """Callbacks are invoked: JSON errors first, then language corrections."""
        from fabulae.llm import language_guard

        # First call: JSON error, second call: wrong language, third call: correct language
        detections = [("fr", 0.9), ("en", 0.95)]

        def fake_detect(_: str) -> tuple[str | None, float | None]:
            return detections.pop(0)

        monkeypatch.setattr(language_guard, "detect_language", fake_detect)

        json_error = ValueError("Unexpected end of JSON")
        wrong_lang_output = SimpleOutput(content="Bonjour le monde" + "x" * 300)
        correct_output = SimpleOutput(content="Hello world" + "x" * 300)

        callback_order: list[str] = []

        def on_json(error_type: JsonErrorType, msg: str, attempt: int) -> None:
            callback_order.append(f"json:{attempt}")

        def on_language(expected: str, detected: str, attempt: int) -> None:
            callback_order.append(f"language:{attempt}")

        config = GuardsConfig(
            language=LanguageGuardConfig(min_chars=50, min_confidence=0.5, max_retries=2),
            json=JsonGuardConfig(max_retries=2),
        )

        # Note: This test simulates the scenario where:
        # 1. First runner call raises JSON error -> retry
        # 2. Second call succeeds with wrong language -> correct callback, retry with reprompt
        # 3. Third call succeeds with correct language
        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[json_error, wrong_lang_output, correct_output],
            extract_text=lambda o: o.content,
            expected_language="en",
            config=config,
            on_json_error=on_json,
            on_language_correction=on_language,
        )

        # JSON error comes first
        assert "json:1" in callback_order
        # Then language correction after JSON succeeds
        assert "language:1" in callback_order
        # Verify order
        assert callback_order.index("json:1") < callback_order.index("language:1")

    def test_on_json_error_callback_not_called_on_success(self, llm_config: LLMConfig) -> None:
        """on_json_error callback is not invoked when JSON is valid."""
        output = SimpleOutput(content="Hello")
        callback_called = []

        def on_json(error_type: JsonErrorType, msg: str, attempt: int) -> None:
            callback_called.append(error_type)

        config = GuardsConfig(json=JsonGuardConfig(max_retries=2))
        _, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            config=config,
            on_json_error=on_json,
        )

        assert len(callback_called) == 0
        assert guards_result.json.passed is True

    def test_on_language_correction_callback_not_called_on_match(
        self, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """on_language_correction callback is not invoked when language matches."""
        from fabulae.llm import language_guard

        monkeypatch.setattr(language_guard, "detect_language", lambda _: ("en", 0.95))

        output = SimpleOutput(content="x" * 300)
        callback_called = []

        def on_language(expected: str, detected: str, attempt: int) -> None:
            callback_called.append((expected, detected))

        config = GuardsConfig(language=LanguageGuardConfig(min_chars=50, min_confidence=0.5))
        _, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            expected_language="en",
            config=config,
            on_language_correction=on_language,
        )

        assert len(callback_called) == 0
        assert guards_result.language.passed is True

    def test_default_config_creates_disabled_guards(self, llm_config: LLMConfig) -> None:
        """Default GuardsConfig disables both guards (skipped results)."""
        output = SimpleOutput(content="Hello")
        result, guards_result, tracker = _run_guards(
            result_type=SimpleOutput,
            system_prompt="test",
            user_prompt="test",
            llm_config=llm_config,
            runner_results=[output],
            extract_text=lambda o: o.content,
            config=None,  # Uses default
        )

        assert result == output
        # By default, guards should pass through (skip)
        assert guards_result.json.skipped is True
        assert guards_result.language.skipped is True
