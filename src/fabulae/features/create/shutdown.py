"""Graceful shutdown handler for create command.

This module provides signal handling for graceful shutdown during
generation. When the program is interrupted (SIGINT/SIGTERM), partial
results are written to disk for debugging and potential resumption.
"""

from __future__ import annotations

import signal
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from types import FrameType

    from fabulae.features.create.progress import CreateProgress
    from fabulae.features.create.state import GenerationState


class ShutdownHandler:
    """Handles graceful shutdown for create command.

    Installs signal handlers for SIGINT and SIGTERM that save partial
    generation state to disk before exiting.
    """

    def __init__(
        self,
        state: GenerationState,
        output_dir: Path,
        progress: CreateProgress | None = None,
    ) -> None:
        """Initialize the shutdown handler.

        Args:
            state: The generation state to save on shutdown.
            output_dir: Directory to write partial results to.
            progress: Optional progress reporter for user feedback.
        """
        self.state = state
        self.output_dir = output_dir
        self.progress = progress
        self._original_sigint: signal.Handlers | None = None
        self._original_sigterm: signal.Handlers | None = None

    def _handle_signal(self, signum: int, frame: FrameType | None) -> None:
        """Handle termination signal by saving partial state.

        Args:
            signum: The signal number received.
            frame: The current stack frame (unused).
        """
        if self.progress:
            self.progress.warn("Interrupted! Saving partial results...")

        partial_dir = self.state.write_partial(self.output_dir)

        if self.progress:
            self.progress.info(f"Partial results saved to {partial_dir}")
            self.progress.info(f"Stage reached: {self.state.current_stage}")

        # Exit with standard signal exit codes
        sys.exit(130 if signum == signal.SIGINT else 143)

    def install(self) -> None:
        """Install signal handlers for graceful shutdown."""
        prev_sigint = signal.signal(signal.SIGINT, self._handle_signal)
        prev_sigterm = signal.signal(signal.SIGTERM, self._handle_signal)
        self._original_sigint = prev_sigint  # type: ignore[assignment]
        self._original_sigterm = prev_sigterm  # type: ignore[assignment]

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

    Installs signal handlers for the duration of the context, then
    restores original handlers on exit.

    Args:
        state: The generation state to save on shutdown.
        output_dir: Directory to write partial results to.
        progress: Optional progress reporter for user feedback.

    Yields:
        None
    """
    handler = ShutdownHandler(state, output_dir, progress)
    handler.install()
    try:
        yield
    finally:
        handler.uninstall()


__all__ = ["ShutdownHandler", "graceful_shutdown"]
