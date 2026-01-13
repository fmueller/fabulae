# Task: Progress View Improvements

**Priority:** Medium - improves user experience during generation.
**Depends on:** None

## Overview

Improve the progress display in the `create` command to show both per-step timers and an overall elapsed timer. Currently, the progress view only shows elapsed time for the current stage, making it hard to understand total generation time and relative duration of each step.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Current Behavior

```
⠋ Generating style... 0:00:12
✓ Style determined
⠋ Generating premise... 0:00:08
✓ Premise created
⠋ Generating characters... 0:00:45
...
```

Issues:
- No overall timer visible during generation
- After completion, no summary of step durations
- Hard to identify which steps are slow

## Proposed Behavior

### During Generation
```
⠋ Generating style... [step: 0:00:12] [total: 0:00:12]
```

### After Each Step
```
✓ Style determined (12s)
⠋ Generating premise... [step: 0:00:08] [total: 0:00:20]
```

### Final Summary
```
✓ Created Fabulae project in ./my-novel

Generation Summary:
  Style:        12s
  Premise:       8s
  Characters:   45s
  Locations:    23s
  Scenes:      120s (2m 0s)
  ─────────────────
  Total:       208s (3m 28s)
```

## Implementation Steps

### Step 1: Add Step Duration Tracking to CreateProgress
**Model: Sonnet**

Update `src/fabulae/features/create/progress.py`:

```python
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class StepTiming:
    """Timing information for a generation step."""

    name: str
    duration_seconds: float


class CreateProgress:
    """Rich progress display for create command with timing tracking."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._start_time: float | None = None
        self._step_timings: list[StepTiming] = []
        self._current_step_start: float | None = None

    def start(self) -> None:
        """Mark the start of generation."""
        self._start_time = time.monotonic()

    @contextmanager
    def stage(self, description: str) -> Generator[None, None, None]:
        """Context manager for a generation stage with dual timer display."""
        if self._start_time is None:
            self._start_time = time.monotonic()

        self._current_step_start = time.monotonic()
        step_name = description.rstrip("...").strip()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TextColumn("[dim]step:[/dim]"),
            TimeElapsedColumn(),
            TextColumn("[dim]total:[/dim]"),
            TextColumn(self._format_total_elapsed),
            console=self.console,
            transient=True,
        ) as progress:
            progress.add_task(description, total=None)
            yield

        # Record step duration
        step_duration = time.monotonic() - self._current_step_start
        self._step_timings.append(StepTiming(name=step_name, duration_seconds=step_duration))

    def _format_total_elapsed(self) -> str:
        """Format total elapsed time."""
        if self._start_time is None:
            return "0:00:00"
        elapsed = time.monotonic() - self._start_time
        return self._format_duration(elapsed)

    @staticmethod
    def _format_duration(seconds: float) -> str:
        """Format seconds as H:MM:SS or M:SS."""
        minutes, secs = divmod(int(seconds), 60)
        hours, minutes = divmod(minutes, 60)
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    @staticmethod
    def _format_duration_human(seconds: float) -> str:
        """Format seconds as human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        minutes, secs = divmod(int(seconds), 60)
        if minutes < 60:
            return f"{minutes}m {secs}s"
        hours, minutes = divmod(minutes, 60)
        return f"{hours}h {minutes}m {secs}s"

    def success(self, message: str) -> None:
        """Display a success message with step duration."""
        duration_str = ""
        if self._step_timings:
            last_step = self._step_timings[-1]
            duration_str = f" ({self._format_duration_human(last_step.duration_seconds)})"
        self.console.print(f"[green]✓[/green] {message}{duration_str}")

    def warn(self, message: str) -> None:
        """Display a warning message in yellow."""
        self.console.print(f"[yellow]Warning:[/yellow] {message}")

    def error(self, message: str) -> None:
        """Display an error message with red X."""
        self.console.print(f"[red]✗[/red] {message}")

    def info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")

    def print_summary(self) -> None:
        """Print timing summary table."""
        if not self._step_timings:
            return

        self.console.print()
        self.console.print("[bold]Generation Summary:[/bold]")

        table = Table(show_header=False, box=None, padding=(0, 2, 0, 0))
        table.add_column("Step", style="dim")
        table.add_column("Duration", justify="right")

        total_seconds = 0.0
        for step in self._step_timings:
            duration_str = self._format_duration_human(step.duration_seconds)
            table.add_row(f"  {step.name}:", duration_str)
            total_seconds += step.duration_seconds

        # Add separator and total
        table.add_row("  ─" * 10, "─" * 6)
        table.add_row("  Total:", self._format_duration_human(total_seconds))

        self.console.print(table)
```

**Files to modify:**
- `src/fabulae/features/create/progress.py`

**Acceptance criteria:**
- Dual timer display during generation
- Step duration shown on completion
- Summary method available

### Step 2: Integrate Summary into CLI
**Model: Haiku**

Update `src/fabulae/features/create/cli.py` to call summary:

```python
# After successful generation, before final success message
progress.print_summary()
progress.success(f"Created Fabulae project in {directory}")
```

**Files to modify:**
- `src/fabulae/features/create/cli.py`

**Acceptance criteria:**
- Summary printed after successful generation
- Timing information visible to user

### Step 3: Update Pipeline Integration
**Model: Sonnet**

Ensure all pipelines properly use stage() for each generation step. Review and update:

1. Each distinct LLM call should be wrapped in `progress.stage()`
2. Stage descriptions should be consistent across pipelines
3. Success messages should use `progress.success()` for duration tracking

**Files to review/modify:**
- `src/fabulae/features/create/pipelines/sequential.py`
- `src/fabulae/features/create/pipelines/prose.py`
- `src/fabulae/features/create/pipelines/micro_prose.py`
- `src/fabulae/features/create/pipelines/micro_prose_sequential.py`
- `src/fabulae/features/create/pipelines/poem.py`
- `src/fabulae/features/create/pipelines/poem_sequential.py`

**Acceptance criteria:**
- All generation steps tracked
- Consistent stage naming
- No missing timing data

### Step 4: Write Tests
**Model: Sonnet**

Create `tests/unit/features/create/progress_test.py`:

```python
from fabulae.features.create.progress import CreateProgress, StepTiming


def test_step_timing_recorded() -> None:
    progress = CreateProgress()
    progress.start()

    with progress.stage("Generating style..."):
        pass  # Simulated work

    assert len(progress._step_timings) == 1
    assert progress._step_timings[0].name == "Generating style"


def test_format_duration_human() -> None:
    assert CreateProgress._format_duration_human(45) == "45s"
    assert CreateProgress._format_duration_human(90) == "1m 30s"
    assert CreateProgress._format_duration_human(3661) == "1h 1m 1s"


def test_format_duration() -> None:
    assert CreateProgress._format_duration(45) == "0:45"
    assert CreateProgress._format_duration(90) == "1:30"
    assert CreateProgress._format_duration(3661) == "1:01:01"
```

**Files to create:**
- `tests/unit/features/create/progress_test.py`

**Acceptance criteria:**
- Step timing tracking tested
- Duration formatting tested
- Edge cases covered

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - Rich progress integration is correct
   - Type hints are complete

2. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass

3. **Manual Testing:**
   - Run `fabulae create` and observe progress display
   - Verify dual timers are visible
   - Verify summary is printed at end

4. **Documentation Review:**
   - No README changes needed (internal improvement)
   - Update CLAUDE.md if progress patterns changed

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/create/progress.py` | Modify | Add dual timers and summary |
| `src/fabulae/features/create/cli.py` | Modify | Integrate summary printing |
| `src/fabulae/features/create/pipelines/*.py` | Review | Ensure proper stage() usage |
| `tests/unit/features/create/progress_test.py` | Create | Unit tests |

## Acceptance Criteria

- [ ] Progress shows step timer and total timer
- [ ] Success messages include step duration
- [ ] Summary table printed at completion
- [ ] All pipelines properly track timing
- [ ] Tests pass for timing logic
- [ ] All checks pass (`ruff`, `mypy`, `pytest`)

## Example Output

```
ℹ Small model detected (<13B): using enrichment disabled, sequential pipeline.
⠋ Generating style... [step: 0:00:12] [total: 0:00:12]
✓ Style determined (12s)
⠋ Generating premise... [step: 0:00:08] [total: 0:00:20]
✓ Premise expanded (8s)
⠋ Generating character 1/3... [step: 0:00:15] [total: 0:00:35]
✓ Character vera created (15s)
⠋ Generating character 2/3... [step: 0:00:14] [total: 0:00:49]
✓ Character marcus created (14s)
⠋ Generating character 3/3... [step: 0:00:16] [total: 0:01:05]
✓ Character chen created (16s)
...

Generation Summary:
  Style:               12s
  Premise:              8s
  Characters:          45s
  Locations:           23s
  Scenes:             120s
  ──────────────────────────
  Total:              208s (3m 28s)

✓ Created Fabulae project in ./my-novel
ℹ Summary: 3 characters, 12 scenes, 0 fragments, 0 stanzas
```
