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
.fabulae/           # Auto-generated, gitignored
├── history/        # Command history entries
├── create/         # Generation artifacts and partial results
├── cache/          # Temporary cache files
└── temp/           # Temporary working files
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
- `fabulae history [OPTIONS] <dir>` views or manages project history.
- `fabulae build [OPTIONS] <dir>` generates complete narrative output from a project.

**Global options:**
- `--no-history` disables project history tracking for the command.

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
fabulae create --idea "A unique tale" --shape my-shape.yml my-project

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
- `--shape, -s` – Story shape: built-in shape ID (use `fabulae shapes` to list) or path to custom YAML file
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

### Managing Project Entities

Fabulae provides CRUD commands for managing all project entities. Each entity type has `add`, `list`, `edit`, `remove`, and `suggest` subcommands.

**Characters** (all formats):
```bash
fabulae character add ./my-project --id hero-jane --name "Jane Doe" --role protagonist
fabulae character list ./my-project
fabulae character edit ./my-project hero-jane --add-trait "brave"
fabulae character remove ./my-project hero-jane --force
fabulae character suggest ./my-project --idea "a mysterious stranger"
```

**World Facts** (all formats):
```bash
fabulae world add ./my-project --id location-tavern --type location --name "The Golden Tankard"
fabulae world list ./my-project --type location
fabulae world suggest ./my-project --type culture --idea "ancient traditions"
```

**Scenes, Beats, Chapters** (prose formats: novel, novella, short-story):
```bash
# Scenes
fabulae scene add ./my-project --id scene-chase --summary "A thrilling chase"
fabulae scene edit ./my-project scene-chase --add-character hero-jane --location location-tavern
fabulae scene suggest ./my-project --chapter chapter-01

# Beats (within scenes)
fabulae beat add ./my-project --scene scene-chase --id beat-escape --kind action --summary "Jane escapes"
fabulae beat suggest ./my-project --scene scene-chase

# Chapters
fabulae chapter add ./my-project --id chapter-01 --title "The Beginning"
fabulae chapter edit ./my-project chapter-01 --add-scene scene-chase
```

**Fragments** (micro-prose format only):
```bash
fabulae fragment add ./my-project --id fragment-03 --content "The rain fell softly..."
fabulae fragment list ./my-project
fabulae fragment suggest ./my-project --idea "a moment of realization"
```

**Stanzas** (poem format only):
```bash
fabulae stanza add ./my-project --id stanza-03 --line "The wind blows cold" --line "Through ancient pines"
fabulae stanza edit ./my-project stanza-03 --meter "iambic pentameter" --rhyme-scheme "ABAB"
fabulae stanza suggest ./my-project --idea "nature imagery"
```

**Common options for suggest commands:**
- `--idea, -i` – Guidance text or path to file
- `--model` – LLM model to use
- `--temperature` – LLM temperature
- `--yes, -y` – Add without confirmation

### Managing Project History

Fabulae tracks command history in the `.fabulae/history/` folder. Use the `history` command to view or manage it.

```bash
# View recent history (default: last 10 entries)
fabulae history my-project

# View more entries
fabulae history -n 20 my-project

# Output as JSON
fabulae history --json my-project

# Clear all history
fabulae history --clear my-project

# Disable history for a command
fabulae --no-history create --idea "A story" my-project
```

### Building Narrative Output

The `build` command generates complete narrative prose from your project's structural elements using an LLM.

```bash
# Basic build
fabulae build ./my-novel

# Build with seed for reproducibility (same seed = same output)
fabulae build ./my-novel --seed 42

# Specify output directory
fabulae build ./my-novel --output ./drafts

# Output as HTML or plain text
fabulae build ./my-novel --format html
fabulae build ./my-novel --format txt

# Use specific model settings
fabulae build ./my-novel --model llama3:8b --temperature 0.8
```

**Build command options:**
- `--output, -o` – Output directory (default: `<project>/output/`)
- `--seed` – Seed for reproducible builds
- `--format, -f` – Output format: `md` (default), `txt`, or `html`
- `--model` – LLM model to use
- `--temperature` – LLM temperature setting

**Output structure:**
```text
output/
└── 2024-01-15_143052_seed42/
    ├── build.json          # Build metadata (model, seed, timestamp)
    ├── story.md            # Complete narrative
    ├── chapters/           # Individual chapter files (if chaptered)
    │   ├── 01-chapter-one.md
    │   └── ...
    └── fragments/          # Individual fragments (for micro-prose)
```

## How We Work

- **Start here**: Read [CURRENT.md](CURRENT.md) for what's happening now
- **Task board**: Tasks live in `backlog/` — run `backlog board` to view
- **Specs**: Non-trivial changes get an [OpenSpec](openspec/) change folder
- **ADRs & Learnings**: Architecture decisions in `docs/decisions/`, patterns and gotchas in `docs/learnings/`
- **Changelog**: [CHANGELOG.md](CHANGELOG.md) follows [Keep a Changelog](https://keepachangelog.com/)
- **Roadmap**: [ROADMAP.md](ROADMAP.md) shows Now / Next / Later milestones
- **Commits**: [Conventional Commits](https://www.conventionalcommits.org/) enforced via pre-commit hook
- **Full agent instructions**: See [AGENTS.md](AGENTS.md)

## Development

### Setup

```bash
git clone https://github.com/fmueller/fabulae.git
cd fabulae
uv sync --locked --all-extras --dev
uv run pre-commit install
uv run pre-commit install --hook-type commit-msg
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
For third-party dependency licensing details and release-compliance notes, see
[docs/THIRD_PARTY_LICENSE_AUDIT.md](docs/THIRD_PARTY_LICENSE_AUDIT.md).
