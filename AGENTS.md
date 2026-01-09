# Repository Guidelines

## Project Structure & Module Organization

- `src/fabulae/` contains the CLI entrypoint (`main.py`), models (`models.py`), and version utilities.
- `tests/` holds pytest suites; unit tests live under `tests/unit/`.
- `templates/basic/` provides a runnable YAML project template (plot, characters, world, style).
- `README.md` documents CLI usage and project concepts; `pyproject.toml` defines tooling and dependencies.

## Build, Test, and Development Commands

- `uv sync --locked --all-extras --dev` installs dependencies with the locked versions.
- `uv run fabulae --help` runs the CLI from source for local development.
- `uv run ruff check` lints the codebase.
- `uv run mypy` runs strict type checks.
- `uv run pytest` executes the test suite.

## Coding Style & Naming Conventions

- Python code follows Ruff formatting: 4-space indentation, double quotes, and a 120-character line length.
- Keep modules under `src/fabulae/` and add new CLI commands in `main.py` or a dedicated module.
- Story template IDs must be lowercase with hyphens (e.g., `scene-01`, `world-london`), and IDs are globally unique.

## Testing Guidelines

- Tests use `pytest` and are located under `tests/`.
- Prefer naming test files with the `_test.py` suffix (e.g., `tests/unit/models_test.py`).
- Run `uv run pytest` before submitting changes, and add tests for validation or parsing logic.

## Commit & Pull Request Guidelines

- Commit messages follow Conventional Commits seen in history: `feat: ...`, `docs: ...`, `fix: ...`.
- PRs should describe the change, link relevant issues, and include test commands run.
- For template or CLI changes, add before/after examples (e.g., updated YAML snippets or CLI output).

## Agent-Specific Instructions

- After every task, run `uv run ruff check --fix`, `uv run mypy`, and `uv run pytest`, then fix any errors before handing off.

## Configuration & Templates

- YAML project files live at the project root when used by the CLI (see `templates/basic/`).
- Scene ordering rules: explicit `chapter.scene_ids` or `plot.scene_ids` override file order.
