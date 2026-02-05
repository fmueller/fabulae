"""Model detection utilities and guard configuration."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from fabulae.llm.json_guard import JsonErrorType, JsonGuardConfig

# Patterns that indicate a small model that may struggle with structured output
SMALL_MODEL_PATTERNS = [
    r"[:\-](\d+(?:\.\d+)?)b\b",  # Matches :1.7b, :3b, :10b, -7b, etc.
    r"mini",
    r"tiny",
    r"small",
]

# Threshold for "small" model in billions of parameters
SMALL_MODEL_THRESHOLD_B = 13

# Retry counts for JSON guard
DEFAULT_JSON_RETRIES = 2
SMALL_MODEL_JSON_RETRIES = 4


def is_small_model(model_name: str) -> bool:
    """Check if a model name suggests it's a small model (<13B parameters).

    Args:
        model_name: The model name to check (e.g., "llama:7b", "gpt-4o-mini").

    Returns:
        True if the model appears to be small (<13B parameters), False otherwise.
    """
    model_lower = model_name.lower()
    for pattern in SMALL_MODEL_PATTERNS:
        match = re.search(pattern, model_lower)
        if match:
            # For numeric patterns, check if < threshold
            if match.lastindex and match.lastindex >= 1:
                try:
                    size = float(match.group(1))
                    if size < SMALL_MODEL_THRESHOLD_B:
                        return True
                except ValueError:
                    pass
            else:
                # Non-numeric patterns like "mini", "tiny", "small"
                return True
    return False


def get_json_retries(model_name: str) -> int:
    """Get the appropriate number of JSON retries for a model.

    Args:
        model_name: The model name to check.

    Returns:
        Number of retries (4 for small models, 2 for large models).
    """
    return SMALL_MODEL_JSON_RETRIES if is_small_model(model_name) else DEFAULT_JSON_RETRIES


def get_json_guard_config(model_name: str) -> JsonGuardConfig:
    """Get JSON guard configuration appropriate for the model size.

    Args:
        model_name: The model name to check.

    Returns:
        JsonGuardConfig with appropriate retry count.
    """
    return JsonGuardConfig(max_retries=get_json_retries(model_name))


# Protocol for progress callbacks (avoids circular import with CreateProgress)
@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for progress notification callbacks."""

    def info(self, message: str) -> None:
        """Display an info message."""
        ...


def make_json_error_callback(
    progress: ProgressCallback | None,
    max_retries: int,
) -> Callable[[JsonErrorType, str, int], None] | None:
    """Create a callback to notify user of JSON error retries.

    Args:
        progress: Progress display object with info() method, or None.
        max_retries: Maximum number of retries for display in message.

    Returns:
        Callback function or None if progress is None.
    """
    if progress is None:
        return None

    def notify(error_type: JsonErrorType, _error_msg: str, attempt: int) -> None:
        progress.info(f"JSON error ({error_type.name}), retrying (attempt {attempt}/{max_retries})...")

    return notify


def make_language_correction_callback(
    progress: ProgressCallback | None,
) -> Callable[[str, str, int], None] | None:
    """Create a callback to notify user of language correction attempts.

    Args:
        progress: Progress display object with info() method, or None.

    Returns:
        Callback function or None if progress is None.
    """
    if progress is None:
        return None

    def notify(expected: str, detected: str, attempt: int) -> None:
        progress.info(f"Language mismatch (expected: {expected}, got: {detected}), correcting (attempt {attempt})...")

    return notify


__all__ = [
    "DEFAULT_JSON_RETRIES",
    "SMALL_MODEL_JSON_RETRIES",
    "SMALL_MODEL_PATTERNS",
    "SMALL_MODEL_THRESHOLD_B",
    "get_json_guard_config",
    "get_json_retries",
    "is_small_model",
    "make_json_error_callback",
    "make_language_correction_callback",
]
