# Repository Guidelines

## Project Structure & Module Organization

- `src/fabulae/main.py` is the CLI wiring only; keep business logic in feature slices.
- `src/fabulae/models.py` remains the core domain models and validation.
- `src/fabulae/features/` holds vertical slices (create, build, check, doctor, entities, tui, history).
- `src/fabulae/data/` contains static data assets like story shapes used by the create feature.
- `src/fabulae/history/` contains the history manager, models, and state for `.fabulae/` folder operations.
- `src/fabulae/llm/` contains shared LLM config, agent factory, and connectivity helpers.
- `src/fabulae/prompts/` contains shared prompt helpers; each feature slice owns its own `prompts.py`.
- `tests/` holds pytest suites; unit tests live under `tests/unit/` and should mirror the feature slices under `tests/unit/features/`.
- `templates/` provides runnable YAML project templates (plot, characters, world, style).
- `README.md` documents CLI usage and project concepts; `pyproject.toml` defines tooling and dependencies.

## Build, Test, and Development Commands

- `uv sync --locked --all-extras --dev` installs dependencies with the locked versions.
- `uv run fabulae --help` runs the CLI from source for local development.
- `uv run ruff check` lints the codebase.
- `uv run mypy` runs strict type checks.
- `uv run pytest` executes the test suite.

## Coding Style & Naming Conventions

- Python code follows Ruff formatting: 4-space indentation, double quotes, and a 120-character line length.
- Keep modules under `src/fabulae/`; register new CLI commands in `main.py`, with command functions implemented in `src/fabulae/features/<slice>/cli.py` and delegating to feature services.
- Story template IDs must be lowercase with hyphens (e.g., `scene-01`, `world-london`), and IDs are globally unique.

## Testing Guidelines

- Tests use `pytest` and are located under `tests/`.
- Prefer naming test files with the `_test.py` suffix (e.g., `tests/unit/models_test.py`).
- Run `uv run pytest` before submitting changes, and add tests for validation or parsing logic.
- Tests must not call live LLMs; use the fake LLM hook (`FABULAE_FAKE_LLM=1`) or stub `create_agent`.
- CLI tests using `CliRunner` that check for specific text in output should strip ANSI escape codes before matching. Use `re.compile(r"\x1b\[[0-9;]*m").sub("", result.output)` to clean the output. This prevents string matching failures in CI where ANSI codes can split text.

## Commit & Pull Request Guidelines

- Commit messages follow Conventional Commits seen in history: `feat: ...`, `docs: ...`, `fix: ...`.
- PRs should describe the change, link relevant issues, and include test commands run.
- For template or CLI changes, add before/after examples (e.g., updated YAML snippets or CLI output).

## Agent-Specific Instructions

- After every task, run `uv run ruff check --fix`, `uv run mypy`, and `uv run pytest`, then fix any errors before handing off.

## Task Execution Guidelines

### Breaking Down Tasks

When implementing a task from `tasks/`:
1. Read the full task description to understand scope
2. Identify discrete implementation steps
3. Evaluate complexity per step (Low/Medium/High)
4. Select appropriate model per step (see Model Selection below)
5. Execute steps sequentially, verifying each before proceeding

### Model Selection per Step

| Step Type | Complexity | Recommended Model |
|-----------|------------|-------------------|
| Boilerplate, simple edits, CLI flags, file moves | Low | Haiku |
| Business logic, validation, service layer, tests | Medium | Sonnet |
| Prompt engineering, architecture, complex refactors | High | Opus |
| Final verification, code review, integration checks | High | Opus |

### Post-Implementation Documentation Review

After completing any implementation task, check if documentation updates are needed:

1. **README.md** - Update if:
   - New CLI commands or flags added
   - User-facing behavior changed
   - New features documented

2. **CLAUDE.md** - Update if:
   - Architectural patterns changed
   - New conventions established
   - Key implementation details added

3. **AGENTS.md** - Update if:
   - Project structure changed
   - Testing guidelines updated
   - Commit conventions modified

## Configuration & Templates

- YAML project files live at the project root when used by the CLI (see `templates/`).
- Templates exist for each format: `novel/`, `novella/`, `short-story/`, `micro-prose/`, `poem/`.
- Scene ordering rules: explicit `chapter.scene_ids` or `plot.scene_ids` override file order.
