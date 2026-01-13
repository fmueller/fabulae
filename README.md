[![Build](https://github.com/fmueller/fabulae/actions/workflows/build.yml/badge.svg)](https://github.com/fmueller/fabulae/actions/workflows/build.yml)

# Fabulae

**A new way to tell stories: stories as a system.**

Fabulae is a CLI-first toolkit for building narratives from small, versionable building blocks – characters, beats,
and world facts – so you can iterate without losing consistency. Instead of starting from a blank page,
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

## Story Shapes

Story shapes are pre-defined narrative templates that provide structural scaffolding for your stories. Each shape defines character slots, setting slots, required beats, variation points, themes, and motifs.

**Built-in shapes:**
- `heros-journey` - Classic monomyth structure
- `betrayal-arc` - Trust broken, consequences explored
- `coming-of-age` - Growth and self-discovery
- `mystery-reveal` - Puzzle-solving narrative
- `romance-arc` - Relationship development
- `revenge-quest` - Vengeance-driven plot
- `forbidden-knowledge` - Dangerous discovery
- `fish-out-of-water` - Displacement and adaptation
- `transformation` - Fundamental change
- `fall-redemption` - Downfall and recovery

Use `fabulae shapes` to list all available shapes and `fabulae shape <id>` to see details.

## Project Layout (v0.1.0)

```text
fabulae.yml
plot.yml
characters.yml
world.yml
style.yml
```

Key rules:
- Global IDs are lowercase with hyphens and unique across the project.
- Chapters are optional; if present, each chapter lists its scenes via `scene_ids`.
- Scene locations are optional; if set, must reference a `world.fact` with type `location`.
- Scenes can have a `time` field for temporal context (e.g., "dawn", "three years later").
- Explicit scene order (via `chapter.scene_ids` or `plot.scene_ids`) overrides file order.

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
- `fabulae create [OPTIONS] <dir>` generates a complete project from an idea using LLM.
- `fabulae shapes` lists all available story shapes.
- `fabulae shape <id>` shows details of a specific story shape.

### Initializing a Project

```bash
# Create a novel project (default)
fabulae init my-novel

# Create a poem project
fabulae init --format poem my-poem

# Create a micro-prose project
fabulae init -f micro-prose my-flash-fiction
```

Available formats: `novel`, `novella`, `short-story`, `micro-prose`, `poem`

### Creating a Project from an Idea

```bash
# Generate a project with default settings
fabulae create --idea "A detective story in a cyberpunk city" my-story

# Use a story shape for structural guidance
fabulae create --idea "A hero's journey in space" --shape heros-journey my-space-opera

# Use a custom story shape file
fabulae create --idea "A unique tale" --shape-file my-shape.yml my-project

# Control variation level (0.0 = minimal, 1.0 = maximum)
fabulae create --idea "A mystery" --variation 0.8 my-mystery

# Disable enrichment pass (skips adding extra characters, subplots, foreshadowing)
fabulae create --idea "A simple story" --no-enrich my-simple-story

# Enforce a specific language
fabulae create --idea "Une histoire d'amour" --language fr my-french-story

# Use a specific random seed for reproducible results
fabulae create --idea "A fantasy epic" --seed 42 my-fantasy
```

**Create command options:**
- `--idea, -i` – Idea text or path to file containing the idea
- `--format, -f` – Literature format (default: novel)
- `--shape` – Built-in story shape ID (use `fabulae shapes` to list)
- `--shape-file` – Path to custom story shape YAML file
- `--variation` – Variation level 0.0-1.0 (default: 0.5)
- `--enrich/--no-enrich` – Enable/disable enrichment pass (default: auto - enabled for large models, disabled for small models <13B)
- `--language, -l` – ISO 639-1 language code to enforce
- `--seed` – Random seed for reproducible generation
- `--pipeline, -p` – Generation pipeline: 'batch' or 'sequential' (default: 'sequential' for small models <13B, 'batch' otherwise)
- `--model` – LLM model to use
- `--temperature` – LLM temperature setting

### Browsing Story Shapes

```bash
# List all available story shapes
fabulae shapes

# Show details of a specific shape
fabulae shape heros-journey
fabulae shape betrayal-arc
```

## Development

### Setup

```bash
git clone https://github.com/fmueller/fabulae.git
cd fabulae
uv sync --locked --all-extras --dev
uv run pre-commit install
```

### Running from Source

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
