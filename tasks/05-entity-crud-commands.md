# Task: Entity CRUD Commands

**Priority:** High - core workflow feature.
**Depends on:** `04-remove-narrative-patterns.md` (should be completed first to avoid implementing dead code)

## Overview

Add CRUD (Create, Read, Update, Delete) commands for all main entities in a Fabulae project:
- `character` - Story characters
- `beat` - Dramatic beats within scenes
- `scene` - Scenes containing beats
- `chapter` - Chapters grouping scenes
- `world` - World facts (locations, cultures, rules, etc.)

**Note:** `plot-pattern` commands are NOT included. The narrative patterns feature is being removed in Task 04 as dead code. Story shapes (`--shape`) are the implemented alternative for structural guidance.

Each entity supports: `add`, `suggest`, `list`, `remove`, `edit` (and `move` where applicable).

All `suggest` commands must use structured output (Pydantic models) instead of free-form text.
All `suggest` commands must enforce project language via the shared language guard.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Command Signatures

```bash
# Character commands
fabulae character add <project-dir> --id "char-id" --name "Name" [--role protagonist] [--desire "..."] ...
fabulae character suggest <project-dir> [--idea "guidance text or file path"] [--yes] [--model MODEL] [--temperature TEMP]
fabulae character list <project-dir> [--format table|json|yaml]
fabulae character remove <project-dir> <character-id>
fabulae character edit <project-dir> <character-id> [--name "New Name"] [--role antagonist] ...

# Beat commands
fabulae beat add <project-dir> --scene "scene-id" --id "beat-id" --kind action [--summary "..."] ...
fabulae beat suggest <project-dir> --scene "scene-id" [--idea "..."] [--yes] [--model MODEL] [--temperature TEMP]
fabulae beat list <project-dir> [--scene "scene-id"] [--format table|json|yaml]
fabulae beat move <project-dir> <beat-id> --to-scene "scene-id" [--position 0]
fabulae beat remove <project-dir> <beat-id>
fabulae beat edit <project-dir> <beat-id> [--kind dialogue] [--summary "..."] ...

# Scene commands
fabulae scene add <project-dir> --id "scene-id" [--chapter "chapter-id"] [--location "loc-id"] [--time "..."] ...
fabulae scene suggest <project-dir> [--chapter "chapter-id"] [--idea "..."] [--yes] [--model MODEL] [--temperature TEMP]
fabulae scene list <project-dir> [--chapter "chapter-id"] [--format table|json|yaml]
fabulae scene move <project-dir> <scene-id> --to-chapter "chapter-id" [--position 0]
fabulae scene remove <project-dir> <scene-id>
fabulae scene edit <project-dir> <scene-id> [--location "loc-id"] [--time "..."] ...

# Chapter commands
fabulae chapter add <project-dir> --id "chapter-id" [--title "..."] [--summary "..."]
fabulae chapter suggest <project-dir> [--idea "..."] [--yes] [--model MODEL] [--temperature TEMP]
fabulae chapter list <project-dir> [--format table|json|yaml]
fabulae chapter remove <project-dir> <chapter-id>
fabulae chapter edit <project-dir> <chapter-id> [--title "..."] [--summary "..."]

# World commands (world facts: locations, cultures, history, rules, objects)
fabulae world add <project-dir> --id "fact-id" --type location|culture|history|rule|object [--facts "..."] ...
fabulae world suggest <project-dir> [--type location] [--idea "..."] [--yes] [--model MODEL] [--temperature TEMP]
fabulae world list <project-dir> [--type location|culture|...] [--format table|json|yaml]
fabulae world remove <project-dir> <fact-id>
fabulae world edit <project-dir> <fact-id> [--facts "..."] ...
```

### The `--idea` Parameter

All `suggest` commands accept an optional `--idea` parameter to guide the LLM:
- Can be literal text: `--idea "a mysterious stranger with a hidden past"`
- Can be a file path: `--idea notes/character-ideas.txt` (auto-detected if file exists)
- If omitted, the LLM suggests based solely on project context

### The `--yes` Flag

All `suggest` commands support a `--yes` / `-y` flag to automatically accept the suggestion:
- Without `--yes`: Display suggestion and prompt for confirmation before adding
- With `--yes`: Automatically add the suggested entity without prompting

```bash
# Interactive (prompts for confirmation)
fabulae character suggest ./my-novel --idea "a sidekick"

# Auto-accept (no confirmation prompt)
fabulae character suggest ./my-novel --idea "a sidekick" --yes
```

## Implementation Steps

### Step 1: Set Up Command Architecture with Typer App Groups
**Model: Haiku**

Use Typer app groups for cleaner code organization and better `--help` output. This is the required architecture pattern:

```python
# Each entity gets its own Typer app
character_app = typer.Typer(help="Manage characters in a Fabulae project")

@character_app.command("add")
def character_add(...): ...

@character_app.command("suggest")
def character_suggest(...): ...

# Main app wires them
app.add_typer(character_app, name="character")
```

This produces commands like:
- `fabulae character add ...`
- `fabulae character suggest ...`
- `fabulae character list ...`

**Files to create:**
- `src/fabulae/features/entities/__init__.py` - package init, exports all apps
- One module per entity type (see Step 2)

**Acceptance criteria:**
- All entity commands use Typer app groups
- `fabulae character --help` shows all character subcommands
- Consistent pattern across all entity types

### Step 2: Create Entity Command Modules
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create dedicated modules for each entity type in the feature slice. These modules should own the Typer apps and CLI command functions; `main.py` only wires them.

**`src/fabulae/features/entities/__init__.py`**
```python
# Package init
```

**`src/fabulae/features/entities/character.py`**
```python
import typer
from fabulae.models import Character, Project, load_project, save_project

character_app = typer.Typer(help="Manage characters in a Fabulae project")

@character_app.command("add")
def add(...): ...

@character_app.command("suggest")
def suggest(...): ...

# etc.
```

**`src/fabulae/features/entities/beat.py`**
```python
import typer
from fabulae.models import Beat, Scene, Project, load_project, save_project

beat_app = typer.Typer(help="Manage beats in a Fabulae project")

# etc.
```

### Step 3: Implement Character Commands
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

#### `character add`
```python
@character_app.command("add")
def add(
    project_dir: Path,
    id: Annotated[str, typer.Option("--id", help="Character ID (lowercase-with-hyphens)")],
    name: Annotated[str, typer.Option("--name", help="Character name")],
    role: Annotated[str | None, typer.Option("--role")] = None,
    desire: Annotated[str | None, typer.Option("--desire")] = None,
    need: Annotated[str | None, typer.Option("--need")] = None,
    flaw: Annotated[str | None, typer.Option("--flaw")] = None,
    secret: Annotated[str | None, typer.Option("--secret")] = None,
    traits: Annotated[list[str] | None, typer.Option("--trait")] = None,
) -> None:
    """Add a new character to the project."""
    project = load_project(project_dir)
    character = Character(id=id, name=name, role=role, ...)
    project.characters.append(character)
    save_project(project, project_dir)
    typer.echo(f"Added character: {name} ({id})")
```

#### `character suggest`
**Model: Sonnet** (implementation, OpenAI alternative: `gpt-5.1-codex-max`), **Opus** (prompt design, OpenAI alternative: `gpt-5.2-codex`)

```python
@character_app.command("suggest")
def suggest(
    project_dir: Path,
    idea: Annotated[str | None, typer.Option("--idea", "-i", help="Guidance text or file path")] = None,
    model: str = model_option(),
    temperature: float = temperature_option(),
    yes: bool = typer.Option(False, "--yes", "-y", help="Add without confirmation"),
) -> None:
    """Suggest a new character based on project context."""
    project = load_project(project_dir)

    # Resolve idea: if file path exists, read contents; otherwise use as literal text
    guidance = resolve_idea_input(idea) if idea else None

    # Call LLM with project context + optional guidance
    # Present suggestion to user
    # Add if user confirms (or --yes flag)
```

The suggest command should:
1. Load project and format context (existing characters, plot, world)
2. Resolve `--idea` input (file path vs. literal text)
3. Call LLM to suggest a character, incorporating guidance if provided
4. Validate suggestion language with the shared language guard and retry on mismatch
4. Display the suggestion clearly
5. Ask user to confirm before adding (or use `--yes` flag)

Add structured output models for suggestions (one per entity type). Example:
```python
from pydantic import BaseModel

class CharacterSuggestion(BaseModel):
    id: str
    name: str
    role: str | None = None
    desire: str | None = None
    need: str | None = None
    flaw: str | None = None
    secret: str | None = None
    traits: list[str] = []
```

Structured output usage:
```python
agent = create_agent(CharacterSuggestion, prompt, config)
suggestion = (await agent.run()).data
```

#### `character list`
```python
@character_app.command("list")
def list_characters(
    project_dir: Path,
    format: Annotated[str, typer.Option("--format", "-f")] = "table",
) -> None:
    """List all characters in the project."""
    project = load_project(project_dir)
    if format == "table":
        # Use rich.table for nice output
    elif format == "json":
        # JSON output
    elif format == "yaml":
        # YAML output
```

#### `character remove`
```python
@character_app.command("remove")
def remove(
    project_dir: Path,
    character_id: str,
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
) -> None:
    """Remove a character from the project."""
    project = load_project(project_dir)
    # Find character
    # Warn if character is referenced in scenes
    # Confirm removal (unless --force)
    # Remove and save
```

#### `character edit`
```python
@character_app.command("edit")
def edit(
    project_dir: Path,
    character_id: str,
    name: Annotated[str | None, typer.Option("--name")] = None,
    role: Annotated[str | None, typer.Option("--role")] = None,
    # ... other optional fields
) -> None:
    """Edit an existing character."""
    project = load_project(project_dir)
    # Find character by ID
    # Update only provided fields
    # Validate and save
```

### Step 4: Implement Beat Commands
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Similar structure to character commands, with additional complexity:

#### `beat add`
- Requires `--scene` to know where to add the beat
- Validates scene exists
- Appends beat to scene's beat list

#### `beat suggest`
- Requires `--scene` context
- Accepts optional `--idea` for guidance
- LLM suggests beat based on scene's characters, location, plot pattern, existing beats

#### `beat list`
- Optional `--scene` filter
- Shows scene ID in output

#### `beat move`
- Special command to relocate beats between scenes
- Validates target scene exists
- Optional `--position` for ordering within scene

#### `beat remove`
- Finds beat across all scenes
- Removes from parent scene

#### `beat edit`
- Locates beat by ID
- Updates specified fields

### Step 5: Implement Scene Commands
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/entities/scene.py`:

#### `scene add`
- Optional `--chapter` to assign scene to a chapter
- Optional `--location` referencing a world fact
- Creates scene with empty beats list

#### `scene suggest`
- Accepts optional `--chapter` for context
- Accepts optional `--idea` for guidance
- LLM suggests scene based on chapter context, existing scenes, plot arc

#### `scene move`
- Relocates scene between chapters
- Updates chapter's `scene_ids` accordingly

#### `scene remove`
- Removes scene from chapter's `scene_ids`
- Warns about beats that will be deleted

### Step 6: Implement Chapter Commands
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/entities/chapter.py`:

#### `chapter add`
- Creates chapter with empty `scene_ids`
- Optional `--title` and `--summary`

#### `chapter suggest`
- Accepts optional `--idea` for guidance
- LLM suggests chapter based on existing chapters, overall plot arc

#### `chapter remove`
- Warns if chapter contains scenes
- Requires `--force` to delete chapter with scenes (orphans the scenes)

### Step 7: Implement World Commands
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/entities/world.py`:

#### `world add`
- Requires `--type` (location, culture, history, rule, object)
- Creates world fact with specified type

#### `world suggest`
- Optional `--type` to constrain suggestion
- Accepts optional `--idea` for guidance
- LLM suggests world fact based on existing world, setting, story needs

#### `world list`
- Optional `--type` filter to show only locations, etc.

#### `world remove`
- Warns if world fact is referenced in scenes (as location or world_fact_id)

### Step 8: Wire Commands to Main App
**Model: Haiku** (OpenAI alternative: `gpt-5.1-codex-mini`)

Update `src/fabulae/main.py` (CLI wiring only; logic lives in feature modules):

```python
from fabulae.features.entities.character import character_app
from fabulae.features.entities.beat import beat_app
from fabulae.features.entities.scene import scene_app
from fabulae.features.entities.chapter import chapter_app
from fabulae.features.entities.world import world_app

app.add_typer(character_app, name="character")
app.add_typer(beat_app, name="beat")
app.add_typer(scene_app, name="scene")
app.add_typer(chapter_app, name="chapter")
app.add_typer(world_app, name="world")
```

### Step 9: Design Suggest Prompts
**Model: Opus** (OpenAI alternative: `gpt-5.2-codex`)

Create prompts for LLM-powered suggestions in `src/fabulae/features/entities/prompts.py`
(using shared helpers from `src/fabulae/prompts/`):

#### 10.1 Utility Functions

First, create shared utilities in `src/fabulae/features/entities/utils.py`:

```python
from pathlib import Path

def resolve_idea_input(idea: str) -> str:
    """
    Resolve --idea parameter: if it's a file path that exists, read its contents.
    Otherwise, return the string as-is.
    """
    path = Path(idea)
    if path.exists() and path.is_file():
        return path.read_text().strip()
    return idea

def format_existing_characters(characters: list[Character]) -> str:
    """Format existing characters for prompt context."""
    if not characters:
        return "No existing characters."
    lines = []
    for c in characters:
        line = f"- {c.name} ({c.id}): {c.role}"
        if c.desire:
            line += f" - wants: {c.desire}"
        lines.append(line)
    return "\n".join(lines)

def format_existing_scenes(scenes: list[Scene]) -> str:
    """Format existing scenes for prompt context."""
    if not scenes:
        return "No existing scenes."
    return "\n".join([f"- {s.id}: {s.title or s.summary[:50]}" for s in scenes])
```

#### 10.2 Character Suggestion Prompt

```python
def build_character_suggest_prompt(
    project: Project,
    guidance: str | None = None,
) -> str:
    """Build prompt for character suggestion."""
    existing = format_existing_characters(project.characters)
    premise = project.plot.premise if project.plot else "Not specified"

    guidance_section = ""
    if guidance:
        guidance_section = f"""
USER GUIDANCE:
{guidance}

Use this guidance to shape the character, but ensure they fit the story.
"""

    return f"""
You are helping create a character for a story.

STORY PREMISE:
{premise}

EXISTING CHARACTERS (do not duplicate these):
{existing}

{guidance_section}

Create a NEW character that:
1. Fills a gap in the current cast (missing archetype, needed role)
2. Has potential for interesting interactions with existing characters
3. Serves the story's needs based on the premise

Generate a character with these fields:
- id: A unique lowercase-with-hyphens identifier (e.g., "detective-chen")
- name: Full character name
- role: One of "protagonist", "antagonist", or "supporting"
- desire: What they consciously want (1 sentence)
- need: What they actually need for growth (1 sentence)
- flaw: Their key weakness (1-3 words)
- secret: Something hidden about them (1 sentence, optional)
- traits: 2-4 personality traits as a list

Output valid JSON matching this schema.
"""

#### 10.3 Beat Suggestion Prompt

```python
def build_beat_suggest_prompt(
    scene: Scene,
    project: Project,
    guidance: str | None = None,
) -> str:
    """Build prompt for beat suggestion within a scene."""
    existing_beats = "\n".join([
        f"- {b.id}: [{b.kind}] {b.summary}"
        for b in (scene.beats or [])
    ]) or "No beats yet."

    scene_characters = [
        c for c in project.characters
        if c.id in (scene.characters or [])
    ]
    char_context = format_existing_characters(scene_characters)

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""
You are helping add a beat to a scene.

SCENE: {scene.title or scene.id}
Summary: {scene.summary or "Not specified"}

CHARACTERS IN SCENE:
{char_context}

EXISTING BEATS IN THIS SCENE:
{existing_beats}
{guidance_section}

Create a NEW beat that:
1. Advances the scene's narrative
2. Involves the characters present
3. Doesn't duplicate existing beats

Generate a beat with these fields:
- id: Unique lowercase-with-hyphens (e.g., "beat-confrontation")
- kind: One of "action", "dialogue", "revelation", "decision", "transition"
- summary: 1-2 sentences describing what happens
- characters: List of character IDs involved (must be from scene's characters)
- emotional_beat: Optional emotional arc moment

Output valid JSON matching this schema.
"""

#### 10.4 Scene Suggestion Prompt

```python
def build_scene_suggest_prompt(
    project: Project,
    chapter_id: str | None = None,
    guidance: str | None = None,
) -> str:
    """Build prompt for scene suggestion."""
    existing = format_existing_scenes(project.plot.scenes or [])
    characters = format_existing_characters(project.characters)

    chapter_context = ""
    if chapter_id and project.plot.chapters:
        chapter = next((c for c in project.plot.chapters if c.id == chapter_id), None)
        if chapter:
            chapter_context = f"""
TARGET CHAPTER: {chapter.title or chapter.id}
Summary: {chapter.summary or "Not specified"}
"""

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""
You are helping add a scene to a story.

PREMISE: {project.plot.premise if project.plot else "Not specified"}
{chapter_context}

EXISTING SCENES:
{existing}

AVAILABLE CHARACTERS:
{characters}
{guidance_section}

Create a NEW scene that:
1. Advances the plot or develops characters
2. Doesn't duplicate existing scenes
3. Uses available characters meaningfully

Generate a scene with these fields:
- id: Unique lowercase-with-hyphens (e.g., "scene-confrontation")
- title: Short evocative title
- summary: 2-3 sentences describing what happens
- characters: List of character IDs who appear
- location: Optional location ID from world facts
- time: Optional time indicator

Output valid JSON matching this schema. Do NOT include beats - those are added separately.
"""

#### 10.5 World Fact Suggestion Prompt

```python
def build_world_suggest_prompt(
    project: Project,
    fact_type: str | None = None,
    guidance: str | None = None,
) -> str:
    """Build prompt for world fact suggestion."""
    existing_facts = "\n".join([
        f"- {f.id} [{f.type}]: {', '.join(f.facts[:2])}"
        for f in (project.world.facts if project.world else [])
    ]) or "No world facts defined."

    type_constraint = ""
    if fact_type:
        type_constraint = f"\nREQUIRED TYPE: {fact_type}\nGenerate only a {fact_type} world fact."

    guidance_section = f"\nUSER GUIDANCE: {guidance}\n" if guidance else ""

    return f"""
You are helping build the world for a story.

PREMISE: {project.plot.premise if project.plot else "Not specified"}

EXISTING WORLD FACTS:
{existing_facts}
{type_constraint}
{guidance_section}

Create a NEW world fact that:
1. Enriches the story's setting
2. Could be referenced in scenes
3. Doesn't contradict existing facts

Generate a world fact with these fields:
- id: Unique lowercase-with-hyphens (e.g., "location-tavern" or "culture-elven")
- type: One of "location", "culture", "history", "rule", "object"
- facts: List of 2-4 specific details about this world element

Output valid JSON matching this schema.
"""

### Step 10: Add Confirmation Flows
**Model: Haiku** (OpenAI alternative: `gpt-5.1-codex-mini`)

For destructive operations and suggestions:

```python
def confirm(message: str, default: bool = False) -> bool:
    """Prompt user for confirmation."""
    return typer.confirm(message, default=default)
```

Use for:
- `remove` commands: require confirmation unless `--force` flag is passed
- `suggest` commands: require confirmation unless `--yes` flag is passed

### Step 11: Write Tests
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `tests/unit/features/entities/`:

**`tests/unit/features/entities/character_test.py`**
- Test add with various options
- Test list with different formats
- Test remove with and without --force
- Test edit with partial updates
- Test suggest with mocked LLM
- Test suggest with --idea (text and file path)

**`tests/unit/features/entities/beat_test.py`**
- Test add to scene
- Test move between scenes
- Test list with and without --scene filter
- Test remove finds beat in any scene
- Test suggest with mocked LLM and --idea

**`tests/unit/features/entities/scene_test.py`**
- Test add with and without --chapter
- Test move between chapters
- Test list with --chapter filter
- Test remove updates chapter's scene_ids
- Test suggest with --idea

**`tests/unit/features/entities/chapter_test.py`**
- Test add with title and summary
- Test list
- Test remove with and without scenes
- Test suggest with --idea

**`tests/unit/features/entities/world_test.py`**
- Test add with different types
- Test list with --type filter
- Test remove warns about references
- Test suggest with --type and --idea

### Step 12: Add Help Text and Examples
**Model: Haiku** (OpenAI alternative: `gpt-5.1-codex-mini`)

Ensure all commands have clear help text:

```python
@character_app.command("add")
def add(
    ...
) -> None:
    """
    Add a new character to the project.

    Example:
        fabulae character add ./my-novel --id "detective-jane" --name "Jane Doe" --role protagonist
    """
```

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
   - Test each entity command manually

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Review and update `AGENTS.md` if project structure, testing guidelines, or commit conventions changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/entities/__init__.py` | Create | Package init |
| `src/fabulae/features/entities/character.py` | Create | Character CRUD commands |
| `src/fabulae/features/entities/beat.py` | Create | Beat CRUD commands |
| `src/fabulae/features/entities/scene.py` | Create | Scene CRUD commands |
| `src/fabulae/features/entities/chapter.py` | Create | Chapter CRUD commands |
| `src/fabulae/features/entities/world.py` | Create | World fact CRUD commands |
| `src/fabulae/features/entities/utils.py` | Create | Shared utilities (resolve_idea_input, confirm, etc.) |
| `src/fabulae/main.py` | Modify | Wire up command groups |
| `src/fabulae/features/entities/prompts.py` | Create | Suggest prompts for all entities |
| `tests/unit/features/entities/__init__.py` | Create | Test package init |
| `tests/unit/features/entities/character_test.py` | Create | Character command tests |
| `tests/unit/features/entities/beat_test.py` | Create | Beat command tests |
| `tests/unit/features/entities/scene_test.py` | Create | Scene command tests |
| `tests/unit/features/entities/chapter_test.py` | Create | Chapter command tests |
| `tests/unit/features/entities/world_test.py` | Create | World command tests |

## Acceptance Criteria

- [ ] `fabulae character add|suggest|list|remove|edit` all work
- [ ] `fabulae beat add|suggest|list|move|remove|edit` all work
- [ ] `fabulae scene add|suggest|list|move|remove|edit` all work
- [ ] `fabulae chapter add|suggest|list|remove|edit` all work
- [ ] `fabulae world add|suggest|list|remove|edit` all work
- [ ] All `suggest` commands support optional `--idea` parameter
- [ ] `--idea` accepts both literal text and file paths (auto-detected)
- [ ] All `suggest` commands support `--yes` flag to auto-accept
- [ ] `suggest` commands use LLM with project context + optional guidance
- [ ] `--model` and `--temperature` work on suggest commands
- [ ] `list` supports table, json, yaml formats
- [ ] Destructive operations require confirmation (or --force)
- [ ] Clear error messages for invalid IDs, missing entities
- [ ] All modified projects pass validation
- [ ] All tests pass
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Example Session

```bash
# List existing characters
$ fabulae character list ./my-novel
┌──────────────┬───────────────┬─────────────┐
│ ID           │ Name          │ Role        │
├──────────────┼───────────────┼─────────────┤
│ vera         │ Vera Mellifer │ protagonist │
│ marcus       │ Marcus Stone  │ antagonist  │
└──────────────┴───────────────┴─────────────┘

# Add a new character
$ fabulae character add ./my-novel --id "inspector-chen" --name "Inspector Chen" --role supporting

# Get LLM suggestion (no guidance)
$ fabulae character suggest ./my-novel --temperature 0.9
Suggested character:
  ID: dr-patil
  Name: Dr. Ananya Patil
  Role: supporting
  Desire: To prove her research is legitimate
  Flaw: Overly trusting of colleagues

Add this character? [y/N]: y
Added character: Dr. Ananya Patil (dr-patil)

# Get LLM suggestion with guidance text
$ fabulae character suggest ./my-novel --idea "a rival detective with a grudge"
Suggested character:
  ID: detective-morris
  Name: Frank Morris
  Role: antagonist
  Desire: To prove himself better than Vera
  Flaw: Lets ego cloud judgment

Add this character? [y/N]: n

# Get LLM suggestion with guidance from file
$ fabulae character suggest ./my-novel --idea notes/villain-ideas.txt

# Add a beat to a scene
$ fabulae beat add ./my-novel --scene "scene-discovery" --id "beat-03" --kind action --summary "Vera examines the evidence"

# Suggest a beat with guidance
$ fabulae beat suggest ./my-novel --scene "scene-discovery" --idea "escalate tension"

# Move beat to different scene
$ fabulae beat move ./my-novel beat-03 --to-scene "scene-investigation" --position 0

# Add a world fact
$ fabulae world add ./my-novel --id "synesthesia-lab" --type location

# Suggest a location
$ fabulae world suggest ./my-novel --type location --idea "somewhere the victim was last seen"

# List scenes in a chapter
$ fabulae scene list ./my-novel --chapter chapter-01

# Suggest a new scene
$ fabulae scene suggest ./my-novel --chapter chapter-02 --idea "confrontation between Vera and Marcus"
```
