"""Global state for history tracking.

This module provides a simple way to check if history tracking is enabled
without creating circular imports.
"""

# Global state for history tracking
_history_enabled = True


def get_history_enabled() -> bool:
    """Get the current history enabled state.

    Returns:
        True if history tracking is enabled, False otherwise.
    """
    return _history_enabled


def set_history_enabled(enabled: bool) -> None:
    """Set the history enabled state.

    Args:
        enabled: Whether history tracking should be enabled.
    """
    global _history_enabled
    _history_enabled = enabled
