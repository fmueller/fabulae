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

## Test Isolation

- Tests must never call live LLMs. Use the fake LLM hook (`FABULAE_FAKE_LLM=1`) or stub `create_agent` in tests.
- CLI tests using `CliRunner` that check for specific text in output should strip ANSI escape codes before matching. Use `re.compile(r"\x1b\[[0-9;]*m").sub("", result.output)` to clean the output. This prevents string matching failures in CI where ANSI codes can split text (e.g., `--no-history` becomes `-`, `-no`, `-history`).

## Architecture

Fabulae is a CLI toolkit for building narratives from YAML building blocks. The codebase follows a lightweight vertical-slice architecture:

**CLI Layer** (`src/fabulae/main.py`): Typer-based command wiring only. Command functions live in `src/fabulae/features/<slice>/cli.py` and should call feature services while avoiding embedded business logic. Entry point is `fabulae = "fabulae.main:main"`.

**Feature Slices** (`src/fabulae/features/`): Each feature owns its prompts, schemas, and service logic (e.g., `create/`, `build/`, `check/`, `doctor/`, `entities/`, `tui/`, `history/`). The CLI and TUI should call into these services to share behavior. The TUI lives under `src/fabulae/features/tui/` and is implemented with Textual (screens, widgets, and modals).

**Shared LLM + Prompts**:
- `src/fabulae/llm/` for `LLMConfig`, agent factory, config resolution, and connectivity tests.
- `src/fabulae/prompts/` for shared prompt helpers; feature-specific prompts live in each slice.

**Data Models** (`src/fabulae/models.py`): Pydantic v2 models for all narrative entities with multi-layer validation:
- Core entities: `Character`, `WorldFact`, `Beat`, `Scene`, `Chapter`, `Plot`
- Story shapes: `StoryShape`, `CharacterSlot`, `SettingSlot`, `RequiredBeat`, `VariationPoint`
- Config: `ProjectConfig`, `Project` (aggregate root)
- Custom `EntityId` type enforces lowercase-with-hyphens format via regex
- Cross-entity validation: unique IDs, valid references, scene ordering rules

**File I/O**: `load_project(path)` and `save_project(project, path)` handle all YAML serialization with validation.

**Template System**: `templates/` contains project templates for different formats:
- `novel/` - Full novel template with characters, world, style
- `novella/` - Condensed prose template
- `short-story/` - Minimal prose template
- `micro-prose/` - Flash fiction with fragments
- `poem/` - Poetry with stanzas

The `init --format <format>` command copies the appropriate template.

### Create Feature Architecture

The `create` feature generates narrative projects from ideas using a multi-stage pipeline:

**Story Shapes** (`src/fabulae/data/story_shapes/`): Pre-defined narrative templates that provide structural scaffolding:
- Each shape defines: character slots, setting slots, required beats, variation points, themes, motifs
- Built-in shapes: `heros-journey`, `betrayal-arc`, `coming-of-age`, `mystery-reveal`, `romance-arc`, etc.
- Select via `--shape <id>` for built-in shapes or `--shape <path>` for custom shape files
- CLI: `fabulae shapes` (list all) and `fabulae shape <id>` (show details)
- Loader: `src/fabulae/features/create/shapes/loader.py` and `selector.py`

**Format-Specific Pipelines** (`src/fabulae/features/create/pipelines/`): Each format has its own generation pipeline:
- `prose.py` - Novel, novella, short-story (scenes, chapters, beats) - batch generation
- `sequential.py` - Per-unit generation pipeline for prose formats (one LLM call per scene/character)
- `micro_prose.py` - Flash fiction (fragments instead of scenes) - batch generation
- `micro_prose_sequential.py` - Per-unit fragment generation with sliding window context
- `poem.py` - Poetry (stanzas, lines) - batch generation
- `poem_sequential.py` - Per-unit stanza generation with sliding window context
- `plot_first.py` - Alternative approach: generate plot structure before scenes
- Main service (`service.py`) dispatches to the appropriate pipeline based on format and `--pipeline` flag

**Sequential Pipeline Architecture**:
- `--pipeline sequential` enables per-unit generation with minimal context per LLM call
- Works for all formats: prose, micro-prose, and poem
- Pre-computes complete structure using RNG (`graph.py`, `structure.py`) before any LLM calls
- Graph types: `PlotGraph` (prose), `MicroProseGraph` (fragments), `PoemGraph` (stanzas)
- Generates one unit at a time with sliding window context
- Uses minimal context builders (`context.py`) to include only relevant entities per prompt
- Focused prompts (`prompts_v2.py`) for each unit type reduce LLM divergence and errors
- Deterministic structure with seed: same seed = same structure skeleton

**ID Generation** (`src/fabulae/features/create/ids.py`): IDs are pre-allocated before LLM generation:
- Sequential format: `{type}-{nn}` (e.g., `scene-01`, `character-03`, `location-04`)
- IDs provided to LLM in prompts, validated unchanged in responses
- Reference validation is strict; no silent filtering of invalid references
- Ensures all entity references are valid before project creation

**Variation System** (`src/fabulae/features/create/variation.py`): Controls narrative randomness and diversity:
- `--variation <float>` CLI flag (0.0-1.0, default 0.5) sets variation level
- Affects: complication beats, character moments, subplot seeds, filler beat selection
- `VariationConfig`: configurable probabilities for each element type
- `ProjectVariation`: pre-computes all variation decisions before generation
- Deterministic RNG via optional `--seed` for reproducible results

**Enrichment Pass** (`src/fabulae/features/create/enrichment.py`): Adds depth without changing structure:
- `--enrich/--no-enrich` CLI flag (default: auto - enabled for large models, disabled for small models <13B)
- Adds: new characters, locations, subplots, foreshadowing, thematic depth
- Runs after initial generation to enhance existing scenes
- Merges new entities while maintaining ID uniqueness and reference integrity

**Small Model Optimizations** (`src/fabulae/features/create/cli.py`): Auto-detected for models <13B parameters:
- Auto-detection via model name patterns (e.g., `:3b`, `:1.7b`, `mini`, `tiny`)
- Sequential pipeline auto-selected (better for limited context, override with `--pipeline batch`)
- Enrichment auto-disabled to reduce context pressure
- Sliding window for context (last 5 units instead of all prior units) - applies to all formats:
  - Prose: last 5 scenes
  - Micro-prose: last 5 fragments
  - Poem: last 5 stanzas
- Warning displayed at startup about potential JSON output issues

### History Feature Architecture

The history system tracks all commands executed on a project in the `.fabulae/` folder:

**Folder Structure** (`.fabulae/`):
- `history/` - YAML files storing command history entries
- `create/` - Generation artifacts (style, premise, structure) and partial results on interruption
- `cache/` - Temporary cache files
- `temp/` - Temporary working files

**Core Components** (`src/fabulae/history/`):
- `manager.py` - `HistoryManager` class handles all `.fabulae/` folder operations
- `models.py` - `HistoryEntry` Pydantic model for history records
- `state.py` - Global state for history manager access across the application

**CLI Integration**:
- Global `--no-history` flag disables tracking for any command
- `fabulae history` command views/manages history (`src/fabulae/features/history/cli.py`)
- History entries include: timestamp, command, arguments, duration, success status

### Entity CRUD Feature Architecture

The `entities` feature (`src/fabulae/features/entities/`) provides CLI commands for managing all project entities:

**Entity Modules**: Each entity type has its own module with a Typer app:
- `character.py` - Character CRUD (all formats)
- `world.py` - WorldFact CRUD (all formats)
- `scene.py` - Scene CRUD (prose formats only)
- `beat.py` - Beat CRUD (prose formats only)
- `chapter.py` - Chapter CRUD (prose formats only)
- `fragment.py` - Fragment CRUD (micro-prose format only)
- `stanza.py` - Stanza CRUD (poem format only)

**Shared Components**:
- `utils.py` - Shared helpers: ID validation, format checking (`require_prose_format`, `require_micro_prose_format`, `require_poem_format`), entity ID collection, reference formatting

**Generation Module** (`src/fabulae/features/entities/generation/`): Unified entity generation layer for LLM-based suggestions, serving as single source of truth for both CRUD commands and create pipeline:
- `prompts.py` - Shared prompt builders for all entity types with StyleOutput support, BeatSlotInfo for beat slots, and position context
- `schemas.py` - Pydantic models for LLM output validation (e.g., `CharacterOutput`, `SceneOutput`, `ChapterOutput`); create/schemas.py re-exports these for backward compatibility
- `title_structure.py` - Title diversity utilities (`TitleRequirement`, `get_title_requirement`) for varied chapter titles with structure rotation
- Entity modules (`character.py`, `world_fact.py`, `scene.py`, `beat.py`, `chapter.py`, `fragment.py`, `stanza.py`) - Unified `suggest_*` functions with both sync and async variants:
  - CRUD mode: Pass `project` parameter, extracts context from project
  - Create mode: Pass individual parameters (`style`, `beat_slots`, `chapter_index`, etc.) for pipeline integration

**Format Validation**: Commands enforce format compatibility at two levels:
1. CLI layer: `require_*_format()` helpers provide helpful error messages suggesting correct commands
2. `save_project()`: Safety net validation prevents saving format-incompatible entities

**Command Pattern**: Each entity module follows the same pattern:
- `add` - Create new entity with CLI options for all model fields
- `list` - Display entities in table/JSON/YAML format
- `edit` - Modify existing entity (supports `--add-*`/`--remove-*` for list fields)
- `remove` - Delete entity with optional `--force` flag
- `suggest` - LLM-generated entity suggestion with `--idea` guidance

### Build Feature Architecture

The `build` feature (`src/fabulae/features/build/`) generates complete narrative prose from project structures:

**Core Components**:
- `schemas.py` - Pydantic models for build output: `BuildMetadata`, `SceneOutput`, `ChapterOutput`, `FragmentOutput`, `StanzaOutput`, `BuildOutput`
- `prompts.py` - Prompt builders for scene, fragment, stanza, and poem generation
- `scene_builder.py` - LLM-based generation for individual scenes, fragments, and stanzas
- `service.py` - Build orchestrator dispatching to format-specific builders
- `writer.py` - Output file writing in md, txt, or html formats
- `cli.py` - CLI command registration

**Build Pipeline**:
1. Load and validate project
2. Dispatch to format-specific builder based on `plot.format`:
   - `novel`/`novella`: Chaptered build with scene-by-scene generation
   - `short-story`: Scene-by-scene without chapters
   - `micro-prose`: Fragment-by-fragment generation
   - `poem`: Stanza-by-stanza or complete poem generation
3. Generate continuity summaries for context threading (prose formats)
4. Write output files to timestamped directory

**Key Features**:
- **Seed-based reproducibility**: Same seed + same project = consistent output
- **Sliding window context**: Last 5 scenes/fragments/stanzas for continuity
- **Language enforcement**: Uses shared language guard from prompts module
- **Multiple output formats**: Markdown (default), plain text, or HTML

**Output Structure**:
```
output/2024-01-15_143052_seed42/
├── build.json          # Metadata (model, seed, timestamp, word count)
├── story.md            # Complete narrative
├── chapters/           # Per-chapter files (chaptered formats)
└── fragments/          # Per-fragment files (micro-prose)
```

## Key Validation Rules

- All entity IDs must be globally unique across the entire project
- IDs must be lowercase alphanumeric with hyphens (e.g., `scene-01`, `world-london`)
- Scene `location` is optional; if set, must reference a WorldFact with `type="location"`
- Scene `characters` and `world_fact_ids` must reference valid entities
- If chapters exist, each chapter lists its scenes via `scene_ids`; all scenes must be assigned to exactly one chapter
- Beat references must point to valid beats in the scene's `beats` list
- Format validation: prose formats require scenes, micro-prose requires fragments, poem requires stanzas/lines

## Coding Conventions

- Ruff formatting: 4-space indent, double quotes, 120-char line length
- Test files use `_test.py` suffix (e.g., `models_test.py`)
- Prefer placing feature tests under `tests/unit/features/` to mirror `src/fabulae/features/`
- Commit messages: Conventional Commits (`feat:`, `fix:`, `docs:`, `refactor:`, `test:`)

## Task Execution

### Complexity-Based Model Selection

When implementing tasks, evaluate each step's complexity and select the appropriate model:

- **Haiku** (Low complexity): Simple edits, boilerplate, file operations, CLI flags
- **Sonnet** (Medium complexity): Business logic, services, tests, refactoring
- **Opus** (High complexity): Prompt engineering, architecture, verification

### Documentation Maintenance

After implementing changes, review and update these files as needed:
- `README.md` for user-facing changes (CLI commands, features)
- `CLAUDE.md` for architectural/convention changes
- `AGENTS.md` for structural/process changes

Keep documentation concise but comprehensive for both human developers and AI coding agents.
