"""Tests for build progress display with dual timer."""

from __future__ import annotations

import io
import time
from unittest.mock import MagicMock

from rich.console import Console

from fabulae.features.build.progress import BuildProgress, UnitDualTimeColumn, maybe_task


class TestUnitDualTimeColumn:
    """Tests for UnitDualTimeColumn custom progress column."""

    def test_format_time_seconds(self) -> None:
        """Formats seconds as M:SS."""
        column = UnitDualTimeColumn(lambda: 0.0, lambda: 0.0)
        assert column._format_time(5.0) == "0:05"
        assert column._format_time(45.0) == "0:45"

    def test_format_time_minutes(self) -> None:
        """Formats minutes as M:SS."""
        column = UnitDualTimeColumn(lambda: 0.0, lambda: 0.0)
        assert column._format_time(65.0) == "1:05"
        assert column._format_time(125.0) == "2:05"
        assert column._format_time(599.0) == "9:59"

    def test_format_time_hours(self) -> None:
        """Formats hours as H:MM:SS."""
        column = UnitDualTimeColumn(lambda: 0.0, lambda: 0.0)
        assert column._format_time(3600.0) == "1:00:00"
        assert column._format_time(3661.0) == "1:01:01"
        assert column._format_time(7325.0) == "2:02:05"

    def test_render_dual_time(self) -> None:
        """Shows unit_time / total_time format."""
        unit_time = 15.0
        total_time = 150.0

        column = UnitDualTimeColumn(lambda: unit_time, lambda: total_time)

        # Create a mock task for rendering
        mock_task = MagicMock()
        mock_task.elapsed = 0.0  # Not used since we provide getters

        text = column.render(mock_task)
        rendered = str(text)

        assert "0:15" in rendered  # Unit time
        assert "2:30" in rendered  # Total time
        assert "/" in rendered


class TestBuildProgress:
    """Tests for BuildProgress class."""

    def test_start_sets_start_time(self) -> None:
        """start() initializes the total timer."""
        progress = BuildProgress()
        assert progress._start_time is None

        progress.start()

        assert progress._start_time is not None
        assert progress._start_time > 0

    def test_start_unit_resets_unit_time(self) -> None:
        """start_unit() resets the unit timer."""
        progress = BuildProgress()
        progress.start()

        # Let some time pass
        time.sleep(0.01)
        progress.start_unit()
        first_unit_start = progress._unit_start_time

        # Let more time pass
        time.sleep(0.01)
        progress.start_unit()
        second_unit_start = progress._unit_start_time

        assert first_unit_start is not None
        assert second_unit_start is not None
        assert second_unit_start > first_unit_start

    def test_unit_time_independent_of_total(self) -> None:
        """Unit elapsed time is independent of total elapsed time."""
        progress = BuildProgress()
        progress.start()
        time.sleep(0.02)

        progress.start_unit()
        unit_elapsed = progress._get_unit_elapsed()
        total_elapsed = progress._get_total_elapsed()

        # Total should be greater since it started before unit
        assert total_elapsed > unit_elapsed
        # Unit should be very small (just started)
        assert unit_elapsed < 0.01

    def test_task_context_manager(self) -> None:
        """task() context manager works with spinner."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True)
        progress = BuildProgress(console=console)
        progress.start()

        with progress.task("Testing..."):
            # Just verify it doesn't crash
            pass

        # Context manager should complete without error
        assert True

    def test_print_status_outputs_dim_line(self) -> None:
        """print_status() outputs a dim status line."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=80)
        progress = BuildProgress(console=console)

        progress.print_status("Building scene 1/12: scene-01")

        result = output.getvalue()
        assert "Building scene 1/12: scene-01" in result

    def test_success_message(self) -> None:
        """success() outputs a green checkmark message."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=80)
        progress = BuildProgress(console=console)

        progress.success("Build complete")

        result = output.getvalue()
        assert "Build complete" in result

    def test_warn_message(self) -> None:
        """warn() outputs a yellow warning message."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=80)
        progress = BuildProgress(console=console)

        progress.warn("Small model detected")

        result = output.getvalue()
        assert "Small model detected" in result

    def test_error_message(self) -> None:
        """error() outputs a red error message."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=80)
        progress = BuildProgress(console=console)

        progress.error("Build failed")

        result = output.getvalue()
        assert "Build failed" in result

    def test_info_message(self) -> None:
        """info() outputs a blue info message."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=False, width=80)
        progress = BuildProgress(console=console)

        progress.info("Building novel: Test Novel")

        result = output.getvalue()
        assert "Building novel: Test Novel" in result

    def test_console_property(self) -> None:
        """console property returns the console instance."""
        console = Console()
        progress = BuildProgress(console=console)

        assert progress.console is console

    def test_get_total_elapsed_before_start(self) -> None:
        """_get_total_elapsed returns 0 before start() is called."""
        progress = BuildProgress()

        assert progress._get_total_elapsed() == 0.0

    def test_get_unit_elapsed_before_start_unit(self) -> None:
        """_get_unit_elapsed returns 0 before start_unit() is called."""
        progress = BuildProgress()
        progress.start()

        assert progress._get_unit_elapsed() == 0.0


class TestMaybeTask:
    """Tests for maybe_task helper function."""

    def test_maybe_task_with_progress(self) -> None:
        """maybe_task wraps task() when progress is provided."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True)
        progress = BuildProgress(console=console)
        progress.start()

        executed = False
        with maybe_task(progress, "Testing..."):
            executed = True

        assert executed

    def test_maybe_task_without_progress(self) -> None:
        """maybe_task is a no-op when progress is None."""
        executed = False
        with maybe_task(None, "Testing..."):
            executed = True

        assert executed

    def test_maybe_task_exception_propagates(self) -> None:
        """maybe_task propagates exceptions from the wrapped code."""
        output = io.StringIO()
        console = Console(file=output, force_terminal=True)
        progress = BuildProgress(console=console)
        progress.start()

        class TestError(Exception):
            pass

        try:
            with maybe_task(progress, "Testing..."):
                raise TestError("test")
        except TestError:
            pass  # Expected
        else:
            raise AssertionError("Exception should have propagated")


class TestBuildProgressProtocolCompatibility:
    """Tests for BuildProgress protocol compatibility."""

    def test_has_console_attribute(self) -> None:
        """BuildProgress has console attribute for ProgressCallback protocol."""
        progress = BuildProgress()
        assert hasattr(progress, "console")
        assert isinstance(progress.console, Console)

    def test_has_warn_method(self) -> None:
        """BuildProgress has warn method for callbacks."""
        progress = BuildProgress()
        assert hasattr(progress, "warn")
        assert callable(progress.warn)

    def test_has_info_method(self) -> None:
        """BuildProgress has info method for callbacks."""
        progress = BuildProgress()
        assert hasattr(progress, "info")
        assert callable(progress.info)
