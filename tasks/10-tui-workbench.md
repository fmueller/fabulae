# Task: TUI Workbench

**Priority:** High - primary user interface for interactive work.
**Depends on:** All other features (TUI provides interface to them)

## Overview

Implement a Terminal User Interface (TUI) as the primary interactive workbench for Fabulae. When Fabulae is called without a command (or with `tui` command), it launches an interactive interface where users can browse, edit, and manage their narrative project.

The TUI is built with Textual (already in dependencies) and serves as a graphical wrapper around all CLI functionality. It should call the same feature slice services used by the CLI (e.g., `src/fabulae/features/*`) rather than duplicating logic.

All LLM interactions triggered from the TUI (suggest/check/build) must use structured output via the underlying feature services.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Entry Point Behavior

```bash
# Launch TUI in current directory
fabulae

# Launch TUI for specific project
fabulae /path/to/project

# Explicit TUI command
fabulae tui /path/to/project
```

**Validation on startup:**
- If directory is not a valid Fabulae project, exit immediately with error message
- Do not launch TUI for invalid projects

## TUI Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fabulae - The Synesthesia Murders                              [novel] 0.1 │
├────────────────────┬────────────────────────────────────────────────────────┤
│ Project            │                                                        │
│ ├── Characters     │  Character: Vera Mellifer                              │
│ │   ├── vera      ◄│  ──────────────────────────────────────────────        │
│ │   ├── marcus     │  Role: protagonist                                     │
│ │   └── chen       │  Desire: To uncover the truth behind the murder        │
│ ├── World          │  Need: To reconnect with her own emotions              │
│ │   ├── locations  │  Flaw: Emotionally guarded                             │
│ │   └── facts      │  Secret: She experiences synesthesia herself           │
│ ├── Plot           │                                                        │
│ │   ├── Chapter 1  │  Traits:                                               │
│ │   │   ├── scene1 │    • Analytical                                        │
│ │   │   └── scene2 │    • Observant                                         │
│ │   └── Chapter 2  │    • Methodical                                        │
│ │       └── ...    │                                                        │
│ ├── Style          │  Appears in scenes:                                    │
│ └── Patterns       │    • scene-discovery                                   │
│                    │    • scene-investigation                               │
├────────────────────┴────────────────────────────────────────────────────────┤
│ [e]dit  [a]dd  [d]elete  [s]uggest  [c]heck  [b]uild  [v]alidate  [q]uit   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Design TUI Architecture
**Model: Opus** (OpenAI alternative: `gpt-5.2-codex`)

Plan the component structure:

1. **Main App** (`FabulaeApp`): Root Textual application
2. **Sidebar** (`ProjectTree`): Tree view of project structure
3. **Content Panel** (`ContentView`): Displays selected entity details
4. **Action Bar** (`ActionBar`): Keyboard shortcuts and commands
5. **Modal Dialogs**: For editing, confirming deletes, etc.
6. **Screens**: For different major views (project, build output, settings)

Key design decisions:
- Reactive updates when project changes
- Undo/redo support (optional, future)
- Async operations for LLM calls with progress indicators
- Responsive layout for different terminal sizes

### Step 2: Create Base App Structure
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/tui/__init__.py` and `src/fabulae/tui/app.py`:

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Tree, Static
from textual.containers import Horizontal, Vertical

class FabulaeApp(App):
    """Fabulae TUI application."""

    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("e", "edit", "Edit"),
        ("a", "add", "Add"),
        ("d", "delete", "Delete"),
        ("s", "suggest", "Suggest"),
        ("c", "check", "Check"),
        ("b", "build", "Build"),
        ("v", "validate", "Validate"),
    ]

    def __init__(self, project_path: Path):
        super().__init__()
        self.project_path = project_path
        self.project: Project | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ProjectTree(id="sidebar")
            yield ContentView(id="content")
        yield Footer()

    async def on_mount(self) -> None:
        self.project = load_project(self.project_path)
        self.query_one(ProjectTree).load_project(self.project)
```

### Step 3: Implement Project Tree Widget
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/tui/widgets/project_tree.py`:

```python
from textual.widgets import Tree
from textual.widgets.tree import TreeNode

class ProjectTree(Tree):
    """Tree view of project structure."""

    def load_project(self, project: Project) -> None:
        self.clear()
        self.root.label = project.config.name or "Project"

        # Characters
        chars = self.root.add("Characters", expand=True)
        for char in project.characters:
            chars.add_leaf(char.name, data=("character", char.id))

        # World
        world = self.root.add("World", expand=True)
        locations = world.add("Locations")
        for fact in project.world.facts:
            if fact.type == "location":
                locations.add_leaf(fact.id, data=("world_fact", fact.id))
        # ... other world facts

        # Plot
        plot = self.root.add("Plot", expand=True)
        if project.plot.chapters:
            for chapter in project.plot.chapters:
                ch_node = plot.add(chapter.title or chapter.id)
                for scene_id in chapter.scene_ids:
                    scene = get_scene_by_id(scene_id, project)
                    ch_node.add_leaf(scene.id, data=("scene", scene.id))
        else:
            for scene in project.plot.scenes:
                plot.add_leaf(scene.id, data=("scene", scene.id))

        # Style
        self.root.add_leaf("Style", data=("style", None))

        # Patterns
        if project.plot_patterns:
            patterns = self.root.add("Patterns")
            for pattern in project.plot_patterns:
                patterns.add_leaf(pattern.id, data=("plot_pattern", pattern.id))

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        if event.node.data:
            entity_type, entity_id = event.node.data
            self.post_message(EntitySelected(entity_type, entity_id))
```

### Step 4: Implement Content View Widget
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/tui/widgets/content_view.py`:

```python
from textual.widgets import Static, Markdown
from textual.reactive import reactive

class ContentView(Static):
    """Displays details of selected entity."""

    entity_type: reactive[str | None] = reactive(None)
    entity_id: reactive[str | None] = reactive(None)

    def render_character(self, character: Character) -> str:
        return f"""
# {character.name}

**Role:** {character.role or 'Not specified'}

**Desire:** {character.desire or 'Not specified'}

**Need:** {character.need or 'Not specified'}

**Flaw:** {character.flaw or 'Not specified'}

**Secret:** {character.secret or 'Not specified'}

**Traits:**
{self._format_list(character.traits)}
        """.strip()

    def render_scene(self, scene: Scene) -> str:
        # Format scene details including beats
        ...

    def render_world_fact(self, fact: WorldFact) -> str:
        # Format world fact
        ...

    def watch_entity_id(self, entity_id: str | None) -> None:
        if entity_id is None:
            self.update("")
            return

        # Fetch and render entity
        project = self.app.project
        if self.entity_type == "character":
            char = get_character_by_id(entity_id, project)
            self.update(Markdown(self.render_character(char)))
        # ... other types
```

### Step 5: Implement Entity Renderers
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create nicely formatted views for each entity type:

**`src/fabulae/tui/renderers/character_renderer.py`**
**`src/fabulae/tui/renderers/scene_renderer.py`**
**`src/fabulae/tui/renderers/world_fact_renderer.py`**
**`src/fabulae/tui/renderers/style_renderer.py`**

Each renderer converts the Pydantic model to rich Markdown for display.

### Step 6: Implement Edit Modals
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create modal dialogs for editing entities:

**`src/fabulae/tui/modals/edit_character.py`**

```python
from textual.screen import ModalScreen
from textual.widgets import Input, Select, Button
from textual.containers import Vertical, Horizontal

class EditCharacterModal(ModalScreen):
    """Modal for editing a character."""

    def __init__(self, character: Character):
        super().__init__()
        self.character = character

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Static("Edit Character", id="title")
            yield Input(value=self.character.name, placeholder="Name", id="name")
            yield Select(
                [(r, r) for r in ["protagonist", "antagonist", "supporting"]],
                value=self.character.role,
                id="role"
            )
            yield Input(value=self.character.desire or "", placeholder="Desire", id="desire")
            # ... other fields
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            # Update character and save project
            self.character.name = self.query_one("#name", Input).value
            # ... update other fields
            save_project(self.app.project, self.app.project_path)
            self.dismiss(self.character)
        else:
            self.dismiss(None)
```

### Step 7: Implement Command Actions
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Wire up keyboard shortcuts to actions (call feature services instead of re-implementing logic):

```python
# In FabulaeApp

async def action_edit(self) -> None:
    """Edit the currently selected entity."""
    tree = self.query_one(ProjectTree)
    selected = tree.cursor_node
    if selected and selected.data:
        entity_type, entity_id = selected.data
        if entity_type == "character":
            char = get_character_by_id(entity_id, self.project)
            result = await self.push_screen(EditCharacterModal(char))
            if result:
                self.query_one(ContentView).refresh()
        # ... other entity types

async def action_add(self) -> None:
    """Add a new entity based on current context."""
    # Determine what type to add based on selection
    # Show appropriate add modal
    ...

async def action_delete(self) -> None:
    """Delete the currently selected entity."""
    # Show confirmation dialog
    # Remove entity if confirmed
    ...

async def action_suggest(self) -> None:
    """Suggest a new entity using LLM."""
    # Show loading indicator
    # Call suggest logic (reuse from CRUD commands)
    # Display result and confirm
    ...

async def action_check(self) -> None:
    """Run semantic checks."""
    # Switch to check results screen
    # Run checks async with progress
    ...

async def action_build(self) -> None:
    """Build the project."""
    # Show build options dialog (seed, output, etc.)
    # Run build async with progress
    # Switch to build output viewer
    ...

async def action_validate(self) -> None:
    """Validate project structure."""
    # Run validation
    # Display results
    ...
```

### Step 8: Implement Build Output Viewer
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create a screen to view generated content:

**`src/fabulae/tui/screens/build_viewer.py`**

```python
from textual.screen import Screen
from textual.widgets import Markdown, DirectoryTree

class BuildViewerScreen(Screen):
    """View build output files."""

    def __init__(self, build_dir: Path):
        super().__init__()
        self.build_dir = build_dir

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield DirectoryTree(str(self.build_dir), id="files")
            yield Markdown(id="preview")

    def on_directory_tree_file_selected(self, event) -> None:
        path = Path(event.path)
        if path.suffix in [".md", ".txt"]:
            content = path.read_text()
            self.query_one("#preview", Markdown).update(content)
```

### Step 9: Add Styling
**Model: Haiku** (OpenAI alternative: `gpt-5.1-codex-mini`)

Create `src/fabulae/tui/styles.tcss`:

```css
/* Main layout */
#sidebar {
    width: 25%;
    min-width: 20;
    max-width: 40;
    border-right: solid $primary;
}

#content {
    width: 75%;
    padding: 1 2;
}

/* Entity view */
ContentView {
    height: 100%;
    overflow-y: auto;
}

/* Dialogs */
#dialog {
    width: 60;
    height: auto;
    border: thick $primary;
    background: $surface;
    padding: 1 2;
}

/* Tree */
ProjectTree {
    padding: 1;
}

ProjectTree > .tree--cursor {
    background: $primary;
}
```

### Step 10: Implement Progress Indicators
**Model: Haiku** (OpenAI alternative: `gpt-5.1-codex-mini`)

For async operations like LLM calls:

```python
from textual.widgets import LoadingIndicator

async def action_suggest(self) -> None:
    with self.suspend():  # Or use a loading overlay
        loading = LoadingIndicator()
        self.mount(loading)
        try:
            suggestion = await suggest_character(self.project, self.llm_config)
            # Show result
        finally:
            loading.remove()
```

### Step 11: Add CLI Entry Point
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `src/fabulae/features/tui/cli.py` and keep CLI entry code in the feature slice:

```python
def register_tui_commands(app: typer.Typer) -> None:
    @app.callback(invoke_without_command=True)
    def main_callback(
        ctx: typer.Context,
        path: Annotated[Path | None, typer.Argument()] = None,
    ) -> None:
        """
        Fabulae - CLI toolkit for building narratives.

        When called without a command, launches the interactive TUI.
        """
        if ctx.invoked_subcommand is None:
            # No command specified, launch TUI
            project_path = path or Path.cwd()
            try:
                # Validate it's a Fabulae project
                load_project(project_path)
            except Exception as e:
                typer.echo(f"Error: {project_path} is not a valid Fabulae project", err=True)
                typer.echo(str(e), err=True)
                raise typer.Exit(1)

            from fabulae.tui import FabulaeApp
            app = FabulaeApp(project_path)
            app.run()


    @app.command()
    def tui(
        path: Annotated[Path, typer.Argument()] = Path("."),
    ) -> None:
        """Launch the interactive TUI."""
        # Same logic as callback
        ...
```

Wire it in `src/fabulae/main.py`:

```python
from fabulae.features.tui.cli import register_tui_commands

register_tui_commands(app)
```

### Step 12: Write Tests
**Model: Sonnet** (OpenAI alternative: `gpt-5.1-codex-max`)

Create `tests/unit/tui_test.py`:

1. Test app initialization with valid project
2. Test app fails gracefully with invalid project
3. Test project tree population
4. Test entity selection updates content view
5. Test keyboard bindings
6. Use Textual's testing framework: `app.run_test()`

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
   - TUI calls feature services correctly

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Acceptance Criteria Validation:**
   - Verify each acceptance criterion is met
   - Test the TUI manually with a sample project

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Review and update `AGENTS.md` if project structure, testing guidelines, or commit conventions changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/tui/__init__.py` | Create | Package init, exports FabulaeApp |
| `src/fabulae/tui/app.py` | Create | Main TUI application |
| `src/fabulae/tui/styles.tcss` | Create | Textual CSS styles |
| `src/fabulae/tui/widgets/__init__.py` | Create | Widget package |
| `src/fabulae/tui/widgets/project_tree.py` | Create | Project tree widget |
| `src/fabulae/tui/widgets/content_view.py` | Create | Content display widget |
| `src/fabulae/tui/renderers/__init__.py` | Create | Renderer package |
| `src/fabulae/tui/renderers/character.py` | Create | Character renderer |
| `src/fabulae/tui/renderers/scene.py` | Create | Scene renderer |
| `src/fabulae/tui/modals/__init__.py` | Create | Modal package |
| `src/fabulae/tui/modals/edit_character.py` | Create | Character edit modal |
| `src/fabulae/tui/modals/confirm.py` | Create | Confirmation dialog |
| `src/fabulae/tui/screens/__init__.py` | Create | Screen package |
| `src/fabulae/tui/screens/build_viewer.py` | Create | Build output viewer |
| `src/fabulae/features/tui/cli.py` | Create | CLI entry point wiring |
| `src/fabulae/main.py` | Modify | Add TUI entry point |
| `tests/unit/tui_test.py` | Create | TUI tests |

## Keyboard Shortcuts

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit the TUI |
| `e` | Edit | Edit selected entity |
| `a` | Add | Add new entity (context-aware) |
| `d` | Delete | Delete selected entity |
| `s` | Suggest | LLM-powered suggestion |
| `c` | Check | Run semantic checks |
| `b` | Build | Build project output |
| `v` | Validate | Run structural validation |
| `?` | Help | Show help overlay |
| `↑/↓` | Navigate | Move through tree |
| `Enter` | Select | Select/expand tree node |
| `Esc` | Back | Close modal/cancel |

## Acceptance Criteria

- [ ] `fabulae` (no command) launches TUI
- [ ] `fabulae tui /path` launches TUI for specified project
- [ ] Invalid project shows error and exits (no TUI launch)
- [ ] Project tree displays all entities correctly
- [ ] Selecting entity shows formatted details
- [ ] YAML files rendered nicely (not raw YAML)
- [ ] Generated markdown files viewable and formatted
- [ ] Edit modals work for all entity types
- [ ] Keyboard shortcuts function correctly
- [ ] LLM operations show progress indicators
- [ ] Responsive layout works in different terminal sizes
- [ ] All tests pass
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Future Enhancements

- Vim-style navigation (`j/k` for up/down)
- Search/filter in tree
- Split view for comparing entities
- Live preview during edit
- Undo/redo support
- Custom themes
- Plugin system for extending views
