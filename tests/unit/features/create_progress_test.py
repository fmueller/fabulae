"""Tests for create progress display."""

from io import StringIO

from rich.console import Console

from fabulae.features.create.progress import CreateProgress, StepTiming


def test_create_progress_success() -> None:
    """Test success message display."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)

    progress.success("Project created successfully")

    output = buffer.getvalue()
    assert "Project created successfully" in output


def test_create_progress_error() -> None:
    """Test error message display."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)

    progress.error("Generation failed")

    output = buffer.getvalue()
    assert "Generation failed" in output


def test_create_progress_warn() -> None:
    """Test warning message display."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)

    progress.warn("Count outside expected range")

    output = buffer.getvalue()
    assert "Warning:" in output
    assert "Count outside expected range" in output


def test_create_progress_info() -> None:
    """Test info message display."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)

    progress.info("5 characters, 10 scenes")

    output = buffer.getvalue()
    # Rich may add formatting/colors, so we check for the content without ANSI codes
    assert "characters" in output
    assert "scenes" in output


def test_create_progress_stage() -> None:
    """Test stage context manager."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)

    with progress.stage("Generating project"):
        pass

    # Stage output is transient, so we can't easily verify it in tests
    # This test mainly ensures the context manager works without errors
    output = buffer.getvalue()
    # Transient progress is cleared, so output may be empty or contain escape sequences
    assert isinstance(output, str)


def test_step_timing_recorded() -> None:
    """Test that step timing is recorded after stage completion."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)
    progress.start()

    with progress.stage("Generating style..."):
        pass  # Simulated work

    assert len(progress._step_timings) == 1
    assert progress._step_timings[0].name == "Generating style"
    assert progress._step_timings[0].duration_seconds >= 0


def test_step_timing_strips_dots() -> None:
    """Test that step name strips trailing dots."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)
    progress.start()

    with progress.stage("Planning structure..."):
        pass

    assert progress._step_timings[0].name == "Planning structure"


def test_multiple_steps_recorded() -> None:
    """Test that multiple steps are all recorded."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)
    progress.start()

    with progress.stage("Step 1..."):
        pass
    with progress.stage("Step 2..."):
        pass
    with progress.stage("Step 3..."):
        pass

    assert len(progress._step_timings) == 3
    assert [s.name for s in progress._step_timings] == ["Step 1", "Step 2", "Step 3"]


def test_format_duration_human() -> None:
    """Test human-readable duration formatting."""
    assert CreateProgress._format_duration_human(0) == "0s"
    assert CreateProgress._format_duration_human(45) == "45s"
    assert CreateProgress._format_duration_human(59) == "59s"
    assert CreateProgress._format_duration_human(60) == "1m 0s"
    assert CreateProgress._format_duration_human(90) == "1m 30s"
    assert CreateProgress._format_duration_human(3599) == "59m 59s"
    assert CreateProgress._format_duration_human(3600) == "1h 0m 0s"
    assert CreateProgress._format_duration_human(3661) == "1h 1m 1s"


def test_format_duration() -> None:
    """Test M:SS and H:MM:SS duration formatting."""
    assert CreateProgress._format_duration(0) == "0:00"
    assert CreateProgress._format_duration(45) == "0:45"
    assert CreateProgress._format_duration(59) == "0:59"
    assert CreateProgress._format_duration(60) == "1:00"
    assert CreateProgress._format_duration(90) == "1:30"
    assert CreateProgress._format_duration(3599) == "59:59"
    assert CreateProgress._format_duration(3600) == "1:00:00"
    assert CreateProgress._format_duration(3661) == "1:01:01"


def test_success_with_duration() -> None:
    """Test that success message includes step duration after a stage."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)
    progress.start()

    with progress.stage("Generating style..."):
        pass

    progress.success("Style determined")

    output = buffer.getvalue()
    assert "Style determined" in output
    # Duration should be shown - 0s is expected since test is fast
    # Rich may add formatting codes around parentheses, so check for the number with 's'
    assert "0s" in output


def test_print_summary_empty() -> None:
    """Test that print_summary does nothing when no steps recorded."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)

    progress.print_summary()

    # No output expected when there are no step timings
    output = buffer.getvalue()
    assert "Generation Summary" not in output


def test_print_summary_with_steps() -> None:
    """Test that print_summary displays step timings."""
    buffer = StringIO()
    console = Console(file=buffer, force_terminal=True, width=120)
    progress = CreateProgress(console=console)
    progress.start()

    with progress.stage("Style..."):
        pass
    with progress.stage("Premise..."):
        pass
    with progress.stage("Characters..."):
        pass

    progress.print_summary()

    output = buffer.getvalue()
    assert "Generation Summary" in output
    assert "Style" in output
    assert "Premise" in output
    assert "Characters" in output
    assert "Total" in output


def test_step_timing_dataclass() -> None:
    """Test StepTiming dataclass."""
    timing = StepTiming(name="Test step", duration_seconds=42.5)
    assert timing.name == "Test step"
    assert timing.duration_seconds == 42.5


def test_start_initializes_time() -> None:
    """Test that start() initializes the start time."""
    progress = CreateProgress()
    assert progress._start_time is None

    progress.start()
    assert progress._start_time is not None


def test_stage_auto_starts_if_not_started() -> None:
    """Test that stage() auto-initializes start time if not called."""
    progress = CreateProgress()
    assert progress._start_time is None

    with progress.stage("Test stage"):
        pass

    assert progress._start_time is not None
