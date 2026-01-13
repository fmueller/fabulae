# Task: Graceful Shutdown Hook for Intermediate Output

**Priority:** Medium - improves resilience and debugging experience.
**Depends on:** None

## Overview

Add a shutdown hook to the `create` command that writes intermediate output files to `.fabulae-create/` when the program is forcibly terminated (Ctrl+C, SIGTERM, etc.). Currently, if generation is interrupted, all progress is lost. This task ensures partial results are preserved for debugging and potential resumption.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Current Behavior

When `fabulae create` is interrupted:
1. Any in-memory state (generated characters, scenes, etc.) is lost
2. Intermediate artifacts are only written at specific checkpoints
3. User has no visibility into what was generated before interruption
4. Must restart generation from scratch

## Proposed Behavior

When `fabulae create` is interrupted:
1. Signal handler catches SIGINT/SIGTERM
2. Current generation state is written to `.fabulae-create/partial/`
3. User sees message: "Interrupted. Partial results saved to .fabulae-create/partial/"
4. Partial results can be inspected for debugging
5. (Future) `--resume` flag could continue from partial state

## Implementation Steps

### Step 1: Create State Container for Pipeline
**Model: Sonnet**

Create a dataclass to hold in-progress generation state in `src/fabulae/features/create/state.py`:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from fabulae.features.create.schemas import StyleOutput
    from fabulae.models import Character, Scene, WorldFact


@dataclass
class GenerationState:
    """Holds in-progress generation state for graceful shutdown."""

    idea: str = ""
    format_name: str = ""
    premise: str | None = None
    style: StyleOutput | None = None
    characters: list[Character] = field(default_factory=list)
    locations: list[WorldFact] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    chapters: list[dict] = field(default_factory=list)
    current_stage: str = "initializing"

    def write_partial(self, output_dir: Path) -> Path:
        """Write current state to partial output directory."""
        partial_dir = output_dir / ".fabulae-create" / "partial"
        partial_dir.mkdir(parents=True, exist_ok=True)

        # Write state.yml with current progress
        state_file = partial_dir / "state.yml"
        state_data = {
            "idea": self.idea,
            "format": self.format_name,
            "current_stage": self.current_stage,
            "progress": {
                "premise": self.premise is not None,
                "style": self.style is not None,
                "characters": len(self.characters),
                "locations": len(self.locations),
                "scenes": len(self.scenes),
                "chapters": len(self.chapters),
            },
        }
        state_file.write_text(yaml.safe_dump(state_data, default_flow_style=False))

        # Write entities if they exist
        if self.premise:
            (partial_dir / "premise.yml").write_text(
                yaml.safe_dump({"premise": self.premise}, default_flow_style=False)
            )

        if self.style:
            (partial_dir / "style.yml").write_text(
                yaml.safe_dump(self.style.model_dump(exclude_none=True), default_flow_style=False)
            )

        if self.characters:
            chars_data = [c.model_dump(exclude_none=True) for c in self.characters]
            (partial_dir / "characters.yml").write_text(
                yaml.safe_dump(chars_data, default_flow_style=False)
            )

        if self.locations:
            locs_data = [loc.model_dump(exclude_none=True) for loc in self.locations]
            (partial_dir / "locations.yml").write_text(
                yaml.safe_dump(locs_data, default_flow_style=False)
            )

        if self.scenes:
            scenes_data = [s.model_dump(exclude_none=True) for s in self.scenes]
            (partial_dir / "scenes.yml").write_text(
                yaml.safe_dump(scenes_data, default_flow_style=False)
            )

        return partial_dir
```

**Files to create:**
- `src/fabulae/features/create/state.py`

**Acceptance criteria:**
- GenerationState dataclass created
- write_partial() method writes state to disk
- All entity types handled

### Step 2: Add Shutdown Handler
**Model: Sonnet**

Create shutdown handler in `src/fabulae/features/create/shutdown.py`:

```python
from __future__ import annotations

import signal
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from fabulae.features.create.progress import CreateProgress
    from fabulae.features.create.state import GenerationState


class ShutdownHandler:
    """Handles graceful shutdown for create command."""

    def __init__(
        self,
        state: GenerationState,
        output_dir: Path,
        progress: CreateProgress | None = None,
    ) -> None:
        self.state = state
        self.output_dir = output_dir
        self.progress = progress
        self._original_sigint = None
        self._original_sigterm = None

    def _handle_signal(self, signum: int, frame: object) -> None:
        """Handle termination signal by saving partial state."""
        if self.progress:
            self.progress.warn("Interrupted! Saving partial results...")

        partial_dir = self.state.write_partial(self.output_dir)

        if self.progress:
            self.progress.info(f"Partial results saved to {partial_dir}")
            self.progress.info(f"Stage reached: {self.state.current_stage}")

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
    """Context manager for graceful shutdown handling."""
    handler = ShutdownHandler(state, output_dir, progress)
    handler.install()
    try:
        yield
    finally:
        handler.uninstall()
```

**Files to create:**
- `src/fabulae/features/create/shutdown.py`

**Acceptance criteria:**
- Signal handlers installed and restored properly
- Partial state written on interrupt
- User-friendly messages displayed

### Step 3: Integrate State Tracking into Sequential Pipeline
**Model: Sonnet**

Update `src/fabulae/features/create/pipelines/sequential.py` to use GenerationState:

```python
# At the start of generate_prose_sequential()
from fabulae.features.create.state import GenerationState
from fabulae.features.create.shutdown import graceful_shutdown

async def generate_prose_sequential(...):
    state = GenerationState(idea=idea, format_name=format)

    with graceful_shutdown(state, artifacts_dir or Path.cwd(), progress):
        # Update state.current_stage as we progress
        state.current_stage = "generating_style"
        style = await generate_style(...)
        state.style = style

        state.current_stage = "generating_premise"
        premise = await generate_premise(...)
        state.premise = premise

        state.current_stage = "generating_characters"
        for char in characters:
            state.characters.append(char)

        # ... continue pattern for other stages
```

**Files to modify:**
- `src/fabulae/features/create/pipelines/sequential.py`
- `src/fabulae/features/create/pipelines/prose.py`
- `src/fabulae/features/create/pipelines/micro_prose.py`
- `src/fabulae/features/create/pipelines/micro_prose_sequential.py`
- `src/fabulae/features/create/pipelines/poem.py`
- `src/fabulae/features/create/pipelines/poem_sequential.py`

**Acceptance criteria:**
- All pipelines track state
- State updated after each generation step
- Graceful shutdown context manager wraps generation

### Step 4: Write Tests
**Model: Sonnet**

Create `tests/unit/features/create/shutdown_test.py`:

```python
import signal
from pathlib import Path

import pytest

from fabulae.features.create.state import GenerationState
from fabulae.features.create.shutdown import ShutdownHandler


def test_generation_state_write_partial(tmp_path: Path) -> None:
    state = GenerationState(
        idea="test idea",
        format_name="novel",
        premise="A test premise",
        current_stage="generating_characters",
    )
    partial_dir = state.write_partial(tmp_path)

    assert (partial_dir / "state.yml").exists()
    assert (partial_dir / "premise.yml").exists()


def test_shutdown_handler_installs_signals() -> None:
    state = GenerationState()
    handler = ShutdownHandler(state, Path("/tmp"))

    handler.install()
    assert signal.getsignal(signal.SIGINT) == handler._handle_signal

    handler.uninstall()
    # Original handler restored
```

**Files to create:**
- `tests/unit/features/create/shutdown_test.py`

**Acceptance criteria:**
- State writing tested
- Signal handler installation tested
- Partial output structure validated

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - Error handling is appropriate
   - Type hints are complete

2. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass

3. **Manual Testing:**
   - Start `fabulae create` and press Ctrl+C mid-generation
   - Verify partial output is written
   - Check output structure is valid YAML

4. **Documentation Review:**
   - Update README.md if needed (document partial output behavior)
   - Update CLAUDE.md if architectural patterns changed

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/create/state.py` | Create | Generation state container |
| `src/fabulae/features/create/shutdown.py` | Create | Shutdown handler |
| `src/fabulae/features/create/pipelines/sequential.py` | Modify | Integrate state tracking |
| `src/fabulae/features/create/pipelines/prose.py` | Modify | Integrate state tracking |
| `src/fabulae/features/create/pipelines/micro_prose.py` | Modify | Integrate state tracking |
| `src/fabulae/features/create/pipelines/micro_prose_sequential.py` | Modify | Integrate state tracking |
| `src/fabulae/features/create/pipelines/poem.py` | Modify | Integrate state tracking |
| `src/fabulae/features/create/pipelines/poem_sequential.py` | Modify | Integrate state tracking |
| `tests/unit/features/create/shutdown_test.py` | Create | Unit tests |

## Acceptance Criteria

- [ ] GenerationState tracks all in-progress entities
- [ ] Shutdown handler catches SIGINT and SIGTERM
- [ ] Partial results written to `.fabulae-create/partial/`
- [ ] User sees helpful message on interrupt
- [ ] All pipelines integrated with state tracking
- [ ] Tests pass for shutdown handling
- [ ] All checks pass (`ruff`, `mypy`, `pytest`)

## Output Structure

When interrupted, the following is written:

```
my-project/
└── .fabulae-create/
    └── partial/
        ├── state.yml       # Progress summary
        ├── premise.yml     # If generated
        ├── style.yml       # If generated
        ├── characters.yml  # Characters generated so far
        ├── locations.yml   # Locations generated so far
        └── scenes.yml      # Scenes generated so far
```

## Future Enhancement

A `--resume` flag could use partial state to continue generation:

```bash
fabulae create ./my-project --resume  # Continue from partial state
```

This is out of scope for this task but documented for future implementation.
