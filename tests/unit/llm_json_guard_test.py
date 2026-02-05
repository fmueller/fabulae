"""Unit tests for the JSON guard."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import pytest
from pydantic import BaseModel

from fabulae.llm.json_guard import (
    JsonErrorType,
    JsonGuardConfig,
    JsonGuardResult,
    classify_json_error,
    run_with_json_guard,
)


class SimpleOutput(BaseModel):
    content: str


class ComplexOutput(BaseModel):
    name: str
    count: int


@dataclass
class CallTracker:
    runner_calls: int = 0
    error_callbacks: list[tuple[JsonErrorType, str, int]] = field(default_factory=list)


def _run_guard(
    result_type: type[Any],
    system_prompt: str,
    user_prompt: str,
    runner_results: list[Any],
    config: JsonGuardConfig | None = None,
    on_error: Any = None,
) -> tuple[Any, JsonGuardResult, CallTracker]:
    """Helper to run the JSON guard synchronously for testing."""
    tracker = CallTracker()
    result_iter = iter(runner_results)

    async def runner() -> Any:
        tracker.runner_calls += 1
        result = next(result_iter)
        if isinstance(result, Exception):
            raise result
        return result

    def _on_error(error_type: JsonErrorType, error_msg: str, attempt: int) -> None:
        tracker.error_callbacks.append((error_type, error_msg, attempt))
        if on_error:
            on_error(error_type, error_msg, attempt)

    output, guard_result = asyncio.run(
        run_with_json_guard(
            runner=runner,
            result_type=result_type,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            config=config,
            on_error=_on_error,
        )
    )
    return output, guard_result, tracker


# --- classify_json_error tests ---


class TestClassifyJsonError:
    """Tests for classify_json_error function."""

    def test_truncated_json_unexpected_end(self) -> None:
        """Truncated JSON with 'unexpected end' message."""
        exc = ValueError("Unexpected end of JSON input")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.TRUNCATED

    def test_truncated_json_unterminated_string(self) -> None:
        """Truncated JSON with unterminated string."""
        exc = ValueError("Unterminated string starting at position 42")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.TRUNCATED

    def test_markdown_wrapped_json(self) -> None:
        """JSON wrapped in markdown code blocks."""
        exc = ValueError("Unexpected token '`' at position 0")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.MARKDOWN_WRAPPED

    def test_markdown_wrapped_json_prefix(self) -> None:
        """JSON with ```json prefix."""
        exc = ValueError("Content starts with markdown code fence: ```json")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.MARKDOWN_WRAPPED

    def test_preamble_text_looking_for_beginning(self) -> None:
        """Preamble text before JSON - looking for beginning of value."""
        exc = ValueError("invalid character 'â' looking for beginning of value")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.PREAMBLE_TEXT

    def test_preamble_text_expected_at_start(self) -> None:
        """Preamble text before JSON - expected at start."""
        exc = ValueError("expected '{' at start of JSON")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.PREAMBLE_TEXT

    def test_unescaped_newline_in_string(self) -> None:
        """Unescaped newline character in string literal."""
        exc = ValueError("invalid character '\\n' in string literal")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.UNESCAPED_CHARS

    def test_unescaped_control_character(self) -> None:
        """Unescaped control character in string."""
        exc = ValueError("control character in string at position 42")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.UNESCAPED_CHARS

    def test_invalid_syntax_trailing_comma(self) -> None:
        """Invalid JSON with trailing comma."""
        exc = ValueError("Trailing comma before closing brace")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.INVALID_SYNTAX

    def test_invalid_syntax_expecting_value(self) -> None:
        """Invalid JSON expecting value."""
        exc = ValueError("Expecting value: line 1 column 1")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.INVALID_SYNTAX

    def test_schema_mismatch_missing_field(self) -> None:
        """Schema mismatch with missing required field."""
        exc = ValueError("Field required: 'name' is a required field")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.SCHEMA_MISMATCH

    def test_schema_mismatch_wrong_type(self) -> None:
        """Schema mismatch with wrong field type."""
        exc = ValueError("Input should be a valid integer, got string")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.SCHEMA_MISMATCH

    def test_validation_error_pydantic(self) -> None:
        """Pydantic validation error."""
        exc = ValueError("validation error for SimpleOutput")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.VALIDATION_ERROR

    def test_unknown_error(self) -> None:
        """Unknown error type defaults to INVALID_SYNTAX."""
        exc = RuntimeError("Some random error")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.INVALID_SYNTAX

    def test_empty_response_nil_content_type(self) -> None:
        """Empty response with nil content type."""
        exc = ValueError("invalid message content type: <nil>")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.EMPTY_RESPONSE

    def test_empty_response_no_content(self) -> None:
        """Empty response with no content message."""
        exc = ValueError("no content in response")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.EMPTY_RESPONSE

    def test_empty_response_empty_message(self) -> None:
        """Empty response with empty message content."""
        exc = ValueError("message content is empty")
        error_type, _ = classify_json_error(exc)
        assert error_type == JsonErrorType.EMPTY_RESPONSE

    def test_extracts_error_message(self) -> None:
        """Error message is extracted from exception."""
        exc = ValueError("Something went wrong")
        _, error_msg = classify_json_error(exc)
        assert "Something went wrong" in error_msg


# --- run_with_json_guard tests ---


class TestRunWithJsonGuard:
    """Tests for run_with_json_guard function."""

    def test_success_first_attempt(self) -> None:
        """Successful generation on first attempt."""
        output = SimpleOutput(content="Hello")
        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[output],
        )
        assert result == output
        assert guard_result.passed is True
        assert guard_result.skipped is False
        assert guard_result.attempts == 1
        assert guard_result.error_type is None
        assert tracker.runner_calls == 1

    def test_retry_on_truncated_error(self) -> None:
        """Retries on truncated JSON error."""
        truncated_error = ValueError("Unexpected end of JSON input")
        success_output = SimpleOutput(content="Fixed")

        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[truncated_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert guard_result.attempts == 2
        assert tracker.runner_calls == 2
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.TRUNCATED

    def test_retry_on_markdown_wrapped(self) -> None:
        """Retries on markdown wrapped JSON."""
        markdown_error = ValueError("Content starts with markdown: ```json")
        success_output = SimpleOutput(content="Fixed")

        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[markdown_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.MARKDOWN_WRAPPED

    def test_retry_on_preamble_text(self) -> None:
        """Retries on preamble text before JSON."""
        preamble_error = ValueError("invalid character 'â' looking for beginning of value")
        success_output = SimpleOutput(content="Fixed")

        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[preamble_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.PREAMBLE_TEXT

    def test_retry_on_unescaped_chars(self) -> None:
        """Retries on unescaped characters in JSON strings."""
        unescaped_error = ValueError("invalid character '\\n' in string literal")
        success_output = SimpleOutput(content="Fixed")

        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[unescaped_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.UNESCAPED_CHARS

    def test_retry_on_invalid_syntax(self) -> None:
        """Retries on invalid JSON syntax."""
        syntax_error = ValueError("Trailing comma before closing brace")
        success_output = SimpleOutput(content="Fixed")

        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[syntax_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.INVALID_SYNTAX

    def test_retry_on_schema_mismatch(self) -> None:
        """Retries on schema mismatch."""
        schema_error = ValueError("Field required: 'name'")
        success_output = ComplexOutput(name="test", count=5)

        result, guard_result, tracker = _run_guard(
            result_type=ComplexOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[schema_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.SCHEMA_MISMATCH

    def test_retry_on_validation_error(self) -> None:
        """Retries on Pydantic validation error."""
        validation_error = ValueError("validation error for ComplexOutput")
        success_output = ComplexOutput(name="test", count=5)

        result, guard_result, tracker = _run_guard(
            result_type=ComplexOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[validation_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.VALIDATION_ERROR

    def test_max_retries_exceeded(self) -> None:
        """Raises exception when max retries exceeded."""
        error = ValueError("Unexpected end of JSON input")

        with pytest.raises(ValueError, match="Unexpected end"):
            _run_guard(
                result_type=SimpleOutput,
                system_prompt="test system",
                user_prompt="test user",
                runner_results=[error, error, error],
                config=JsonGuardConfig(max_retries=2),
            )

    def test_on_error_callback_invoked(self) -> None:
        """on_error callback is invoked with correct arguments."""
        error = ValueError("Unexpected end of JSON input")
        success_output = SimpleOutput(content="Fixed")

        callback_data: list[tuple[JsonErrorType, str, int]] = []

        def on_error(error_type: JsonErrorType, error_msg: str, attempt: int) -> None:
            callback_data.append((error_type, error_msg, attempt))

        _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[error, success_output],
            config=JsonGuardConfig(max_retries=2),
            on_error=on_error,
        )

        assert len(callback_data) == 1
        assert callback_data[0][0] == JsonErrorType.TRUNCATED
        assert "Unexpected end" in callback_data[0][1]
        assert callback_data[0][2] == 1  # attempt number

    def test_multiple_retries_callback_each_attempt(self) -> None:
        """on_error callback is invoked for each retry attempt."""
        error1 = ValueError("Unexpected end of JSON input")
        error2 = ValueError("Trailing comma")
        success_output = SimpleOutput(content="Fixed")

        _, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[error1, error2, success_output],
            config=JsonGuardConfig(max_retries=3),
        )

        assert len(tracker.error_callbacks) == 2
        assert tracker.error_callbacks[0][2] == 1  # first attempt
        assert tracker.error_callbacks[1][2] == 2  # second attempt
        assert guard_result.attempts == 3

    def test_default_config_used_when_none(self) -> None:
        """Default config is used when config is None."""
        error = ValueError("Unexpected end")
        success_output = SimpleOutput(content="Fixed")

        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[error, success_output],
            config=None,  # Uses default
        )

        assert result == success_output
        assert guard_result.passed is True

    def test_retry_on_empty_response(self) -> None:
        """Retries on empty response error."""
        empty_error = ValueError("invalid message content type: <nil>")
        success_output = SimpleOutput(content="Fixed")

        result, guard_result, tracker = _run_guard(
            result_type=SimpleOutput,
            system_prompt="test system",
            user_prompt="test user",
            runner_results=[empty_error, success_output],
            config=JsonGuardConfig(max_retries=2),
        )

        assert result == success_output
        assert guard_result.passed is True
        assert len(tracker.error_callbacks) == 1
        assert tracker.error_callbacks[0][0] == JsonErrorType.EMPTY_RESPONSE
