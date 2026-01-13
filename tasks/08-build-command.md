# Task: Build Command (Generate Story Output)

**Priority:** High - core feature for producing final output.
**Depends on:** None (LLM infrastructure already in place)

## Overview

Add a `build` command that generates one possible version of the complete narrative from a Fabulae project. This is the primary output mechanism - it takes all the structured building blocks (characters, world, plot, scenes, beats) and uses an LLM to write the actual prose, poetry, or other content format.

All LLM interactions must use structured output (Pydantic models) instead of free-form text.
All generated narrative text must pass the shared language guard (project language).

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Command Signature

```bash
fabulae build <project-dir> [--output OUTPUT_DIR] [--seed SEED] [--model MODEL] [--temperature TEMP] [--format md|txt|html]
```

## Key Concepts

### Deterministic Builds with Seeds
- The `--seed` option enables reproducible builds
- Same seed + same project + same model = same output
- Without seed, each build produces a unique variation
- Seeds allow comparing different "takes" on the same story

### Output Structure
Build outputs are written to a timestamped directory:
```
output/
└── 2024-01-15_143052_seed42/
    ├── build.json          # Build metadata
    ├── story.md            # Complete narrative
    ├── chapters/
    │   ├── 01-chapter-one.md
    │   ├── 02-chapter-two.md
    │   └── ...
    └── fragments/          # (for micro-prose)
        └── ...
```

## Implementation Steps

### Step 1: Design Build Pipeline Architecture
**Model: Opus** (OpenAI alternative: `gpt-5.2-codex`)

The build process needs to handle multiple formats with different output structures:

| Format | Input | Output |
|--------|-------|--------|
| `novel` | Chapters → Scenes → Beats | Multi-file chapters + combined story |
| `novella` | Chapters → Scenes → Beats | Smaller chapter structure |
| `short-story` | Scenes → Beats | Single file or few sections |
| `micro-prose` | Fragments | Single file with fragments |
| `poem` | Stanzas → Lines | Single file poem |

Design decisions:
1. **Chunked generation**: Generate scene-by-scene to manage context and token limits
2. **Context threading**: Pass previous scene summaries to maintain continuity (can reuse `sliding_window_scenes` pattern from create feature)
3. **Style consistency**: Include style guide in every prompt
4. **Beat expansion**: Each beat becomes prose guided by its properties

**Note:** Consider reusing context builders and graph structures from `src/fabulae/features/create/context.py` and `src/fabulae/features/create/graph.py`. The existing `SceneContext`, `FragmentContext`, and `StanzaContext` classes provide well-tested patterns for managing context windows.

### Step 2: Create Build Output Models
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/build/schemas.py`:

```python
from datetime import datetime
from pathlib import Path
from pydantic import BaseModel

class BuildMetadata(BaseModel):
    project_name: str
    format: str
    seed: int | None
    model: str
    temperature: float
    timestamp: datetime
    version: str  # Fabulae version

class SceneOutput(BaseModel):
    scene_id: str
    chapter_id: str | None
    title: str | None
    content: str
    word_count: int

class ChapterOutput(BaseModel):
    chapter_id: str
    title: str
    scenes: list[SceneOutput]
    word_count: int

class BuildOutput(BaseModel):
    metadata: BuildMetadata
    chapters: list[ChapterOutput] | None = None
    scenes: list[SceneOutput] | None = None  # For short-story without chapters
    fragments: list[str] | None = None  # For micro-prose
    poem: str | None = None  # For poem format
    full_text: str  # Combined output
    total_word_count: int
```

Add a structured output model for continuity summaries:
```python
class ContinuitySummary(BaseModel):
    summary: str
```

### Step 3: Design Generation Prompts
**Model: Opus** (OpenAI alternative: `gpt-5.2-codex`)

Create specialized prompts in `src/fabulae/features/build/prompts.py`
(using shared helpers from `src/fabulae/prompts/`):

1. **Scene generation prompt**:
   - Inputs: Scene definition, beats, characters present, location, world facts, style guide
   - Previous context: Summary of prior scenes
   - Output: Prose for the scene
   - Guidance: Expand each beat, maintain POV, follow voice guidelines

2. **Fragment generation prompt** (micro-prose):
   - Inputs: Fragment definition, style guide
   - Output: Polished flash fiction paragraph

3. **Poem generation prompt**:
   - Inputs: Stanza definitions, meter, rhyme scheme, style
   - Output: Formatted poem

4. **Continuity summary prompt**:
   - After each scene, generate a brief summary for context threading
   - Output must conform to `ContinuitySummary`

### Step 4: Implement Scene Builder
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/build/scene_builder.py`:

```python
async def build_scene(
    scene: Scene,
    project: Project,
    prior_context: str,  # Summary of previous scenes
    config: LLMConfig,
) -> SceneOutput:
    """Generate prose for a single scene."""
    # Gather scene context
    characters = get_characters_in_scene(scene, project)
    location = get_location(scene, project)
    world_facts = get_world_facts(scene, project)

    # Format prompt with all context
    prompt = format_scene_prompt(
        scene=scene,
        characters=characters,
        location=location,
        world_facts=world_facts,
        style=project.style,
        prior_context=prior_context,
    )

    # Generate prose
    agent = create_agent(SceneOutput, prompt, config)
    result = await agent.run()

    return result.data
```

Structured output example for continuity summaries:
```python
summary_agent = create_agent(ContinuitySummary, summary_prompt, config)
continuity = (await summary_agent.run()).data.summary
```

### Step 5: Implement Build Orchestrator
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/build/service.py`:

```python
async def build_project(
    project: Project,
    config: LLMConfig,
    seed: int | None = None,
) -> BuildOutput:
    """Orchestrate the complete build process."""
    if seed is not None:
        # Set random seed for reproducibility
        random.seed(seed)

    format = project.plot.format

    if format in ["novel", "novella"]:
        return await build_chaptered(project, config, seed)
    elif format == "short-story":
        return await build_short_story(project, config, seed)
    elif format == "micro-prose":
        return await build_micro_prose(project, config, seed)
    elif format == "poem":
        return await build_poem(project, config, seed)

### Step 6: Enforce Project Language
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Apply the shared language guard to all generated narrative text:
- Scene prose (`SceneOutput.content`)
- Fragment text (micro-prose)
- Poem output (stanzas/lines)
- Full combined output

Retry with a strict language instruction on mismatch.
    else:
        raise ValueError(f"Unknown format: {format}")
```

### Step 6: Implement Format-Specific Builders
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

**Chaptered builder** (novel, novella):
```python
async def build_chaptered(
    project: Project,
    config: LLMConfig,
    seed: int | None,
) -> BuildOutput:
    chapters = []
    prior_context = ""

    for chapter in project.plot.chapters:
        chapter_scenes = []
        for scene_id in chapter.scene_ids:
            scene = get_scene_by_id(scene_id, project)
            scene_output = await build_scene(scene, project, prior_context, config)
            chapter_scenes.append(scene_output)
            prior_context = update_context(prior_context, scene_output)

        chapters.append(ChapterOutput(
            chapter_id=chapter.id,
            title=chapter.title,
            scenes=chapter_scenes,
            word_count=sum(s.word_count for s in chapter_scenes),
        ))

    return BuildOutput(
        chapters=chapters,
        full_text=combine_chapters(chapters),
        total_word_count=sum(c.word_count for c in chapters),
        metadata=...,
    )
```

**Micro-prose builder**:
```python
async def build_micro_prose(
    project: Project,
    config: LLMConfig,
    seed: int | None,
) -> BuildOutput:
    fragments = []
    for fragment in project.plot.fragments:
        content = await generate_fragment(fragment, project, config)
        fragments.append(content)

    return BuildOutput(
        fragments=fragments,
        full_text="\n\n".join(fragments),
        ...
    )
```

### Step 7: Implement CLI Command
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/build/cli.py` and keep CLI command code in the feature slice:

```python
from fabulae.features.build.service import build_project

def register_build_command(app: typer.Typer) -> None:
    @app.command()
    def build(
        project_dir: Annotated[Path, typer.Argument(help="Path to Fabulae project")],
        output: Annotated[Path | None, typer.Option("--output", "-o")] = None,
        seed: Annotated[int | None, typer.Option("--seed", "-s")] = None,
        model: str = model_option(),
        temperature: float = temperature_option(),
        format: Annotated[str, typer.Option("--format", "-f")] = "md",
    ) -> None:
        """
        Build a complete narrative from a Fabulae project.

        Generates prose/poetry from the project's structural elements using an LLM.
        Each build with a different seed produces a unique variation.

        Examples:
            fabulae build ./my-novel
            fabulae build ./my-novel --seed 42 --output ./drafts
            fabulae build ./my-poem --format html
        """
        # Validate project first
        project = load_project(project_dir)

        # Determine output directory
        if output is None:
            output = project_dir / "output"

        # Create timestamped build directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        seed_suffix = f"_seed{seed}" if seed else ""
        build_dir = output / f"{timestamp}{seed_suffix}"
        build_dir.mkdir(parents=True, exist_ok=True)

        # Run build
        config = LLMConfig(model=model, temperature=temperature)
        result = asyncio.run(build_project(project, config, seed))

        # Write outputs
        write_build_output(result, build_dir, format)

        # Print summary
        typer.echo(f"Build complete: {build_dir}")
        typer.echo(f"Total words: {result.total_word_count}")
```

Wire it in `src/fabulae/main.py`:

```python
from fabulae.features.build.cli import register_build_command

register_build_command(app)
```

### Step 8: Implement Output Writers
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/build/writer.py`:

```python
def write_build_output(
    result: BuildOutput,
    output_dir: Path,
    format: str,
) -> None:
    """Write build output to files."""
    # Write metadata
    (output_dir / "build.json").write_text(
        result.metadata.model_dump_json(indent=2)
    )

    # Write combined story
    if format == "md":
        (output_dir / "story.md").write_text(result.full_text)
    elif format == "txt":
        (output_dir / "story.txt").write_text(strip_markdown(result.full_text))
    elif format == "html":
        (output_dir / "story.html").write_text(markdown_to_html(result.full_text))

    # Write individual chapters (if applicable)
    if result.chapters:
        chapters_dir = output_dir / "chapters"
        chapters_dir.mkdir(exist_ok=True)
        for i, chapter in enumerate(result.chapters, 1):
            filename = f"{i:02d}-{slugify(chapter.title)}.{format}"
            (chapters_dir / filename).write_text(format_chapter(chapter, format))
```

### Step 9: Add Progress Feedback
**Model: Haiku** (OpenAI alternative: `gpt-5.1-codex-mini`)

Building takes time, so provide feedback:

```python
from rich.progress import Progress, SpinnerColumn, TextColumn

with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
) as progress:
    task = progress.add_task("Building...", total=len(scenes))

    for scene in scenes:
        progress.update(task, description=f"Building {scene.id}...")
        # Generate scene
        progress.advance(task)
```

### Step 10: Implement Seed-Based Reproducibility
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

1. Set Python random seed
2. Pass seed to LLM (if supported) or document that exact reproducibility depends on model
3. Store seed in build metadata for reference

Note: True reproducibility may vary by LLM provider. Document limitations.

### Step 11: Write Tests
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `tests/unit/features/build_test.py`:

1. Test build orchestrator with mocked scene builder
2. Test each format-specific builder
3. Test output file structure
4. Test CLI argument handling
5. Test seed reproducibility (with mocks)
6. Test output format conversion (md, txt, html)

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - No duplicate code introduced
   - Error handling is appropriate
   - Type hints are complete

2. **Integration Check:**
   - All new code integrates properly with existing code
   - Imports are correct
   - No circular dependencies

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Acceptance Criteria Validation:**
   - Verify each acceptance criterion is met
   - Test the build command manually with different formats

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Review and update `AGENTS.md` if project structure, testing guidelines, or commit conventions changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/build/schemas.py` | Create | Build output models |
| `src/fabulae/features/build/__init__.py` | Create | Package init |
| `src/fabulae/features/build/service.py` | Create | Build orchestration |
| `src/fabulae/features/build/scene_builder.py` | Create | Scene prose generation |
| `src/fabulae/features/build/writer.py` | Create | Output file writing |
| `src/fabulae/features/build/prompts.py` | Create | Build prompts |
| `src/fabulae/features/build/cli.py` | Create | CLI command implementation |
| `src/fabulae/main.py` | Modify | Add build command |
| `tests/unit/features/build_test.py` | Create | Unit tests |

## Example Usage

```bash
# Basic build
$ fabulae build ./my-novel
Building...
  ✓ Chapter 1: The Discovery (3 scenes)
  ✓ Chapter 2: The Investigation (5 scenes)
  ✓ Chapter 3: The Revelation (4 scenes)
Build complete: ./my-novel/output/2024-01-15_143052
Total words: 12,453

# Reproducible build with seed
$ fabulae build ./my-novel --seed 42 --output ./drafts
Build complete: ./drafts/2024-01-15_143215_seed42
Total words: 12,501

# Build with different settings
$ fabulae build ./my-novel --seed 42 --temperature 0.9 --model llama3:8b
Build complete: ./my-novel/output/2024-01-15_143400_seed42
Total words: 12,387

# Compare builds
$ diff ./drafts/2024-01-15_143052/story.md ./drafts/2024-01-15_143215_seed42/story.md
```

## Output Structure Example

```
my-novel/output/2024-01-15_143052_seed42/
├── build.json
│   {
│     "project_name": "The Synesthesia Murders",
│     "format": "novel",
│     "seed": 42,
│     "model": "ministral-3:3b",
│     "temperature": 0.7,
│     "timestamp": "2024-01-15T14:30:52",
│     "version": "0.1.0"
│   }
├── story.md              # Complete narrative
├── chapters/
│   ├── 01-the-discovery.md
│   ├── 02-the-investigation.md
│   └── 03-the-revelation.md
```

## Acceptance Criteria

- [ ] `fabulae build` generates complete narrative output
- [ ] All five formats (novel, novella, short-story, micro-prose, poem) work
- [ ] Output directory structure is correct
- [ ] `--seed` enables reproducible builds
- [ ] `--output` redirects output location
- [ ] `--format` option works (md, txt, html)
- [ ] `--model` and `--temperature` work correctly
- [ ] Progress feedback during generation
- [ ] Build metadata saved to build.json
- [ ] All tests pass
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Future Enhancements

- `--continue` option to resume interrupted builds
- `--chapter` option to rebuild specific chapters only
- Build comparison tool (`fabulae diff-builds`)
- Export to additional formats (epub, pdf via pandoc)
- Streaming output for real-time viewing
