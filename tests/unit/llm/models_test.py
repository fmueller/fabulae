"""Tests for model detection utilities."""

import pytest

from fabulae.llm.json_guard import JsonGuardConfig
from fabulae.llm.models import (
    DEFAULT_JSON_RETRIES,
    SMALL_MODEL_JSON_RETRIES,
    SMALL_MODEL_THRESHOLD_B,
    get_json_guard_config,
    get_json_retries,
    is_small_model,
    make_json_error_callback,
    make_language_correction_callback,
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


class TestGetJsonRetries:
    """Tests for get_json_retries function."""

    def test_small_model_gets_more_retries(self) -> None:
        """Small models get 4 retries."""
        assert get_json_retries("llama:7b") == SMALL_MODEL_JSON_RETRIES
        assert get_json_retries("gpt-4o-mini") == SMALL_MODEL_JSON_RETRIES

    def test_large_model_gets_default_retries(self) -> None:
        """Large models get 2 retries."""
        assert get_json_retries("llama:70b") == DEFAULT_JSON_RETRIES
        assert get_json_retries("gpt-4-turbo") == DEFAULT_JSON_RETRIES

    def test_retry_constants(self) -> None:
        """Verify retry constants are correct."""
        assert DEFAULT_JSON_RETRIES == 2
        assert SMALL_MODEL_JSON_RETRIES == 4


class TestGetJsonGuardConfig:
    """Tests for get_json_guard_config function."""

    def test_returns_config_with_correct_retries(self) -> None:
        """Returns JsonGuardConfig with appropriate retry count."""
        small_config = get_json_guard_config("llama:7b")
        assert isinstance(small_config, JsonGuardConfig)
        assert small_config.max_retries == 4

        large_config = get_json_guard_config("llama:70b")
        assert isinstance(large_config, JsonGuardConfig)
        assert large_config.max_retries == 2


class TestMakeJsonErrorCallback:
    """Tests for make_json_error_callback function."""

    def test_returns_none_when_no_progress(self) -> None:
        """Returns None when progress is None."""
        callback = make_json_error_callback(None, 4)
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
        callback = make_json_error_callback(progress, 4)
        assert callback is not None

        callback(JsonErrorType.PREAMBLE_TEXT, "error", 2)
        assert len(progress.messages) == 1
        assert "PREAMBLE_TEXT" in progress.messages[0]
        assert "2/4" in progress.messages[0]


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
