# Repository Guidelines

## Project Structure & Module Organization

- `src/fabulae/main.py` is the CLI wiring only; keep business logic in feature slices.
- `src/fabulae/models.py` remains the core domain models and validation.
- `src/fabulae/features/` holds vertical slices (create, build, check, doctor, entities, tui).
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

## Commit & Pull Request Guidelines

- Commit messages follow Conventional Commits seen in history: `feat: ...`, `docs: ...`, `fix: ...`.
- PRs should describe the change, link relevant issues, and include test commands run.
- For template or CLI changes, add before/after examples (e.g., updated YAML snippets or CLI output).

## Agent-Specific Instructions

- After every task, run `uv run ruff check --fix`, `uv run mypy`, and `uv run pytest`, then fix any errors before handing off.

## Configuration & Templates

- YAML project files live at the project root when used by the CLI (see `templates/basic/`).
- Scene ordering rules: explicit `chapter.scene_ids` or `plot.scene_ids` override file order.
