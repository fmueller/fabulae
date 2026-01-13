# Task: Shared Entity Suggest System

**Priority:** Medium - improves code reuse and consistency.
**Depends on:** `05-entity-crud-commands.md`, `01-create-pipeline-simplification.md` (completed)

## Overview

After the Entity CRUD commands are implemented, refactor the `create` command to use the same entity suggestion functionality. This creates a shared system where:

1. **CRUD `suggest` commands** use shared suggestion functions
2. **`create` command** uses the same functions for generating characters, locations, etc.
3. **Consistent quality** across both features
4. **Single source of truth** for entity generation prompts

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Current Duplication Problem

Once Entity CRUD is implemented, there will be two places generating entities:

### Create Command (current)
```python
# In src/fabulae/features/create/pipelines/prose.py (batch) and sequential.py (sequential)
async def generate_characters(outline, style, shape, config):
    # Custom character generation logic
    # Custom prompts (prompts.py and prompts_v2.py)
    # Custom validation
```

Note: The create command now supports both batch (`--pipeline batch`) and sequential (`--pipeline sequential`) pipelines for all formats. The shared entity generation should work with both approaches.

### CRUD Suggest Command (new)
```python
# In src/fabulae/features/entities/character.py
@character_app.command("suggest")
async def suggest(project_dir, idea, model, temperature):
    # Different character generation logic
    # Different prompts
    # Different validation
```

This duplication leads to:
- Inconsistent output quality
- Duplicated prompt engineering effort
- Bug fixes needed in multiple places
- Divergent validation rules

## Proposed Architecture

### Shared Entity Generation Layer

```
src/fabulae/features/entities/
├── __init__.py
├── generation/              # NEW: Shared generation functions
│   ├── __init__.py
│   ├── character.py        # suggest_character()
│   ├── scene.py            # suggest_scene()
│   ├── beat.py             # suggest_beat()
│   ├── world_fact.py       # suggest_world_fact()
│   └── prompts.py          # Shared prompts
├── character.py            # CRUD CLI using generation/
├── scene.py                # CRUD CLI using generation/
├── beat.py                 # CRUD CLI using generation/
└── ...
```

### Usage Pattern

```python
# CRUD suggest command
from fabulae.features.entities.generation.character import suggest_character

@character_app.command("suggest")
async def suggest_cmd(project_dir, idea, ...):
    project = load_project(project_dir)
    character = await suggest_character(
        project=project,
        idea=idea,
        config=llm_config,
    )
    # Display and confirm...

# Create command
from fabulae.features.entities.generation.character import suggest_character

async def generate_characters_for_create(project_state, shape, config):
    characters = []
    for slot in shape.character_slots:
        char = await suggest_character(
            project=project_state,  # Partial project during creation
            idea=slot.description,  # Use shape slot as guidance
            role_hint=slot.role,
            config=config,
        )
        characters.append(char)
    return characters
```

## Implementation Steps

### Step 1: Create Generation Module Structure
**Model: Haiku**

Create the shared generation module:

```bash
mkdir -p src/fabulae/features/entities/generation
touch src/fabulae/features/entities/generation/__init__.py
```

**Files to create:**
- `src/fabulae/features/entities/generation/__init__.py`

**Acceptance criteria:**
- Generation module exists as subpackage of entities

### Step 2: Extract Character Generation
**Model: Sonnet**

Create `src/fabulae/features/entities/generation/character.py`:

```python
from fabulae.models import Character, Project
from fabulae.llm import LLMConfig, create_agent
from fabulae.features.entities.generation.prompts import build_character_prompt
from fabulae.features.entities.generation.schemas import CharacterSuggestionOutput

async def suggest_character(
    project: Project | None = None,
    idea: str | None = None,
    role_hint: str | None = None,
    name_hint: str | None = None,
    existing_characters: list[Character] | None = None,
    style_context: str | None = None,
    premise: str | None = None,
    config: LLMConfig = None,
) -> Character:
    """
    Suggest a character based on context.

    This function is used by both:
    - `fabulae character suggest` command
    - `fabulae create` command's character generation phase

    Args:
        project: Existing project for context (for CRUD suggest)
        idea: User-provided guidance text
        role_hint: Suggested role (protagonist, antagonist, supporting)
        name_hint: Suggested name (from shape slot)
        existing_characters: Characters already in project (for avoiding duplicates)
        style_context: Tone/voice context for consistency
        premise: Story premise for thematic alignment
        config: LLM configuration

    Returns:
        Generated Character object
    """
    # Build context from project or individual parameters
    if project:
        existing_characters = existing_characters or project.characters
        premise = premise or (project.plot.premise if project.plot else None)
        style_context = style_context or _extract_style_from_project(project)

    # Build prompt
    prompt = build_character_prompt(
        idea=idea,
        role_hint=role_hint,
        name_hint=name_hint,
        existing_characters=existing_characters or [],
        style_context=style_context,
        premise=premise,
    )

    # Generate
    agent = create_agent(CharacterSuggestionOutput, prompt, config)
    result = await agent.run()

    # Convert to Character model
    return Character(
        id=result.data.id,
        name=result.data.name,
        role=result.data.role,
        desire=result.data.desire,
        need=result.data.need,
        flaw=result.data.flaw,
        secret=result.data.secret,
        traits=result.data.traits,
    )
```

**Files to create:**
- `src/fabulae/features/entities/generation/character.py`

**Acceptance criteria:**
- Function handles both CRUD and create contexts
- Parameters are flexible for different use cases
- Output is standard Character model

### Step 3: Create Shared Prompts Module
**Model: Opus**

Create `src/fabulae/features/entities/generation/prompts.py`:

```python
from fabulae.models import Character

def build_character_prompt(
    idea: str | None,
    role_hint: str | None,
    name_hint: str | None,
    existing_characters: list[Character],
    style_context: str | None,
    premise: str | None,
) -> str:
    """Build a focused prompt for character generation."""

    # Existing characters section
    existing_section = ""
    if existing_characters:
        char_list = "\n".join([
            f"- {c.name} ({c.id}): {c.role}"
            for c in existing_characters
        ])
        existing_section = f"""
EXISTING CHARACTERS (avoid duplicating these):
{char_list}
"""

    # Role hint
    role_section = ""
    if role_hint:
        role_section = f"\nSuggested role: {role_hint}"

    # Guidance
    guidance_section = ""
    if idea:
        guidance_section = f"\nUser guidance: {idea}"

    # Context
    context_section = ""
    if premise:
        context_section += f"\nStory premise: {premise}"
    if style_context:
        context_section += f"\nStyle: {style_context}"

    return f"""
Create a character for a story.
{role_section}
{guidance_section}
{context_section}
{existing_section}

Generate a character with:
- id: lowercase-with-hyphens identifier
- name: Full name
- role: protagonist, antagonist, or supporting
- desire: What do they want? (1 sentence)
- need: What do they actually need? (1 sentence)
- flaw: Their key weakness (1-3 words)
- secret: Something hidden (1 sentence, optional)
- traits: 2-4 personality traits

{"Use suggested name: " + name_hint if name_hint else "Choose an appropriate name."}

Create a unique character that complements the existing cast.
"""

def build_scene_prompt(...) -> str:
    """Build prompt for scene generation."""
    ...

def build_beat_prompt(...) -> str:
    """Build prompt for beat generation."""
    ...

def build_world_fact_prompt(...) -> str:
    """Build prompt for world fact generation."""
    ...
```

**Files to create:**
- `src/fabulae/features/entities/generation/prompts.py`

**Acceptance criteria:**
- Prompts handle all contexts (CRUD and create)
- Clear guidance for LLM
- Existing entities referenced to avoid duplication

### Step 4: Create Shared Schemas
**Model: Sonnet**

Create `src/fabulae/features/entities/generation/schemas.py`:

```python
from pydantic import BaseModel, Field

class CharacterSuggestionOutput(BaseModel):
    """LLM output for character suggestion."""
    id: str = Field(description="Character ID in lowercase-with-hyphens format")
    name: str = Field(description="Character's full name")
    role: str = Field(description="Role: protagonist, antagonist, or supporting")
    desire: str | None = Field(None, description="What they want")
    need: str | None = Field(None, description="What they actually need")
    flaw: str | None = Field(None, description="Key weakness")
    secret: str | None = Field(None, description="Hidden aspect")
    traits: list[str] = Field(default_factory=list, description="Personality traits")

class SceneSuggestionOutput(BaseModel):
    """LLM output for scene suggestion."""
    id: str
    title: str
    summary: str
    characters: list[str] = []  # Character IDs

class BeatSuggestionOutput(BaseModel):
    """LLM output for beat suggestion."""
    id: str
    kind: str
    summary: str

class WorldFactSuggestionOutput(BaseModel):
    """LLM output for world fact suggestion."""
    id: str
    type: str  # location, culture, history, rule, object
    facts: list[str]
```

**Files to create:**
- `src/fabulae/features/entities/generation/schemas.py`

**Acceptance criteria:**
- Schemas match expected LLM output
- All entity types have corresponding schema
- Field descriptions guide LLM output

### Step 5: Update CRUD Commands to Use Shared Functions
**Model: Sonnet**

Refactor CRUD suggest commands:

```python
# In src/fabulae/features/entities/character.py

from fabulae.features.entities.generation.character import suggest_character

@character_app.command("suggest")
async def suggest_cmd(
    project_dir: Path,
    idea: str | None = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    yes: bool = typer.Option(False, "--yes", "-y"),
):
    """Suggest a new character based on project context."""
    project = load_project(project_dir)
    config = LLMConfig(model=model, temperature=temperature)

    # Use shared generation function
    character = await suggest_character(
        project=project,
        idea=idea,
        config=config,
    )

    # Display and confirm
    display_character(character)
    if yes or typer.confirm("Add this character?"):
        project.characters.append(character)
        save_project(project, project_dir)
        typer.echo(f"Added character: {character.name} ({character.id})")
```

**Files to modify:**
- `src/fabulae/features/entities/character.py`
- `src/fabulae/features/entities/scene.py`
- `src/fabulae/features/entities/beat.py`
- `src/fabulae/features/entities/world.py`

**Acceptance criteria:**
- All suggest commands use shared functions
- No duplicate generation logic in CRUD files

### Step 6: Update Create Command to Use Shared Functions
**Model: Sonnet**

Refactor create pipeline:

```python
# In src/fabulae/features/create/pipelines/prose.py

from fabulae.features.entities.generation.character import suggest_character
from fabulae.features.entities.generation.scene import suggest_scene

async def generate_characters(
    shape: StoryShape | None,
    style: StyleOutput,
    premise: str,
    config: LLMConfig,
    progress: CreateProgress,
) -> list[Character]:
    """Generate characters using shared suggestion function."""
    characters = []

    if shape and shape.character_slots:
        # Use shape slots as guidance
        for slot in shape.character_slots:
            with progress.stage(f"Creating {slot.role} character..."):
                char = await suggest_character(
                    idea=slot.description,
                    role_hint=slot.role,
                    name_hint=slot.suggested_name,
                    existing_characters=characters,
                    style_context=style.tone,
                    premise=premise,
                    config=config,
                )
                characters.append(char)
    else:
        # Generate default character set
        for role in ["protagonist", "antagonist", "supporting"]:
            with progress.stage(f"Creating {role}..."):
                char = await suggest_character(
                    role_hint=role,
                    existing_characters=characters,
                    style_context=style.tone,
                    premise=premise,
                    config=config,
                )
                characters.append(char)

    return characters
```

**Files to modify:**
- `src/fabulae/features/create/pipelines/prose.py`
- `src/fabulae/features/create/pipelines/micro_prose.py`
- `src/fabulae/features/create/pipelines/poem.py`

**Acceptance criteria:**
- Create command uses shared generation functions
- Story shape guidance properly passed to shared functions
- Output quality matches or improves previous implementation

### Step 7: Remove Duplicate Code from Create
**Model: Sonnet**

Delete redundant generation code from create feature:

```python
# REMOVE from src/fabulae/features/create/:
# - Character generation prompts (now in entities/generation/)
# - Character generation schemas (now in entities/generation/)
# - Scene generation logic (if duplicated)
# - Beat generation logic (if duplicated)
```

**Files to modify:**
- `src/fabulae/features/create/prompts.py` - remove entity-specific prompts
- `src/fabulae/features/create/schemas.py` - remove entity generation schemas

**Acceptance criteria:**
- No duplicate entity generation code
- Create-specific prompts remain (outline, structure)
- Shared code lives in entities/generation/

### Step 8: Write Tests
**Model: Sonnet**

Create tests for shared generation:

**`tests/unit/features/entities/generation/test_character.py`:**
- Test suggest_character with project context
- Test suggest_character with minimal context (create mode)
- Test existing characters are avoided
- Test role hints are respected

**`tests/unit/features/entities/generation/test_prompts.py`:**
- Test prompt building with various contexts
- Test prompt includes relevant information
- Test prompt excludes irrelevant information

**Acceptance criteria:**
- Shared generation functions tested
- Both usage contexts (CRUD and create) covered
- Tests use mocked LLM
- `uv run pytest` passes

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - No duplicate code remains
   - Error handling is appropriate
   - Type hints are complete

2. **Integration Check:**
   - All new code integrates properly with existing code
   - Both CRUD and create commands use shared functions
   - Imports are correct
   - No circular dependencies

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Acceptance Criteria Validation:**
   - Verify each acceptance criterion is met
   - Test both CRUD suggest and create commands

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Review and update `AGENTS.md` if project structure, testing guidelines, or commit conventions changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create

| File | Description |
|------|-------------|
| `src/fabulae/features/entities/generation/__init__.py` | Package init |
| `src/fabulae/features/entities/generation/character.py` | Character generation |
| `src/fabulae/features/entities/generation/scene.py` | Scene generation |
| `src/fabulae/features/entities/generation/beat.py` | Beat generation |
| `src/fabulae/features/entities/generation/world_fact.py` | World fact generation |
| `src/fabulae/features/entities/generation/prompts.py` | Shared prompts |
| `src/fabulae/features/entities/generation/schemas.py` | Output schemas |
| `tests/unit/features/entities/generation/test_*.py` | Tests |

## Files to Modify

| File | Changes |
|------|---------|
| `src/fabulae/features/entities/character.py` | Use shared generation |
| `src/fabulae/features/entities/scene.py` | Use shared generation |
| `src/fabulae/features/entities/beat.py` | Use shared generation |
| `src/fabulae/features/entities/world.py` | Use shared generation |
| `src/fabulae/features/create/pipelines/prose.py` | Use shared generation (batch pipeline) |
| `src/fabulae/features/create/pipelines/sequential.py` | Use shared generation (sequential pipeline) |
| `src/fabulae/features/create/pipelines/micro_prose.py` | Use shared generation (batch) |
| `src/fabulae/features/create/pipelines/micro_prose_sequential.py` | Use shared generation (sequential) |
| `src/fabulae/features/create/pipelines/poem.py` | Use shared generation (batch) |
| `src/fabulae/features/create/pipelines/poem_sequential.py` | Use shared generation (sequential) |
| `src/fabulae/features/create/prompts.py` | Remove duplicated prompts |
| `src/fabulae/features/create/prompts_v2.py` | Remove duplicated prompts (per-unit prompts) |
| `src/fabulae/features/create/schemas.py` | Remove duplicated schemas |

## Acceptance Criteria

- [ ] Shared generation module created
- [ ] All entity types have shared generation functions
- [ ] CRUD suggest commands use shared functions
- [ ] Create command uses shared functions
- [ ] No duplicate generation code remains
- [ ] Output quality maintained or improved
- [ ] All tests pass
- [ ] `uv run ruff check`, `uv run mypy`, and `uv run pytest` pass

## Benefits

1. **Single source of truth** for entity generation
2. **Consistent quality** across CRUD and create
3. **Easier maintenance** - fix bugs in one place
4. **Better prompts** - consolidate prompt engineering effort
5. **Reusable functions** for future features (expand, enrich, etc.)
