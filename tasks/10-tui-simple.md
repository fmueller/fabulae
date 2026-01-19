# Task: Simple TUI for v0.1.0 Release

**Priority:** High - primary interactive interface for the v0.1.0 release.
**Depends on:** `05-entity-crud-commands.md`, `08-build-command.md`

## Overview

Implement a minimal Terminal User Interface (TUI) for the Fabulae v0.1.0 release. This TUI provides an interactive workflow for the core Fabulae experience:

1. **Create** - Generate a new project from an idea
2. **View** - Browse the generated project structure
3. **Edit** - Perform CRUD actions on entities
4. **Build** - Generate the final narrative output

The TUI should be simple and focused, using Textual (already in dependencies). It calls the same feature slice services used by the CLI (`src/fabulae/features/*`) rather than duplicating logic.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Entry Point Behavior

```bash
# Launch TUI in current directory (if valid project exists)
fabulae

# Launch TUI for specific project
fabulae /path/to/project

# Explicit TUI command
fabulae tui /path/to/project

# Create mode - start with project creation
fabulae tui --new
```

**Behavior:**
- If directory contains a valid Fabulae project, open it in view mode
- If `--new` is passed, start in create mode (idea input)
- If directory is empty or doesn't exist, prompt for create or exit

## Core Workflow Screens

### Screen 1: Welcome / Create

When no project exists or `--new` is passed:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Fabulae v0.1.0                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Welcome to Fabulae!                                                        │
│                                                                             │
│  Enter your story idea:                                                     │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ A detective with synesthesia investigates murders where the crime    │  │
│  │ scenes are arranged like musical compositions...                     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  Format: [novel ▾]     Shape: [mystery-reveal ▾]                           │
│                                                                             │
│  [Create Project]  [Cancel]                                                │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Screen 2: Project View (Main Screen)

After creating or opening a project:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fabulae - The Synesthesia Murders                              [novel] 0.1 │
├────────────────────┬────────────────────────────────────────────────────────┤
│ Project            │                                                        │
│ ├── Characters (3) │  Character: Vera Mellifer                              │
│ │   ├── vera      ◄│  ──────────────────────────────────────────────        │
│ │   ├── marcus     │  Role: protagonist                                     │
│ │   └── chen       │  Desire: To uncover the truth behind the murder        │
│ ├── World (8)      │  Need: To reconnect with her own emotions              │
│ │   ├── locations  │  Flaw: Emotionally guarded                             │
│ │   └── facts      │                                                        │
│ ├── Plot           │  Traits:                                               │
│ │   ├── Chapter 1  │    • Analytical                                        │
│ │   │   └── 2 scenes│   • Observant                                         │
│ │   └── Chapter 2  │                                                        │
│ │       └── 3 scenes│                                                       │
│ └── Style          │                                                        │
├────────────────────┴────────────────────────────────────────────────────────┤
│ [a]dd  [e]dit  [d]elete  [b]uild  [q]uit                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Screen 3: Build Progress / Output

When building:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fabulae - Building...                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Building The Synesthesia Murders                                           │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 60%                    │
│                                                                             │
│  ✓ Chapter 1: The Discovery (3 scenes)                                     │
│  → Chapter 2: The Investigation (scene 2/5)                                │
│  ○ Chapter 3: The Revelation                                               │
│                                                                             │
│  [Cancel]                                                                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

After build completes:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fabulae - Build Complete                                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ✓ Build Complete!                                                         │
│                                                                             │
│  Output: ./output/2024-01-15_143052/                                       │
│  Words: 12,453                                                              │
│  Time: 2m 34s                                                               │
│                                                                             │
│  [View Output]  [Back to Project]                                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Create Basic App Structure
**Model: Sonnet**

Create the TUI feature slice structure:

```
src/fabulae/features/tui/
├── __init__.py
├── cli.py              # CLI entry point
├── app.py              # Main Textual app
├── screens/
│   ├── __init__.py
│   ├── welcome.py      # Create screen
│   ├── project.py      # Main project view
│   └── build.py        # Build progress/results
├── widgets/
│   ├── __init__.py
│   ├── project_tree.py # Sidebar tree
│   └── entity_view.py  # Entity detail panel
└── styles.tcss         # Textual CSS
```

**Files to create:**
- All files in the structure above

**Acceptance criteria:**
- App launches without errors
- Basic layout renders

### Step 2: Implement Welcome/Create Screen
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/welcome.py`:

```python
from textual.screen import Screen
from textual.widgets import Input, Select, Button, Static
from textual.containers import Vertical, Horizontal

class WelcomeScreen(Screen):
    """Welcome screen for creating new projects."""

    def compose(self) -> ComposeResult:
        yield Static("Fabulae v0.1.0", id="title")
        yield Static("Enter your story idea:")
        yield Input(placeholder="A detective investigates...", id="idea")
        with Horizontal():
            yield Select(
                [(f, f) for f in ["novel", "novella", "short-story", "micro-prose", "poem"]],
                value="novel",
                id="format",
            )
            yield Select(
                [(s.id, s.name) for s in load_shapes()],
                value="heros-journey",
                id="shape",
            )
        with Horizontal():
            yield Button("Create Project", variant="primary", id="create")
            yield Button("Cancel", id="cancel")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            idea = self.query_one("#idea", Input).value
            format_ = self.query_one("#format", Select).value
            shape = self.query_one("#shape", Select).value
            # Call create service
            await self.run_create(idea, format_, shape)
```

**Acceptance criteria:**
- Form captures idea, format, shape
- Create button triggers project generation
- Progress indicator during creation

### Step 3: Implement Project View Screen
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/project.py`:

```python
from textual.screen import Screen
from textual.widgets import Header, Footer
from textual.containers import Horizontal

class ProjectScreen(Screen):
    """Main project viewing and editing screen."""

    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("b", "build", "Build"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path
        self.project = load_project(project_path)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ProjectTree(self.project, id="sidebar")
            yield EntityView(id="content")
        yield Footer()
```

**Acceptance criteria:**
- Tree shows all entity categories
- Selecting entity shows details
- Keyboard shortcuts work

### Step 4: Implement Project Tree Widget
**Model: Sonnet**

Create `src/fabulae/features/tui/widgets/project_tree.py`:

```python
from textual.widgets import Tree

class ProjectTree(Tree):
    """Tree view of project structure."""

    def __init__(self, project: Project, **kwargs):
        super().__init__("Project", **kwargs)
        self.project = project
        self._build_tree()

    def _build_tree(self) -> None:
        # Characters
        chars = self.root.add(f"Characters ({len(self.project.characters)})")
        for char in self.project.characters:
            chars.add_leaf(char.name, data=("character", char.id))

        # World facts
        if self.project.world:
            world = self.root.add(f"World ({len(self.project.world.facts)})")
            # Group by type
            locations = [f for f in self.project.world.facts if f.type == "location"]
            if locations:
                loc_node = world.add("Locations")
                for loc in locations:
                    loc_node.add_leaf(loc.id, data=("world_fact", loc.id))
            # Other facts...

        # Plot structure (format-dependent)
        plot = self.root.add("Plot")
        if self.project.plot.chapters:
            for chapter in self.project.plot.chapters:
                ch_node = plot.add(chapter.title or chapter.id)
                ch_node.add_leaf(f"{len(chapter.scene_ids)} scenes")
        elif self.project.plot.scenes:
            for scene in self.project.plot.scenes:
                plot.add_leaf(scene.id, data=("scene", scene.id))
        elif self.project.plot.fragments:
            for frag in self.project.plot.fragments:
                plot.add_leaf(frag.id, data=("fragment", frag.id))
        elif self.project.plot.stanzas:
            for stanza in self.project.plot.stanzas:
                plot.add_leaf(stanza.id, data=("stanza", stanza.id))

        # Style
        self.root.add_leaf("Style", data=("style", None))
```

**Acceptance criteria:**
- Tree reflects project structure
- Format-appropriate entities shown
- Selection events propagate

### Step 5: Implement Entity View Widget
**Model: Sonnet**

Create `src/fabulae/features/tui/widgets/entity_view.py`:

```python
from textual.widgets import Static, Markdown

class EntityView(Static):
    """Displays formatted details of selected entity."""

    def show_character(self, char: Character) -> None:
        content = f"""
## {char.name}

**Role:** {char.role or "—"}

**Desire:** {char.desire or "—"}

**Need:** {char.need or "—"}

**Flaw:** {char.flaw or "—"}

**Traits:** {", ".join(char.traits) if char.traits else "—"}
"""
        self.update(Markdown(content))

    def show_scene(self, scene: Scene) -> None:
        beats_text = "\n".join(f"- {b.summary}" for b in (scene.beats or []))
        content = f"""
## {scene.title or scene.id}

**Summary:** {scene.summary or "—"}

**Characters:** {", ".join(scene.characters) if scene.characters else "—"}

**Location:** {scene.location or "—"}

**Beats:**
{beats_text or "No beats defined"}
"""
        self.update(Markdown(content))

    # Similar methods for other entity types...
```

**Acceptance criteria:**
- All entity types render nicely
- Markdown formatting works
- Empty fields shown as "—"

### Step 6: Implement CRUD Actions
**Model: Sonnet**

Add action handlers to ProjectScreen:

```python
async def action_add(self) -> None:
    """Add a new entity based on current selection."""
    # Determine entity type from selection
    tree = self.query_one(ProjectTree)
    node = tree.cursor_node
    entity_type = self._get_entity_type_from_node(node)

    # Push appropriate add modal
    if entity_type == "character":
        result = await self.app.push_screen(AddCharacterModal())
        if result:
            self.project.characters.append(result)
            save_project(self.project, self.project_path)
            self._refresh_tree()

async def action_edit(self) -> None:
    """Edit the selected entity."""
    tree = self.query_one(ProjectTree)
    if tree.cursor_node and tree.cursor_node.data:
        entity_type, entity_id = tree.cursor_node.data
        entity = self._get_entity(entity_type, entity_id)
        if entity:
            result = await self.app.push_screen(EditModal(entity_type, entity))
            if result:
                self._update_entity(entity_type, entity_id, result)
                save_project(self.project, self.project_path)
                self._refresh_tree()

async def action_delete(self) -> None:
    """Delete the selected entity."""
    tree = self.query_one(ProjectTree)
    if tree.cursor_node and tree.cursor_node.data:
        entity_type, entity_id = tree.cursor_node.data
        # Show confirmation
        if await self.app.push_screen(ConfirmDeleteModal(entity_type, entity_id)):
            self._delete_entity(entity_type, entity_id)
            save_project(self.project, self.project_path)
            self._refresh_tree()
```

**Acceptance criteria:**
- Add creates new entities via CLI service
- Edit updates existing entities
- Delete removes with confirmation
- Tree refreshes after changes

### Step 7: Implement Build Screen
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/build.py`:

```python
from textual.screen import Screen
from textual.widgets import ProgressBar, Static, Button

class BuildScreen(Screen):
    """Build progress and results screen."""

    def __init__(self, project: Project, project_path: Path):
        super().__init__()
        self.project = project
        self.project_path = project_path

    def compose(self) -> ComposeResult:
        yield Static(f"Building {self.project.config.name or 'Project'}...", id="title")
        yield ProgressBar(total=100, id="progress")
        yield Static("", id="status")
        yield Button("Cancel", id="cancel")

    async def on_mount(self) -> None:
        # Run build in background
        self.run_worker(self._run_build())

    async def _run_build(self) -> None:
        from fabulae.features.build.service import build_project
        from fabulae.llm import resolve_config

        config = resolve_config(None, None, None, None)

        # Note: For simple TUI, we run build without detailed progress
        # Future enhancement: add progress callback to build_project
        result = await build_project(self.project, config, seed=None)

        # Show completion
        self.query_one("#progress", ProgressBar).update(progress=100)
        self.query_one("#status", Static).update(
            f"✓ Complete! {result.total_word_count} words"
        )
```

**Acceptance criteria:**
- Build runs asynchronously
- Progress updates shown
- Results displayed on completion
- Cancel button works

### Step 8: Wire CLI Entry Point
**Model: Sonnet**

Create `src/fabulae/features/tui/cli.py`:

```python
import typer
from pathlib import Path
from typing import Annotated

def register_tui_commands(app: typer.Typer) -> None:
    @app.callback(invoke_without_command=True)
    def main_callback(
        ctx: typer.Context,
        path: Annotated[Path | None, typer.Argument(help="Project directory")] = None,
        new: Annotated[bool, typer.Option("--new", help="Start with project creation")] = False,
    ) -> None:
        """
        Fabulae - CLI toolkit for building narratives.

        When called without a command, launches the interactive TUI.
        """
        if ctx.invoked_subcommand is not None:
            return

        from fabulae.features.tui.app import FabulaeApp

        project_path = path or Path.cwd()

        # Check if valid project exists
        has_project = (project_path / "fabulae.yml").exists()

        app = FabulaeApp(project_path, start_create=new or not has_project)
        app.run()

    @app.command()
    def tui(
        path: Annotated[Path, typer.Argument(help="Project directory")] = Path("."),
        new: Annotated[bool, typer.Option("--new", help="Start with project creation")] = False,
    ) -> None:
        """Launch the interactive TUI."""
        from fabulae.features.tui.app import FabulaeApp

        has_project = (path / "fabulae.yml").exists()
        app = FabulaeApp(path, start_create=new or not has_project)
        app.run()
```

Update `src/fabulae/main.py` to register TUI commands.

**Acceptance criteria:**
- `fabulae` without args launches TUI
- `fabulae tui` explicit command works
- `--new` starts creation flow

### Step 9: Add Simple Modals
**Model: Haiku**

Create basic modals for CRUD operations:

**`src/fabulae/features/tui/modals/`**:
- `add_entity.py` - Simple form for adding entities
- `edit_entity.py` - Form for editing entity fields
- `confirm.py` - Confirmation dialog

Keep modals simple for v0.1.0 - basic input fields matching entity model fields.

**Acceptance criteria:**
- Modals open/close properly
- Form data captured correctly
- Cancel returns None

### Step 10: Add Styling
**Model: Haiku**

Create `src/fabulae/features/tui/styles.tcss`:

```css
/* Layout */
#sidebar {
    width: 30%;
    min-width: 25;
    border-right: solid $primary;
    padding: 1;
}

#content {
    width: 70%;
    padding: 1 2;
}

/* Welcome screen */
WelcomeScreen {
    align: center middle;
}

#title {
    text-align: center;
    text-style: bold;
    margin-bottom: 2;
}

/* Build screen */
BuildScreen ProgressBar {
    margin: 2 4;
}

/* Modals */
ModalScreen {
    align: center middle;
}

.modal-dialog {
    width: 60;
    height: auto;
    border: thick $primary;
    background: $surface;
    padding: 1 2;
}
```

**Acceptance criteria:**
- Consistent visual style
- Readable in various terminal sizes
- Proper spacing and borders

### Step 11: Write Tests
**Model: Sonnet**

Create `tests/unit/features/tui_test.py`:

1. Test app initialization
2. Test screen navigation
3. Test entity selection in tree
4. Test CRUD actions (with mocked project)
5. Use Textual's test framework

**Acceptance criteria:**
- Core functionality tested
- Tests don't require actual LLM
- `uv run pytest` passes

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - TUI calls feature services, no duplicated logic
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

4. **Manual Testing:**
   - Test the full workflow: create → view → edit → build
   - Test with different formats (novel, poem, micro-prose)
   - Test keyboard shortcuts
   - Test error handling (invalid project, LLM failures)

5. **Documentation Review:**
   - Update `README.md` with TUI usage section
   - Update `CLAUDE.md` with TUI feature architecture
   - Ensure version shown as 0.1.0

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/tui/__init__.py` | Create | Package init |
| `src/fabulae/features/tui/cli.py` | Create | CLI entry point |
| `src/fabulae/features/tui/app.py` | Create | Main Textual app |
| `src/fabulae/features/tui/screens/__init__.py` | Create | Screens package |
| `src/fabulae/features/tui/screens/welcome.py` | Create | Create screen |
| `src/fabulae/features/tui/screens/project.py` | Create | Main view screen |
| `src/fabulae/features/tui/screens/build.py` | Create | Build screen |
| `src/fabulae/features/tui/widgets/__init__.py` | Create | Widgets package |
| `src/fabulae/features/tui/widgets/project_tree.py` | Create | Tree widget |
| `src/fabulae/features/tui/widgets/entity_view.py` | Create | Detail view |
| `src/fabulae/features/tui/modals/__init__.py` | Create | Modals package |
| `src/fabulae/features/tui/modals/add_entity.py` | Create | Add modal |
| `src/fabulae/features/tui/modals/edit_entity.py` | Create | Edit modal |
| `src/fabulae/features/tui/modals/confirm.py` | Create | Confirm dialog |
| `src/fabulae/features/tui/styles.tcss` | Create | Textual CSS |
| `src/fabulae/main.py` | Modify | Add TUI entry point |
| `tests/unit/features/tui_test.py` | Create | TUI tests |
| `pyproject.toml` | Modify | Update version to 0.1.0 |

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit the TUI |
| `a` | Add | Add new entity |
| `e` | Edit | Edit selected entity |
| `d` | Delete | Delete selected entity |
| `b` | Build | Build project output |
| `↑/↓` | Navigate | Move through tree |
| `Enter` | Select | Select/expand tree node |
| `Esc` | Back | Close modal/cancel |

## Acceptance Criteria

- [ ] `fabulae` (no command) launches TUI
- [ ] Create workflow: idea → format → shape → generate
- [ ] Project tree displays entities by category
- [ ] Selecting entity shows formatted details
- [ ] Add/Edit/Delete actions work for all entity types
- [ ] Build action generates output with progress
- [ ] All formats work (novel, novella, short-story, micro-prose, poem)
- [ ] Keyboard shortcuts function correctly
- [ ] Error states handled gracefully
- [ ] All tests pass
- [ ] `ruff check`, `mypy`, and `pytest` pass
- [ ] Version displays as 0.1.0

## v0.1.0 Release Scope

This task represents the v0.1.0 release milestone. The release includes:

1. **Create command** - Generate projects from ideas (CLI + TUI)
2. **Entity CRUD** - Manage characters, scenes, beats, etc. (CLI + TUI)
3. **Build command** - Generate final narrative output (CLI + TUI)
4. **Simple TUI** - Interactive interface for the core workflow
5. **Project history** - Track command history
6. **Validation** - Structural validation of projects

Future releases will add more advanced features (check, doctor, advanced TUI).
