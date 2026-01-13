"""Tests for create CLI functions."""

import pytest

from fabulae.features.create.cli import _SMALL_MODEL_THRESHOLD_B, _is_small_model


class TestIsSmallModel:
    """Tests for _is_small_model function."""

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
        assert _is_small_model(model_name) == expected, f"Expected {expected} for {model_name}"

    def test_threshold_is_13b(self) -> None:
        """Test that the threshold is set to 13B."""
        assert _SMALL_MODEL_THRESHOLD_B == 13
