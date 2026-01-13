# Task: Project History System

**Priority:** Low - nice-to-have feature for project management.
**Depends on:** None

## Overview

Implement a project history system using a `.fabulae` folder that tracks all actions performed on a project. This provides:

1. **Action history:** Record of all create, edit, suggest, build operations
2. **Reproducibility:** Ability to understand how a project evolved
3. **Recovery:** Potential to undo or replay actions
4. **Global opt-out:** `--no-history` flag to disable history tracking

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Current State

The user noticed temporary files being created during project creation. These should be:
1. Moved into a dedicated `.fabulae` folder
2. Organized as a proper history/cache system
3. Made optional via global flag

## Proposed Structure

```
my-novel/
├── .fabulae/
│   ├── config.yml           # Local fabulae settings
│   ├── history/
│   │   ├── 2024-01-15_143052_create.json
│   │   ├── 2024-01-15_144530_character_add.json
│   │   ├── 2024-01-15_145012_build.json
│   │   └── ...
│   ├── cache/
│   │   ├── llm_responses/   # Cached LLM responses (optional)
│   │   └── builds/          # Build artifacts
│   └── temp/                # Temporary files during operations
├── fabulae.yml
├── characters.yml
├── world.yml
├── plot.yml
└── ...
```

## Implementation Steps

### Step 1: Create History Data Models
**Model: Sonnet**

Create `src/fabulae/history/models.py`:

```python
from datetime import datetime
from enum import Enum
from pathlib import Path
from pydantic import BaseModel
from typing import Any

class ActionType(str, Enum):
    CREATE = "create"
    BUILD = "build"
    CHECK = "check"
    CHARACTER_ADD = "character_add"
    CHARACTER_EDIT = "character_edit"
    CHARACTER_REMOVE = "character_remove"
    CHARACTER_SUGGEST = "character_suggest"
    SCENE_ADD = "scene_add"
    SCENE_EDIT = "scene_edit"
    SCENE_REMOVE = "scene_remove"
    # ... etc for all entity operations

class HistoryEntry(BaseModel):
    """A single action in project history."""
    id: str  # UUID
    timestamp: datetime
    action: ActionType
    command: str  # Full command line
    parameters: dict[str, Any]  # Command parameters
    result: str  # success, failed, cancelled
    duration_seconds: float | None = None
    error_message: str | None = None
    changes: list[str] | None = None  # List of changed files

class ProjectHistory(BaseModel):
    """Complete history for a project."""
    project_path: Path
    entries: list[HistoryEntry] = []

    def add_entry(self, entry: HistoryEntry) -> None:
        self.entries.append(entry)
        self.save()

    def get_recent(self, limit: int = 10) -> list[HistoryEntry]:
        return sorted(self.entries, key=lambda e: e.timestamp, reverse=True)[:limit]
```

**Files to create:**
- `src/fabulae/history/__init__.py`
- `src/fabulae/history/models.py`

**Acceptance criteria:**
- History entries capture all relevant action information
- Model is serializable to JSON
- Supports all planned action types

### Step 2: Implement History Manager
**Model: Sonnet**

Create `src/fabulae/history/manager.py`:

```python
from pathlib import Path
from datetime import datetime
import json
import uuid
from contextlib import contextmanager
from fabulae.history.models import HistoryEntry, ActionType

FABULAE_DIR = ".fabulae"
HISTORY_DIR = "history"

class HistoryManager:
    """Manages project history in .fabulae folder."""

    def __init__(self, project_path: Path, enabled: bool = True):
        self.project_path = project_path
        self.enabled = enabled
        self.fabulae_dir = project_path / FABULAE_DIR
        self.history_dir = self.fabulae_dir / HISTORY_DIR

    def ensure_dirs(self) -> None:
        """Create .fabulae directory structure if needed."""
        if not self.enabled:
            return
        self.history_dir.mkdir(parents=True, exist_ok=True)
        (self.fabulae_dir / "cache").mkdir(exist_ok=True)
        (self.fabulae_dir / "temp").mkdir(exist_ok=True)

    @contextmanager
    def track_action(
        self,
        action: ActionType,
        command: str,
        parameters: dict,
    ):
        """Context manager to track an action."""
        if not self.enabled:
            yield
            return

        self.ensure_dirs()
        entry_id = str(uuid.uuid4())[:8]
        start_time = datetime.now()
        result = "success"
        error_message = None
        changes = []

        try:
            yield
        except Exception as e:
            result = "failed"
            error_message = str(e)
            raise
        finally:
            duration = (datetime.now() - start_time).total_seconds()
            entry = HistoryEntry(
                id=entry_id,
                timestamp=start_time,
                action=action,
                command=command,
                parameters=parameters,
                result=result,
                duration_seconds=duration,
                error_message=error_message,
                changes=changes if changes else None,
            )
            self._save_entry(entry)

    def _save_entry(self, entry: HistoryEntry) -> None:
        """Save history entry to file."""
        filename = f"{entry.timestamp.strftime('%Y-%m-%d_%H%M%S')}_{entry.action.value}.json"
        filepath = self.history_dir / filename
        filepath.write_text(entry.model_dump_json(indent=2))

    def get_history(self, limit: int | None = None) -> list[HistoryEntry]:
        """Load history entries from disk."""
        if not self.history_dir.exists():
            return []

        entries = []
        for file in sorted(self.history_dir.glob("*.json"), reverse=True):
            try:
                data = json.loads(file.read_text())
                entries.append(HistoryEntry.model_validate(data))
                if limit and len(entries) >= limit:
                    break
            except Exception:
                continue  # Skip corrupted entries

        return entries

    def clear_history(self) -> int:
        """Clear all history entries. Returns count of deleted entries."""
        if not self.history_dir.exists():
            return 0

        count = 0
        for file in self.history_dir.glob("*.json"):
            file.unlink()
            count += 1
        return count
```

**Files to create:**
- `src/fabulae/history/manager.py`

**Acceptance criteria:**
- History manager creates .fabulae structure
- Actions tracked via context manager
- History persisted as JSON files
- History can be loaded and queried

### Step 3: Add Global --no-history Flag
**Model: Sonnet**

Add global flag to main CLI:

```python
# In src/fabulae/main.py

app = typer.Typer()

# Global state for history setting
_history_enabled = True

@app.callback()
def main_callback(
    no_history: Annotated[bool, typer.Option(
        "--no-history",
        help="Disable project history tracking for this command",
        is_eager=True,
    )] = False,
):
    """Fabulae - CLI toolkit for building narratives."""
    global _history_enabled
    _history_enabled = not no_history

def get_history_enabled() -> bool:
    """Get current history enabled state."""
    return _history_enabled
```

**Files to modify:**
- `src/fabulae/main.py`

**Acceptance criteria:**
- `--no-history` available on all commands
- Flag is processed before subcommands run
- History manager respects the flag

### Step 4: Integrate History into Commands
**Model: Sonnet**

Update commands to track their actions:

```python
# Example for create command in src/fabulae/features/create/cli.py

from fabulae.history.manager import HistoryManager
from fabulae.history.models import ActionType
from fabulae.main import get_history_enabled

@app.command()
def create(
    project_dir: Path,
    idea: str,
    format: str,
    ...
):
    history = HistoryManager(project_dir, enabled=get_history_enabled())

    with history.track_action(
        action=ActionType.CREATE,
        command=f"fabulae create {project_dir} --idea '{idea}' --format {format}",
        parameters={
            "idea": idea,
            "format": format,
            "model": model,
            "temperature": temperature,
            # ... other parameters
        },
    ):
        project = generate_project_from_idea(...)
        save_project(project, project_dir)
```

**Files to modify:**
- `src/fabulae/features/create/cli.py`
- `src/fabulae/features/build/cli.py` (when implemented)
- `src/fabulae/features/check/cli.py` (when implemented)
- `src/fabulae/features/entities/*.py` (when implemented)

**Acceptance criteria:**
- Create command tracks action in history
- Build command tracks action in history
- All entity commands track actions
- Failed commands recorded with error

### Step 5: Add History Command
**Model: Sonnet**

Add command to view project history:

```bash
fabulae history ./my-novel              # Show recent history
fabulae history ./my-novel --limit 50   # Show more entries
fabulae history ./my-novel --clear      # Clear history
fabulae history ./my-novel --json       # Output as JSON
```

```python
# In src/fabulae/features/history/cli.py

@app.command()
def history(
    project_dir: Annotated[Path, typer.Argument()],
    limit: Annotated[int, typer.Option("--limit", "-n")] = 10,
    clear: Annotated[bool, typer.Option("--clear")] = False,
    json_output: Annotated[bool, typer.Option("--json")] = False,
):
    """View or manage project history."""
    manager = HistoryManager(project_dir)

    if clear:
        count = manager.clear_history()
        typer.echo(f"Cleared {count} history entries")
        return

    entries = manager.get_history(limit=limit)

    if json_output:
        import json
        typer.echo(json.dumps([e.model_dump() for e in entries], default=str, indent=2))
        return

    # Pretty print history
    console = Console()
    for entry in entries:
        icon = "✓" if entry.result == "success" else "✗"
        color = "green" if entry.result == "success" else "red"
        console.print(f"[{color}]{icon}[/{color}] {entry.timestamp:%Y-%m-%d %H:%M} - {entry.action.value}")
        if entry.duration_seconds:
            console.print(f"    Duration: {entry.duration_seconds:.1f}s")
        if entry.error_message:
            console.print(f"    [red]Error: {entry.error_message}[/red]")
```

**Files to create:**
- `src/fabulae/features/history/__init__.py`
- `src/fabulae/features/history/cli.py`

**Files to modify:**
- `src/fabulae/main.py` - wire history command

**Acceptance criteria:**
- `fabulae history` shows recent actions
- `--limit` controls entry count
- `--clear` removes history
- `--json` outputs machine-readable format

### Step 6: Add .fabulae to .gitignore Template
**Model: Haiku**

Update project templates to include .gitignore:

```gitignore
# .gitignore (in project templates)
.fabulae/
output/
*.pyc
__pycache__/
```

**Files to modify:**
- `templates/novel/.gitignore` (create if not exists)
- `templates/novella/.gitignore`
- `templates/short-story/.gitignore`
- `templates/micro-prose/.gitignore`
- `templates/poem/.gitignore`

**Acceptance criteria:**
- .fabulae folder excluded from version control by default
- Users can override by removing from .gitignore

### Step 7: Clean Up Temp Files
**Model: Haiku**

Ensure temp files go to .fabulae/temp and are cleaned up:

```python
# In src/fabulae/history/manager.py

def get_temp_dir(self) -> Path:
    """Get temp directory, creating if needed."""
    self.ensure_dirs()
    return self.fabulae_dir / "temp"

def clean_temp(self) -> int:
    """Remove all temp files. Returns count deleted."""
    temp_dir = self.fabulae_dir / "temp"
    if not temp_dir.exists():
        return 0

    count = 0
    for file in temp_dir.iterdir():
        if file.is_file():
            file.unlink()
            count += 1
    return count
```

**Files to modify:**
- `src/fabulae/history/manager.py`
- Any code currently creating temp files elsewhere

**Acceptance criteria:**
- All temp files use .fabulae/temp
- Temp files cleaned after operations
- No temp files left in project root

### Step 8: Write Tests
**Model: Sonnet**

Create tests for history system:

**`tests/unit/history/test_manager.py`:**
- Test history entry creation
- Test history persistence to disk
- Test history loading
- Test `--no-history` flag disables tracking
- Test temp file management
- Test history clearing

**Acceptance criteria:**
- History manager fully tested
- Global flag behavior tested
- File operations tested
- `uv run pytest` passes

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - No duplicate code introduced
   - Error handling is appropriate
   - Type hints are complete

2. **Integration Check:**
   - All new code integrates properly with existing code
   - Imports are correct
   - No circular dependencies

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Acceptance Criteria Validation:**
   - Verify each acceptance criterion is met
   - Test the feature manually if applicable

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Review and update `AGENTS.md` if project structure, testing guidelines, or commit conventions changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/history/__init__.py` | Create | Package init |
| `src/fabulae/history/models.py` | Create | History data models |
| `src/fabulae/history/manager.py` | Create | History manager |
| `src/fabulae/features/history/__init__.py` | Create | Feature package |
| `src/fabulae/features/history/cli.py` | Create | History command |
| `src/fabulae/main.py` | Modify | Add --no-history flag, wire history command |
| `src/fabulae/features/create/cli.py` | Modify | Integrate history tracking |
| `templates/*/.gitignore` | Create | Exclude .fabulae from git |
| `tests/unit/history/test_manager.py` | Create | History tests |

## Acceptance Criteria

- [ ] `.fabulae` folder created in projects
- [ ] History entries saved as JSON files
- [ ] `--no-history` global flag works
- [ ] `fabulae history` command shows project history
- [ ] Temp files stored in `.fabulae/temp`
- [ ] `.fabulae` excluded from git by default
- [ ] All tests pass
- [ ] `uv run ruff check`, `uv run mypy`, and `uv run pytest` pass

## Example History Output

```bash
$ fabulae history ./my-novel

Project History: ./my-novel
───────────────────────────────────────────────────────────────

✓ 2024-01-15 14:50 - build
    Duration: 45.2s
    Output: ./my-novel/output/2024-01-15_145012_seed42/

✓ 2024-01-15 14:45 - character_suggest
    Duration: 3.1s
    Added: dr-patil

✓ 2024-01-15 14:43 - character_add
    Duration: 0.1s
    Added: inspector-chen

✓ 2024-01-15 14:30 - create
    Duration: 28.7s
    Format: novel
    Model: ministral-3:3b

───────────────────────────────────────────────────────────────
Showing 4 of 4 entries
```

## Notes

- History is project-local, not global
- Large history can be pruned with `--clear` or manual deletion
- Consider adding `--since` date filter in future
- Could add `fabulae history replay <entry-id>` to re-run commands
