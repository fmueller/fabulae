[![Build](https://github.com/fmueller/fabulae/actions/workflows/build.yml/badge.svg)](https://github.com/fmueller/fabulae/actions/workflows/build.yml)

# Fabulae

**A new way to tell stories: stories as a system.**

Fabulae is a CLI-first toolkit for building narratives from small, versionable building blocks – characters, beats,
plot patterns, and world facts – so you can iterate without losing consistency. Instead of starting from a blank page,
you assemble a structure (YAML) and let Fabulae render readable prose or scene drafts you can edit and own. It's built
for exploration and repeatability: explore your story space by generating candidates, comparing variants, keeping what
resonates, and exporting to clean artifacts.

## Supported Formats

Fabulae supports multiple narrative formats via the `format` field in `plot.yml`:

| Format | Structure | Use Case |
|--------|-----------|----------|
| `novel` | Chapters, scenes, beats | Long-form fiction |
| `novella` | Chapters, scenes, beats | Medium-length fiction |
| `short-story` | Scenes, beats (chapters optional) | Single-sitting narratives |
| `micro-prose` | Fragments | Flash fiction, vignettes |
| `poem` | Stanzas or lines | Poetry, lyrics, verse |

See `templates/` for examples of each format.

## Project layout (v0.1.0)

```text
fabulae.yml
plot.yml
characters.yml
world.yml
style.yml
plot_patterns.yml
narrative_patterns.yml
```

Key rules:
- Global IDs are lowercase with hyphens and unique across the project.
- Chapters are optional; if present, scenes must reference a chapter.
- Scene locations are optional; if set, must reference a `world.fact` with type `location`.
- Scenes can have a `time` field for temporal context (e.g., "dawn", "three years later").
- Explicit scene order (via `chapter.scene_ids` or `plot.scene_ids`) overrides file order.
- Plot patterns describe plot structure; narrative patterns bundle plot patterns with theme/world cues.
- `plot_patterns.yml` and `narrative_patterns.yml` are optional; omit them if you do not use patterns.

Templates:
- `templates/novel` – Novel with chapters, scenes, and beats
- `templates/novella` – Novella with scenes and a smaller starter scope
- `templates/short-story` – Short story with a tight scene-based outline
- `templates/poem` – Poetry with stanzas
- `templates/micro-prose` – Flash fiction with fragments

## CLI

- `fabulae validate <dir>` validates a project directory.
- `fabulae version` prints the current version.
- `fabulae init [--format FORMAT] <dir>` scaffolds a new project from a template.

### Initializing a project

```bash
# Create a novel project (default)
fabulae init my-novel

# Create a poem project
fabulae init --format poem my-poem

# Create a micro-prose project
fabulae init -f micro-prose my-flash-fiction
```

Available formats: `novel`, `novella`, `short-story`, `micro-prose`, `poem`

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
