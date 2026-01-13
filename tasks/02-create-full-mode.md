# Task: Create Full Mode Flag

**Priority:** Medium - improves workflow flexibility.
**Depends on:** `01-create-pipeline-simplification.md` (completed)

## Overview

Add a `--full` flag to the `create` command that controls the depth of generation:

- **Without `--full` (default):** Stop at a rough outline with chapter summaries and scene suggestions
- **With `--full`:** Generate everything including all beats and detailed scene content

This allows users to quickly generate a story skeleton, review it, and then optionally expand to full detail.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Current Behavior

The current `create` command always generates the complete project including:
- Style and premise
- Full outline with chapters and scenes
- All characters with detailed attributes
- World facts and locations
- All beats for every scene
- Optional enrichment pass

This "all or nothing" approach has drawbacks:
- Long generation time for large projects
- No opportunity to review structure before investing in details
- Wasted LLM tokens if the user wants to change direction

## Proposed Behavior

### Default Mode (Outline Only)
```bash
fabulae create ./my-novel --idea "detective with synesthesia" --format novel
```

Generates:
- Style (tone, voice, POV, tense)
- Expanded premise
- Chapter structure with titles and summaries
- Scene placeholders with titles and brief summaries
- Character sketches (name, role, one-line description)
- Location list (names only)

Does NOT generate:
- Detailed character attributes (desire, need, flaw, secret, traits)
- Detailed beats for scenes
- World fact details
- Enrichment content

### Full Mode
```bash
fabulae create ./my-novel --idea "detective with synesthesia" --format novel --full
```

Generates everything (current behavior).

## Implementation Steps

### Step 1: Add CLI Flag
**Model: Haiku**

Update `src/fabulae/features/create/cli.py`:

```python
@app.command()
def create(
    ...
    full: Annotated[bool, typer.Option(
        "--full", "-F",
        help="Generate full project with all details. Default generates outline only."
    )] = False,
):
    """
    Create a new Fabulae project from an idea.

    By default, generates a rough outline (chapters, scene summaries, character sketches).
    Use --full to generate complete project with all beats and details.

    Examples:
        fabulae create ./my-novel --idea "..." --format novel          # Outline only
        fabulae create ./my-novel --idea "..." --format novel --full   # Full details
    """
```

**Files to modify:**
- `src/fabulae/features/create/cli.py`

**Acceptance criteria:**
- `--full` / `-F` flag available on create command
- Help text explains the difference
- Flag defaults to False

### Step 2: Create Outline-Only Schemas
**Model: Sonnet**

Add simplified output schemas in `src/fabulae/features/create/schemas.py`:

```python
class CharacterSketchOutput(BaseModel):
    """Minimal character info for outline mode."""
    id: str
    name: str
    role: str
    description: str = Field(description="One-line character description")

class SceneSketchOutput(BaseModel):
    """Minimal scene info for outline mode."""
    id: str
    title: str
    summary: str = Field(description="2-3 sentence scene summary")
    character_ids: list[str] = []

class ChapterSketchOutput(BaseModel):
    """Chapter with scene sketches for outline mode."""
    id: str
    title: str
    summary: str
    scenes: list[SceneSketchOutput]

class OutlineOutput(BaseModel):
    """Complete outline for outline-only mode."""
    title: str
    premise: str
    chapters: list[ChapterSketchOutput]
    characters: list[CharacterSketchOutput]
    locations: list[str]  # Just names/IDs
```

**Files to modify:**
- `src/fabulae/features/create/schemas.py`

**Acceptance criteria:**
- Outline schemas are simpler than full schemas
- Character sketches have minimal fields
- Scene sketches have no beats

### Step 3: Create Outline-Only Prompts
**Model: Sonnet**

Add outline-specific prompts in `src/fabulae/features/create/prompts.py`:

```python
def build_outline_only_prompt(idea: str, format: str, style: StyleOutput) -> str:
    """Build prompt for outline-only generation."""
    return f"""
Create a story outline from this idea: {idea}

Format: {format}
Tone: {style.tone}
Voice: {style.voice}

Generate:
1. Title for the story
2. Expanded premise (2-4 sentences)
3. Chapter structure:
   - For each chapter: title, summary (2-3 sentences)
   - For each scene in chapter: title, summary (1-2 sentences), which characters appear
4. Character sketches:
   - Name, role (protagonist/antagonist/supporting), one-line description
5. Location list (just names)

This is an OUTLINE only - do not generate detailed beats, character backstories, or world facts.
Keep it high-level and structural.
"""
```

**Files to modify:**
- `src/fabulae/features/create/prompts.py`

**Acceptance criteria:**
- Outline prompts request minimal detail
- Clear instruction to stay high-level
- Output matches OutlineOutput schema

### Step 4: Implement Outline-Only Pipeline
**Model: Sonnet**

Create or modify pipeline to support outline mode:

```python
# In src/fabulae/features/create/pipelines/prose.py or new file

async def generate_outline_only(
    idea: str,
    format: str,
    shape: StoryShape | None,
    config: LLMConfig,
    progress: CreateProgress,
) -> Project:
    """Generate outline-only project."""

    # Phase 1: Style (same as full)
    with progress.stage("Determining style..."):
        style = await generate_style(idea, format, config)
    progress.success("Style determined")

    # Phase 2: Outline structure and content (combined, simplified)
    with progress.stage("Creating outline..."):
        outline = await generate_outline(idea, format, style, shape, config)
    progress.success(f"Outline created: {len(outline.chapters)} chapters")

    # Phase 3: Convert to Project structure
    project = convert_outline_to_project(outline, style, format)

    return project

def convert_outline_to_project(
    outline: OutlineOutput,
    style: StyleOutput,
    format: str,
) -> Project:
    """Convert outline to Project with placeholder content."""
    # Characters with minimal info
    characters = [
        Character(
            id=c.id,
            name=c.name,
            role=c.role,
            # Other fields left as None - to be filled in --full mode
        )
        for c in outline.characters
    ]

    # Scenes with no beats
    scenes = []
    for chapter in outline.chapters:
        for scene_sketch in chapter.scenes:
            scenes.append(Scene(
                id=scene_sketch.id,
                title=scene_sketch.title,
                summary=scene_sketch.summary,
                characters=scene_sketch.character_ids,
                beats=[],  # Empty - to be filled in --full mode
            ))

    # ... assemble Project
```

**Files to modify:**
- `src/fabulae/features/create/pipelines/prose.py` - add outline mode
- `src/fabulae/features/create/service.py` - route based on full flag

**Acceptance criteria:**
- Outline mode completes in ~30% of full mode time
- Output is valid Project structure
- Missing details are clearly empty/None (not placeholders)

### Step 5: Add Expand Command (Future)
**Model: Sonnet**

Design (but don't implement yet) an `expand` command to fill in details later:

```bash
# Future command - document in task for reference
fabulae expand ./my-novel  # Expand outline to full project
fabulae expand ./my-novel --chapter chapter-02  # Expand specific chapter
fabulae expand ./my-novel --scene scene-05  # Expand specific scene
```

This is OUT OF SCOPE for this task but should be documented as follow-up.

**Files to modify:**
- None (documentation only)

### Step 6: Update Service Layer
**Model: Sonnet**

Modify service to accept and pass through full flag:

```python
# In src/fabulae/features/create/service.py

async def generate_project_from_idea(
    idea: str,
    output_dir: Path,
    format: str,
    full: bool = False,  # New parameter
    ...
) -> Project:
    if full:
        return await generate_prose(...)  # Current full pipeline
    else:
        return await generate_outline_only(...)  # New outline pipeline
```

**Files to modify:**
- `src/fabulae/features/create/service.py`

**Acceptance criteria:**
- Service layer properly routes based on full flag
- Both modes produce valid Project output

### Step 7: Write Tests
**Model: Sonnet**

Create tests for outline mode:

**`tests/unit/features/create/test_outline_mode.py`:**
- Test outline-only generation produces valid Project
- Test outline has chapters and scenes but no beats
- Test characters have name/role but no detailed attributes
- Test full mode still works as before
- Compare generation time between modes (outline should be faster)

**Acceptance criteria:**
- Both modes have test coverage
- Tests verify correct schema usage
- Tests use mocked LLM
- `uv run pytest` passes

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
   - Test the feature manually if applicable

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Review and update `AGENTS.md` if project structure, testing guidelines, or commit conventions changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/create/cli.py` | Modify | Add --full flag |
| `src/fabulae/features/create/schemas.py` | Modify | Add outline schemas |
| `src/fabulae/features/create/prompts.py` | Modify | Add outline prompts |
| `src/fabulae/features/create/pipelines/prose.py` | Modify | Add outline pipeline |
| `src/fabulae/features/create/service.py` | Modify | Route based on flag |
| `tests/unit/features/create/test_outline_mode.py` | Create | Outline mode tests |

## Acceptance Criteria

- [ ] `--full` / `-F` flag available on create command
- [ ] Default (no flag) generates outline only
- [ ] `--full` generates complete project (current behavior)
- [ ] Outline mode is significantly faster than full mode
- [ ] Outline output is valid Project structure
- [ ] All tests pass
- [ ] `uv run ruff check`, `uv run mypy`, and `uv run pytest` pass

## Example Output

### Outline Mode (default)
```yaml
# characters.yml
- id: vera
  name: Vera Mellifer
  role: protagonist
  # Note: no desire, need, flaw, secret, traits

- id: marcus
  name: Marcus Stone
  role: antagonist
```

```yaml
# plot.yml
chapters:
  - id: chapter-01
    title: The Discovery
    summary: Vera is called to investigate a murder at the symphony hall...
    scene_ids: [scene-01, scene-02, scene-03]

scenes:
  - id: scene-01
    title: The Crime Scene
    summary: Vera arrives at the symphony hall to find the conductor dead.
    characters: [vera]
    beats: []  # Empty in outline mode
```

### Full Mode (--full)
```yaml
# characters.yml
- id: vera
  name: Vera Mellifer
  role: protagonist
  desire: To uncover the truth behind the murder
  need: To reconnect with her own emotions
  flaw: Emotionally guarded
  secret: She experiences synesthesia herself
  traits: [analytical, observant, methodical]
```

```yaml
# plot.yml
scenes:
  - id: scene-01
    title: The Crime Scene
    summary: Vera arrives at the symphony hall to find the conductor dead.
    characters: [vera]
    beats:
      - id: beat-01
        kind: action
        summary: Vera examines the body, noting unusual details
      - id: beat-02
        kind: revelation
        summary: The colors she sees in the ambient sound reveal something wrong
```

## Future Enhancement: Expand Command

After outline generation, users should be able to expand to full detail:

```bash
# Generate outline
fabulae create ./my-novel --idea "..." --format novel

# Review and edit outline manually...

# Expand to full project
fabulae expand ./my-novel

# Or expand incrementally
fabulae expand ./my-novel --chapter chapter-01
```

This command is OUT OF SCOPE but documented here for future implementation.
