"""Tests for model detection utilities."""

import pytest

from fabulae.llm.models import (
    SMALL_MODEL_THRESHOLD_B,
    is_small_model,
    make_json_error_callback,
    make_language_correction_callback,
    small_model_message,
)


class TestIsSmallModel:
    """Tests for is_small_model function."""

    @pytest.mark.parametrize(
        "model_name,expected",
        [
            # Single digit sizes (should be small)
            ("ministral-3:3b", True),
            ("model:7b", True),
            ("qwen2:1b", True),
            # Decimal sizes (should be small)
            ("model:1.7b", True),
            ("llama:3.5b", True),
            ("phi:2.7b", True),
            # Double digit sizes under threshold (should be small)
            ("qwen2:10b", True),
            ("model:12b", True),
            # At or above threshold (should not be small)
            ("llama:13b", False),
            ("model:14b", False),
            ("ministral-3:14b", False),  # Bug fix: explicit 14b >= 13B, ignore "mini" in name
            ("llama:70b", False),
            ("model:405b", False),
            # Keyword-based detection
            ("gpt-4o-mini", True),
            ("claude-3-haiku", False),  # "haiku" is not in patterns
            ("tiny-llama", True),
            ("small-model", True),
            # Edge cases
            ("ministral-3b", True),  # hyphen separator
            ("model-7b-instruct", True),  # hyphen separator with suffix
            ("model:7B", True),  # uppercase B
            ("model:7b-q4", True),  # quantization suffix
            # Not matching patterns (should not be small)
            ("gpt-4-turbo", False),
            ("claude-3-opus", False),
            ("llama-instruct", False),  # no size indicator
        ],
    )
    def test_is_small_model(self, model_name: str, expected: bool) -> None:
        """Test small model detection for various model names."""
        assert is_small_model(model_name) == expected, f"Expected {expected} for {model_name}"

    def test_threshold_is_13b(self) -> None:
        """Test that the threshold is set to 13B."""
        assert SMALL_MODEL_THRESHOLD_B == 13


class TestMakeJsonErrorCallback:
    """Tests for make_json_error_callback function."""

    def test_returns_none_when_no_progress(self) -> None:
        """Returns None when progress is None."""
        callback = make_json_error_callback(None, 2)
        assert callback is None

    def test_returns_callable_with_progress(self) -> None:
        """Returns a callable when progress is provided."""
        from fabulae.llm.json_guard import JsonErrorType

        class MockProgress:
            def __init__(self) -> None:
                self.messages: list[str] = []

            def info(self, message: str) -> None:
                self.messages.append(message)

        progress = MockProgress()
        callback = make_json_error_callback(progress, 2)
        assert callback is not None

        callback(JsonErrorType.PREAMBLE_TEXT, "error", 2)
        assert len(progress.messages) == 1
        assert "PREAMBLE_TEXT" in progress.messages[0]
        assert "2/2" in progress.messages[0]


class TestSmallModelMessage:
    """Tests for small_model_message function."""

    def test_single_optimization(self) -> None:
        """Single optimization produces correct message."""
        msg = small_model_message([("sequential pipeline", "--pipeline batch")])
        assert msg == "Small model detected (<13B): using sequential pipeline. Override with --pipeline batch."

    def test_multiple_optimizations(self) -> None:
        """Multiple optimizations are comma-joined, overrides slash-joined."""
        msg = small_model_message(
            [
                ("sequential pipeline", "--pipeline batch"),
                ("enrichment disabled", "--enrich"),
            ]
        )
        assert msg == (
            "Small model detected (<13B): using sequential pipeline, enrichment disabled."
            " Override with --pipeline batch/--enrich."
        )


class TestMakeLanguageCorrectionCallback:
    """Tests for make_language_correction_callback function."""

    def test_returns_none_when_no_progress(self) -> None:
        """Returns None when progress is None."""
        callback = make_language_correction_callback(None)
        assert callback is None

    def test_returns_callable_with_progress(self) -> None:
        """Returns a callable when progress is provided."""

        class MockProgress:
            def __init__(self) -> None:
                self.messages: list[str] = []

            def info(self, message: str) -> None:
                self.messages.append(message)

        progress = MockProgress()
        callback = make_language_correction_callback(progress)
        assert callback is not None

        callback("en", "de", 1)
        assert len(progress.messages) == 1
        assert "en" in progress.messages[0]
        assert "de" in progress.messages[0]
