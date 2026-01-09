# Fabulae

**A new way to tell stories: stories as a system.**

Fabulae is a CLI-first toolkit for building narratives from small, versionable building blocks – characters, beats,
microplots, and world facts – so you can iterate without losing consistency. Instead of starting from a blank page,
you assemble a structure (YAML) and let Fabulae render readable prose or scene drafts you can edit and own. It’s built
for exploration and repeatability: explore your story space by generating candidates, comparing variants, keeping what
resonates, and exporting to clean artifacts.

## Project layout (v0.1.0)

```text
fabulae.yml
plot.yml
characters.yml
world.yml
style.yml
plot_patterns.yml
```

Key rules:
- Global IDs are lowercase with hyphens and unique across the project.
- Chapters are optional; if present, scenes must reference a chapter.
- Scene locations must reference a `world.fact` with type `location`.
- Explicit scene order (via `chapter.scene_ids` or `plot.scene_ids`) overrides file order.

See `templates/basic` for a runnable example project.

## CLI

- `fabulae validate <dir>` validates a project directory.
- `fabulae version` prints the current version.

## Development

### Setup

```bash
git clone https://github.com/fmueller/fabulae.git
cd fabulae
uv sync --locked --all-extras --dev
```

### Running from source

```bash
uv run fabulae --help
```

### Testing

```bash
uv run ruff check   # Lint
uv run mypy         # Type check
uv run pytest       # Run tests
```

## License

This project is licensed under the Apache License 2.0. See [LICENSE](LICENSE) for details.
