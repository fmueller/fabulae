"""Tests for create progress display."""

from io import StringIO

from rich.console import Console

from fabulae.features.create.progress import CreateProgress


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
    assert "⚠" in output
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
