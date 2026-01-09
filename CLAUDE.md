# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build, Test, and Lint Commands

```bash
uv sync --locked --all-extras --dev   # Install dependencies
uv run fabulae --help                 # Run CLI from source
uv run pytest                         # Run all tests
uv run pytest -k test_name            # Run specific test by name
uv run pytest tests/unit/main_test.py # Run specific test file
uv run ruff check                     # Lint
uv run ruff check --fix               # Auto-fix lint issues
uv run mypy                           # Type check (strict mode)
```

## Before Completing Any Task

After every task, run all checks and fix any errors before handing off:

```bash
uv run ruff check --fix && uv run mypy && uv run pytest
```

If any check fails, fix the issues before considering the task complete.

## Architecture

Fabulae is a CLI toolkit for building narratives from YAML building blocks. The codebase has three main layers:

**CLI Layer** (`src/fabulae/main.py`): Typer-based commands - `version`, `validate`, `narrative-patterns`, `init`. Entry point defined in pyproject.toml as `fabulae = "fabulae.main:main"`.

**Data Models** (`src/fabulae/models.py`): Pydantic v2 models for all narrative entities with multi-layer validation:
- Core entities: `Character`, `WorldFact`, `Beat`, `Scene`, `Chapter`, `Plot`
- Pattern models: `PlotPattern`, `NarrativePattern`
- Config: `ProjectConfig`, `Project` (aggregate root)
- Custom `EntityId` type enforces lowercase-with-hyphens format via regex
- Cross-entity validation: unique IDs, valid references, scene ordering rules

**File I/O**: `load_project(path)` and `save_project(project, path)` handle all YAML serialization with validation.

**Template System**: `templates/basic/` contains the default project template, copied by `init` command.

## Key Validation Rules

- All entity IDs must be globally unique across the entire project
- IDs must be lowercase alphanumeric with hyphens (e.g., `scene-01`, `world-london`)
- Scene `location` must reference a WorldFact with `type="location"`
- Scene `characters` and `world_facts` must reference valid entities
- If chapters exist, scenes must reference them via `chapter.scene_ids`
- `plot_pattern_beat` requires `plot_pattern` to be set on the scene

## Coding Conventions

- Ruff formatting: 4-space indent, double quotes, 120-char line length
- Test files use `_test.py` suffix (e.g., `models_test.py`)
- Commit messages: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)
