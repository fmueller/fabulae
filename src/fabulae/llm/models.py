"""Model detection utilities."""

from __future__ import annotations

import re

# Patterns that indicate a small model that may struggle with structured output
SMALL_MODEL_PATTERNS = [
    r"[:\-](\d+(?:\.\d+)?)b\b",  # Matches :1.7b, :3b, :10b, -7b, etc.
    r"mini",
    r"tiny",
    r"small",
]

# Threshold for "small" model in billions of parameters
SMALL_MODEL_THRESHOLD_B = 13


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


__all__ = [
    "SMALL_MODEL_PATTERNS",
    "SMALL_MODEL_THRESHOLD_B",
    "is_small_model",
]
