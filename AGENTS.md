# Agent Instructions

## Quick Start

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

**Before completing any task**, run all checks and fix any errors:

```bash
uv run ruff check --fix && uv run mypy && uv run pytest
```

If any check fails, fix the issues before considering the task complete.

## Workflow: Read Order

1. **CURRENT.md** — what just happened and what's next
2. **`backlog board`** — full task board (priorities, statuses, dependencies)
3. **OpenSpec / docs** — specs and context for the task at hand
4. **Implement** — write code, tests, docs
5. **Update CURRENT.md** — move completed items to "Last", update "Next"

## Task Types & When to Use OpenSpec

- **Trivial fix** (typo, one-liner, config change) → backlog task only
- **Non-trivial behavior change** (new feature, architectural change, prompt rewrite) → backlog task + OpenSpec change

The full workflow is documented in [openspec/WORKFLOW.md](openspec/WORKFLOW.md). Key points:

1. Create a change directory: `mkdir -p openspec/changes/<name>/specs`
2. Create artifacts in order: proposal → specs → design → tasks
3. Implement tasks, checking them off in `tasks.md`
4. Sync delta specs to main specs, then archive

### Backlog is the Source of Truth

The backlog (`backlog/` directory) tracks ALL work. When OpenSpec creates a `tasks.md`, **each task must also exist in the backlog**:

1. Run `backlog task create` for each task in `tasks.md`
2. Include `--ref openspec/changes/<name>/tasks.md` to link back
3. Add a label matching the change name (e.g., `--label add-auth`)
4. The backlog task is the source of truth for status; the OpenSpec checkbox is kept in sync

This ensures `backlog board` always shows the full picture, even for spec-driven work.

## Linking Rules

- Every backlog task should link to relevant openspec/docs when applicable
- CURRENT.md links to the top tasks and any active changes
- Use `--ref` when creating backlog tasks to link specs or docs

## Definition of Done

Before considering a task complete:

- [ ] `uv run ruff check --fix && uv run mypy && uv run pytest` passes
- [ ] `CURRENT.md` updated ("Last"/"Next" reflect the latest state)
- [ ] Backlog task status updated
- [ ] `CHANGELOG.md` updated for user-facing changes
- [ ] Commit message follows Conventional Commits

## Commits

Conventional Commits format, enforced via pre-commit hook.

**Allowed types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `ci`, `style`, `perf`, `build`, `revert`

**Format:** `<type>(<optional scope>): <description>`

Examples:
- `feat(build): add word count targets to scene prompts`
- `fix: prevent retry callback from firing on exhausted final attempt`
- `docs(agents): rewrite AGENTS.md with unified workflow`

After the hook is installed (`pre-commit install --hook-type commit-msg`), bad commit messages will be rejected.

## When to Write ADRs / Learnings

**ADR triggers** — write to `docs/decisions/` when choosing between durable alternatives:
- Architecture patterns (e.g., batch vs. sequential pipeline)
- Storage formats (YAML vs. JSON vs. TOML)
- API design (CLI flags, command structure)
- Dependency choices (which library, which LLM provider)

**Learning triggers** — write to `docs/learnings/` when you encounter:
- Surprises that cost time (`gotchas/`)
- Patterns that worked well across multiple tasks (`patterns/`)
- Step-by-step procedures for recurring operations (`runbooks/`)
- Agent failure modes and workarounds (`gotchas/`)

## Changelog & Roadmap Rules

- **CHANGELOG.md**: [Keep a Changelog](https://keepachangelog.com/) format. `[Unreleased]` section at top. Categories: Added, Changed, Fixed, Removed. Update when merging to main.
- **ROADMAP.md**: Now / Next / Later sections. Describes direction and goals, not individual tasks — link to backlog task ranges instead of listing line-by-line. Update when milestones shift.

## Test Isolation

- Tests must never call live LLMs. Use the fake LLM hook (`FABULAE_FAKE_LLM=1`) or stub `create_agent` in tests.
- CLI tests using `CliRunner` that check for specific text in output should strip ANSI escape codes before matching. Use `re.compile(r"\x1b\[[0-9;]*m").sub("", result.output)` to clean the output. This prevents string matching failures in CI where ANSI codes can split text (e.g., `--no-history` becomes `-`, `-no`, `-history`).

## Architecture

Fabulae is a CLI toolkit for building narratives from YAML building blocks, following a vertical-slice architecture.

- **CLI Layer** (`src/fabulae/main.py`) — Typer-based command wiring; feature commands in `features/<slice>/cli.py`
- **Feature Slices** (`src/fabulae/features/`) — each owns prompts, schemas, service logic (create, build, entities, history, etc.)
- **Shared LLM** (`src/fabulae/llm/`) — config, agent factory, connectivity tests
- **Data Models** (`src/fabulae/models.py`) — Pydantic v2 entities with cross-entity validation
- **Templates** (`templates/`) — project scaffolds per format (novel, poem, micro-prose, etc.)

For detailed feature architectures (Create pipelines, Build pipeline, Entity CRUD, History system, validation rules): see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Coding Conventions

- Ruff formatting: 4-space indent, double quotes, 120-char line length
- Test files use `_test.py` suffix (e.g., `models_test.py`)
- Prefer placing feature tests under `tests/unit/features/` to mirror `src/fabulae/features/`
- Commit messages: Conventional Commits (see [Commits](#commits) section)

## Complexity-Based Model Selection

When implementing tasks, evaluate each step's complexity and select the appropriate model:

| Step Type | Complexity | Recommended Model |
|-----------|------------|-------------------|
| Boilerplate, simple edits, CLI flags, file moves | Low | Haiku |
| Business logic, validation, service layer, tests | Medium | Sonnet |
| Prompt engineering, architecture, complex refactors | High | Opus |
| Final verification, code review, integration checks | High | Opus |

## Documentation Maintenance

After implementing changes, review and update these files as needed:

- **README.md** — user-facing changes (CLI commands, features)
- **AGENTS.md** — architectural/convention changes
- **docs/ARCHITECTURE.md** — structural/architectural changes
- **CURRENT.md** — move completed items to "Last", update "Next"
- **CHANGELOG.md** — add entries under `[Unreleased]`
- **ROADMAP.md** — update if milestones shift

## Project Structure

```
src/fabulae/           # Main package
├── main.py            # CLI wiring (Typer)
├── models.py          # Core domain models (Pydantic v2)
├── llm/               # Shared LLM config, agent factory
├── prompts/           # Shared prompt helpers
├── history/           # History manager, models, state
├── data/              # Static data (story shapes)
└── features/          # Vertical slices
    ├── create/        # Project generation from ideas
    ├── build/         # Narrative prose generation
    ├── check/         # Semantic quality checks (planned)
    ├── doctor/        # Environment diagnostics (planned)
    ├── entities/      # Entity CRUD commands
    ├── tui/           # Terminal UI (planned)
    └── history/       # History CLI commands
templates/             # Project templates (novel, poem, etc.)
tests/                 # Pytest suites
├── unit/              # Unit tests mirroring src/ structure
backlog/               # Task management (source of truth for all tasks)
openspec/              # Spec-driven development (see openspec/WORKFLOW.md)
docs/
├── decisions/         # Architecture Decision Records
└── learnings/         # Patterns, runbooks, gotchas
```
