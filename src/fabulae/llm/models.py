"""Model detection utilities and guard configuration."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol, runtime_checkable

from fabulae.llm.json_guard import JsonErrorType

# Patterns that indicate a small model that may struggle with structured output
SMALL_MODEL_PATTERNS = [
    r"[:\-](\d+(?:\.\d+)?)b\b",  # Matches :1.7b, :3b, :10b, -7b, etc.
    r"mini",
    r"tiny",
    r"small",
]

# Threshold for "small" model in billions of parameters
SMALL_MODEL_THRESHOLD_B = 13

# Retry count for JSON guard
DEFAULT_JSON_RETRIES = 2


def is_small_model(model_name: str) -> bool:
    """Check if a model name suggests it's a small model (<13B parameters).

    Args:
        model_name: The model name to check (e.g., "llama:7b", "gpt-4o-mini").

    Returns:
        True if the model appears to be small (<13B parameters), False otherwise.
    """
    model_lower = model_name.lower()

    # First, check for explicit size pattern (e.g., :7b, -7b, :1.7b)
    # This is definitive - if we find an explicit size, use it
    size_pattern = SMALL_MODEL_PATTERNS[0]  # r"[:\-](\d+(?:\.\d+)?)b\b"
    match = re.search(size_pattern, model_lower)
    if match and match.lastindex and match.lastindex >= 1:
        try:
            size = float(match.group(1))
            # Explicit size is definitive - return based on threshold
            return size < SMALL_MODEL_THRESHOLD_B
        except ValueError:
            pass

    # No explicit size found - check keyword patterns
    return any(re.search(pattern, model_lower) for pattern in SMALL_MODEL_PATTERNS[1:])


# Protocol for progress callbacks (avoids circular import with CreateProgress)
@runtime_checkable
class ProgressCallback(Protocol):
    """Protocol for progress notification callbacks."""

    def info(self, message: str) -> None:
        """Display an info message."""
        ...

    def warn(self, message: str) -> None:
        """Display a warning message."""
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
        progress.warn(f"JSON error ({error_type.name}), retrying (attempt {attempt}/{max_retries})...")

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
        progress.warn(f"Language mismatch (expected: {expected}, got: {detected}), correcting (attempt {attempt})...")

    return notify


def small_model_message(optimizations: list[tuple[str, str]]) -> str:
    """Build a small model detection info message.

    Args:
        optimizations: List of (description, override_flag) tuples.
            Example: [("sequential pipeline", "--pipeline batch")]

    Returns:
        Formatted message like "Small model detected (<13B): using sequential pipeline. Override with --pipeline batch."
    """
    descriptions = [opt[0] for opt in optimizations]
    overrides = [opt[1] for opt in optimizations]
    msg = f"Small model detected (<{SMALL_MODEL_THRESHOLD_B}B): using {', '.join(descriptions)}."
    if overrides:
        msg += f" Override with {'/'.join(overrides)}."
    return msg


__all__ = [
    "DEFAULT_JSON_RETRIES",
    "SMALL_MODEL_PATTERNS",
    "SMALL_MODEL_THRESHOLD_B",
    "is_small_model",
    "make_json_error_callback",
    "make_language_correction_callback",
    "small_model_message",
]
