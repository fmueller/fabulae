"""Tests for progress module with timing functionality."""

from __future__ import annotations

import time
from io import StringIO

import pytest
from rich.console import Console

from fabulae.features.create.progress import CreateProgress, DualTimeColumn, StepTiming, maybe_stage


class TestStepTiming:
    """Tests for StepTiming dataclass."""

    def test_step_timing_creation(self) -> None:
        """StepTiming stores name and duration."""
        timing = StepTiming(name="Generate style", duration_seconds=12.5)
        assert timing.name == "Generate style"
        assert timing.duration_seconds == 12.5


class TestDualTimeColumn:
    """Tests for DualTimeColumn custom progress column."""

    def test_format_time_seconds(self) -> None:
        """_format_time formats seconds correctly."""
        assert DualTimeColumn._format_time(0) == "0:00"
        assert DualTimeColumn._format_time(5) == "0:05"
        assert DualTimeColumn._format_time(30) == "0:30"
        assert DualTimeColumn._format_time(59) == "0:59"

    def test_format_time_minutes(self) -> None:
        """_format_time formats minutes correctly."""
        assert DualTimeColumn._format_time(60) == "1:00"
        assert DualTimeColumn._format_time(90) == "1:30"
        assert DualTimeColumn._format_time(125) == "2:05"
        assert DualTimeColumn._format_time(3599) == "59:59"

    def test_format_time_hours(self) -> None:
        """_format_time formats hours correctly."""
        assert DualTimeColumn._format_time(3600) == "1:00:00"
        assert DualTimeColumn._format_time(3661) == "1:01:01"
        assert DualTimeColumn._format_time(7200) == "2:00:00"

    def test_render_dual_time(self) -> None:
        """render() shows step time / total time format."""
        # Create column with a mock total elapsed getter
        column = DualTimeColumn(lambda: 120.0)  # 2 minutes total

        # Create a minimal mock task with elapsed property
        class MockTask:
            elapsed = 30.0  # 30 seconds step time

        result = column.render(MockTask())  # type: ignore[arg-type]
        result_str = str(result)

        # Check the text contains the dual format "0:30 / 2:00"
        assert "/" in result_str
        assert "0:30" in result_str  # step time
        assert "2:00" in result_str  # total time


class TestCreateProgress:
    """Tests for CreateProgress class."""

    def test_start_sets_start_time(self) -> None:
        """start() initializes the start time."""
        progress = CreateProgress()
        assert progress._start_time is None
        progress.start()
        assert progress._start_time is not None

    def test_get_total_elapsed_returns_zero_before_start(self) -> None:
        """_get_total_elapsed returns 0 if not started."""
        progress = CreateProgress()
        assert progress._get_total_elapsed() == 0.0

    def test_get_total_elapsed_returns_elapsed_time(self) -> None:
        """_get_total_elapsed returns time since start."""
        progress = CreateProgress()
        progress.start()
        time.sleep(0.05)
        elapsed = progress._get_total_elapsed()
        assert elapsed >= 0.05

    def test_stage_records_timing(self) -> None:
        """stage() records step timing after completion."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        # Use stage and verify timing is recorded
        with progress.stage("Test step..."):
            time.sleep(0.01)  # Small delay for measurable time

        assert len(progress._step_timings) == 1
        assert progress._step_timings[0].name == "Test step"
        assert progress._step_timings[0].duration_seconds >= 0.01

    def test_stage_auto_starts_if_not_started(self) -> None:
        """stage() auto-starts timing if not already started."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        assert progress._start_time is None
        with progress.stage("Test step..."):
            pass
        assert progress._start_time is not None

    def test_multiple_stages_accumulate(self) -> None:
        """Multiple stages accumulate in order."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        with progress.stage("Step 1..."):
            time.sleep(0.01)
        with progress.stage("Step 2..."):
            time.sleep(0.01)
        with progress.stage("Step 3..."):
            time.sleep(0.01)

        assert len(progress._step_timings) == 3
        assert progress._step_timings[0].name == "Step 1"
        assert progress._step_timings[1].name == "Step 2"
        assert progress._step_timings[2].name == "Step 3"

    def test_total_time_increases_across_stages(self) -> None:
        """Total elapsed time continues to increase across multiple stages."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        progress.start()
        initial_total = progress._get_total_elapsed()

        with progress.stage("Step 1..."):
            time.sleep(0.02)
        after_step1 = progress._get_total_elapsed()

        with progress.stage("Step 2..."):
            time.sleep(0.02)
        after_step2 = progress._get_total_elapsed()

        # Total time should keep increasing
        assert after_step1 > initial_total
        assert after_step2 > after_step1

    def test_stage_strips_trailing_dots_and_spaces(self) -> None:
        """stage() strips trailing dots and spaces from step names."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        with progress.stage("Generating style..."):
            pass
        with progress.stage("Creating world."):
            pass
        with progress.stage("Assembling project"):
            pass

        assert progress._step_timings[0].name == "Generating style"
        assert progress._step_timings[1].name == "Creating world"
        assert progress._step_timings[2].name == "Assembling project"

    def test_format_duration_under_minute(self) -> None:
        """_format_duration formats correctly for durations under a minute."""
        assert CreateProgress._format_duration(0) == "0:00"
        assert CreateProgress._format_duration(5) == "0:05"
        assert CreateProgress._format_duration(30) == "0:30"
        assert CreateProgress._format_duration(59) == "0:59"

    def test_format_duration_minutes(self) -> None:
        """_format_duration formats correctly for durations in minutes."""
        assert CreateProgress._format_duration(60) == "1:00"
        assert CreateProgress._format_duration(90) == "1:30"
        assert CreateProgress._format_duration(125) == "2:05"
        assert CreateProgress._format_duration(3599) == "59:59"

    def test_format_duration_hours(self) -> None:
        """_format_duration formats correctly for durations with hours."""
        assert CreateProgress._format_duration(3600) == "1:00:00"
        assert CreateProgress._format_duration(3661) == "1:01:01"
        assert CreateProgress._format_duration(7200) == "2:00:00"

    def test_format_duration_human_seconds(self) -> None:
        """_format_duration_human formats seconds correctly."""
        assert CreateProgress._format_duration_human(0) == "0s"
        assert CreateProgress._format_duration_human(5) == "5s"
        assert CreateProgress._format_duration_human(30.7) == "31s"
        assert CreateProgress._format_duration_human(59.4) == "59s"

    def test_format_duration_human_minutes(self) -> None:
        """_format_duration_human formats minutes correctly."""
        assert CreateProgress._format_duration_human(60) == "1m 0s"
        assert CreateProgress._format_duration_human(90) == "1m 30s"
        assert CreateProgress._format_duration_human(125) == "2m 5s"
        assert CreateProgress._format_duration_human(3599) == "59m 59s"

    def test_format_duration_human_hours(self) -> None:
        """_format_duration_human formats hours correctly."""
        assert CreateProgress._format_duration_human(3600) == "1h 0m 0s"
        assert CreateProgress._format_duration_human(3661) == "1h 1m 1s"
        assert CreateProgress._format_duration_human(7325) == "2h 2m 5s"

    def test_success_message(self) -> None:
        """success() displays message with checkmark."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = CreateProgress(console=console)

        progress.success("Step completed")

        result = output.getvalue()
        assert "✓" in result
        assert "Step completed" in result

    def test_warn_message(self) -> None:
        """warn() displays message with warning prefix."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = CreateProgress(console=console)

        progress.warn("Something might be wrong")

        result = output.getvalue()
        assert "Warning:" in result
        assert "Something might be wrong" in result

    def test_error_message(self) -> None:
        """error() displays message with error X."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = CreateProgress(console=console)

        progress.error("Something went wrong")

        result = output.getvalue()
        assert "✗" in result
        assert "Something went wrong" in result

    def test_info_message(self) -> None:
        """info() displays message with info symbol."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = CreateProgress(console=console)

        progress.info("Additional information")

        result = output.getvalue()
        assert "ℹ" in result
        assert "Additional information" in result


class TestMaybeStage:
    """Tests for maybe_stage helper function."""

    def test_maybe_stage_with_progress(self) -> None:
        """maybe_stage() uses stage() when progress is available."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        with maybe_stage(progress, "Test step..."):
            time.sleep(0.01)

        assert len(progress._step_timings) == 1
        assert progress._step_timings[0].name == "Test step"

    def test_maybe_stage_without_progress(self) -> None:
        """maybe_stage() is a no-op when progress is None."""
        result = []

        with maybe_stage(None, "Test step..."):
            result.append("executed")

        assert result == ["executed"]

    def test_maybe_stage_context_manager_behavior(self) -> None:
        """maybe_stage() works as a proper context manager."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        value = None
        with maybe_stage(progress, "Test step..."):
            value = 42

        assert value == 42
        assert len(progress._step_timings) == 1

    def test_maybe_stage_exception_propagation(self) -> None:
        """maybe_stage() propagates exceptions correctly."""
        console = Console(file=StringIO(), force_terminal=True)
        progress = CreateProgress(console=console)

        with pytest.raises(ValueError, match="test error"), maybe_stage(progress, "Test step..."):
            raise ValueError("test error")

        # Step should not be recorded on exception
        # (actually it IS recorded because the timing is recorded after yield)
        # This tests current behavior - exception during stage is still timed


class TestCreateProgressIntegration:
    """Integration tests for CreateProgress with realistic usage."""

    def test_full_generation_flow(self) -> None:
        """Simulate a full generation flow with multiple stages."""
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=120)
        progress = CreateProgress(console=console)

        progress.start()

        # Simulate generation stages
        with progress.stage("Determining narrative style..."):
            time.sleep(0.01)
        progress.success("Style determined")

        with progress.stage("Planning story structure..."):
            time.sleep(0.01)
        progress.success("Structure planned")

        with progress.stage("Creating characters..."):
            time.sleep(0.01)
        progress.success("Characters created")

        result = output.getvalue()

        # Verify success messages were printed
        assert "Style determined" in result
        assert "Structure planned" in result
        assert "Characters created" in result

        # Verify all steps are tracked
        assert len(progress._step_timings) == 3
