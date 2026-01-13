"""Graceful shutdown handler for create command.

This module provides signal handling to save partial generation state
when the program is interrupted (SIGINT/SIGTERM).
"""

from __future__ import annotations

import signal
import sys
from collections.abc import Callable
from contextlib import contextmanager
from pathlib import Path
from types import FrameType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

    from fabulae.features.create.progress import CreateProgress
    from fabulae.features.create.state import GenerationState

# Type alias for signal handlers
SignalHandler = Callable[[int, FrameType | None], Any] | int | None


class ShutdownHandler:
    """Handles graceful shutdown for create command.

    Installs signal handlers for SIGINT and SIGTERM that save partial
    generation state before exiting.
    """

    def __init__(
        self,
        state: GenerationState,
        output_dir: Path,
        progress: CreateProgress | None = None,
    ) -> None:
        """Initialize shutdown handler.

        Args:
            state: Generation state to save on shutdown
            output_dir: Directory for partial output files
            progress: Optional progress reporter for user feedback
        """
        self.state = state
        self.output_dir = output_dir
        self.progress = progress
        self._original_sigint: SignalHandler = None
        self._original_sigterm: SignalHandler = None

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        """Handle termination signal by saving partial state.

        Args:
            signum: Signal number received
            frame: Current stack frame (unused)
        """
        if self.progress:
            self.progress.warn("Interrupted! Saving partial results...")

        partial_dir = self.state.write_partial(self.output_dir)

        if self.progress:
            self.progress.info(f"Partial results saved to {partial_dir}")
            self.progress.info(f"Stage reached: {self.state.current_stage}")

        # Exit with appropriate code: 128 + signal number
        sys.exit(130 if signum == signal.SIGINT else 143)

    def install(self) -> None:
        """Install signal handlers."""
        self._original_sigint = signal.signal(signal.SIGINT, self._handle_signal)
        self._original_sigterm = signal.signal(signal.SIGTERM, self._handle_signal)

    def uninstall(self) -> None:
        """Restore original signal handlers."""
        if self._original_sigint is not None:
            signal.signal(signal.SIGINT, self._original_sigint)
        if self._original_sigterm is not None:
            signal.signal(signal.SIGTERM, self._original_sigterm)


@contextmanager
def graceful_shutdown(
    state: GenerationState,
    output_dir: Path,
    progress: CreateProgress | None = None,
) -> Generator[None, None, None]:
    """Context manager for graceful shutdown handling.

    Usage:
        state = GenerationState(idea=idea, format_name=format)
        with graceful_shutdown(state, output_dir, progress):
            # Generation code that updates state as it progresses
            state.current_stage = "generating_characters"
            ...

    Args:
        state: Generation state to save on shutdown
        output_dir: Directory for partial output files
        progress: Optional progress reporter for user feedback

    Yields:
        None - just provides context management
    """
    handler = ShutdownHandler(state, output_dir, progress)
    handler.install()
    try:
        yield
    finally:
        handler.uninstall()


__all__ = ["ShutdownHandler", "graceful_shutdown"]
