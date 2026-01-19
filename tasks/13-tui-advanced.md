# Task: Advanced TUI Workbench

**Priority:** Medium - enhances user experience after core features are stable.
**Depends on:** `10-tui-simple.md`, `11-check-command.md`, `12-doctor-command.md`

## Overview

Extend the simple TUI from v0.1.0 with advanced features including:
- Semantic checks integration
- Doctor diagnostics integration
- LLM-powered entity suggestions
- Split views for comparing entities
- Search and filtering
- Vim-style navigation
- Custom themes
- Build output preview

This task builds on the foundation laid in task 10 (simple TUI) and integrates the check (task 11) and doctor (task 12) features.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Feature Overview

### 1. Check Integration
Add LLM-powered semantic checks directly in the TUI:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fabulae - The Synesthesia Murders                    [Check Results] novel │
├────────────────────┬────────────────────────────────────────────────────────┤
│ Project            │  Check Results                                         │
│ ├── Characters (3) │  ──────────────────────────────────────────────        │
│ │   ├── vera       │  ✗ [consistency] Character "Marcus" left-handed in    │
│ │   ├── marcus    ◄│    scene-01 but right-handed in scene-05              │
│ │   └── chen       │    Location: scene:scene-05                           │
│ ...                │    [Go to scene] [Dismiss]                            │
│                    │                                                        │
│                    │  ⚠ [pacing] Chapter 2 has only 2 scenes               │
│                    │    Location: chapter:chapter-02                        │
│                    │    [Go to chapter] [Dismiss]                          │
│                    │                                                        │
├────────────────────┴────────────────────────────────────────────────────────┤
│ Filter: [all ▾]  Severity: [all ▾]                    3 issues             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Doctor Integration
Inline diagnostics panel:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fabulae - Diagnostics                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Environment                                                                │
│  ───────────                                                                │
│    ✓ Python 3.12.1                                                          │
│    ✓ Fabulae 0.1.0                                                          │
│                                                                             │
│  LLM Connection                                                             │
│  ──────────────                                                             │
│    ✓ Endpoint: http://localhost:11434/v1                                   │
│    ✓ Connection: reachable (45ms)                                          │
│    ✓ Model: ministral-3:3b                                                 │
│                                                                             │
│  [Refresh]  [Back]                                                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3. LLM Suggestions
Inline entity suggestions with preview:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Suggest New Character                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│  Idea (optional):                                                           │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │ A forensic specialist who helps Vera                                  │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  [Generate]                                                                 │
│                                                                             │
│  ─────────────────────────────────────────────────────────────────────────  │
│  Preview:                                                                   │
│                                                                             │
│  Name: Dr. Sarah Kim                                                        │
│  Role: supporting                                                           │
│  Desire: To apply science to solve crimes                                   │
│  Flaw: Overly detached                                                      │
│  Traits: methodical, precise, skeptical                                     │
│                                                                             │
│  [Accept]  [Regenerate]  [Cancel]                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 4. Split View
Compare entities side by side:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Fabulae - Compare                                                           │
├──────────────────────────────────┬──────────────────────────────────────────┤
│  Scene: scene-discovery          │  Scene: scene-investigation              │
│  ──────────────────────────────  │  ──────────────────────────────────────  │
│  Summary: Vera discovers the     │  Summary: Vera interviews witnesses     │
│  body at the concert hall...     │  at the crime scene...                  │
│                                  │                                          │
│  Characters:                     │  Characters:                             │
│    • vera                        │    • vera                                │
│    • marcus                      │    • chen                                │
│                                  │    • marcus                              │
│  Location: concert-hall          │  Location: police-station               │
│                                  │                                          │
│  Beats:                          │  Beats:                                  │
│    1. Vera enters the hall       │    1. Chen briefs Vera                  │
│    2. Discovers the body         │    2. Witness interviews                │
│    3. Initial assessment         │    3. Evidence review                   │
├──────────────────────────────────┴──────────────────────────────────────────┤
│ [Close Split]                                                               │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5. Search and Filter
Quick search across all entities:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Search: vera                                                    [Esc] Close │
├─────────────────────────────────────────────────────────────────────────────┤
│  Characters                                                                 │
│    vera - Vera Mellifer (protagonist)                                      │
│                                                                             │
│  Scenes                                                                     │
│    scene-discovery - Characters: vera, marcus                              │
│    scene-investigation - Characters: vera, chen, marcus                    │
│    scene-confrontation - Characters: vera, suspect                         │
│                                                                             │
│  World Facts                                                                │
│    vera-apartment - Vera's minimalist apartment                            │
│                                                                             │
│  5 results found                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6. Build Output Preview
Integrated build output viewer:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ Build Output - 2024-01-15_143052                                            │
├────────────────────┬────────────────────────────────────────────────────────┤
│ Files              │  Chapter 1: The Discovery                              │
│ ├── story.md       │  ═══════════════════════════════════════════════════   │
│ ├── chapters/      │                                                        │
│ │   ├── 01-discov◄│  The concert hall was silent, a stark contrast to     │
│ │   ├── 02-invest │  the chaos that usually filled these walls. Vera       │
│ │   └── 03-reveal │  stepped carefully over the crime scene tape,          │
│ └── build.json     │  her synesthesia painting the air with muted           │
│                    │  colors—the lingering emotions of the departed...      │
│                    │                                                        │
│                    │  "Detective Mellifer?" A voice cut through her         │
│                    │  concentration. Marcus approached, his expression      │
│                    │  carefully neutral.                                    │
│                    │                                                        │
├────────────────────┴────────────────────────────────────────────────────────┤
│ Words: 12,453  |  Seed: 42  |  [Export]  [Rebuild]  [Back]                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Implementation Steps

### Step 1: Refactor TUI for Extensibility
**Model: Sonnet**

Update the simple TUI structure to support additional screens and features:

```python
# src/fabulae/features/tui/app.py

class FabulaeApp(App):
    """Extended Fabulae TUI application."""

    SCREENS = {
        "welcome": WelcomeScreen,
        "project": ProjectScreen,
        "build": BuildScreen,
        "check": CheckScreen,      # NEW
        "doctor": DoctorScreen,    # NEW
        "search": SearchScreen,    # NEW
        "compare": CompareScreen,  # NEW
        "output": OutputScreen,    # NEW
    }

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("s", "suggest", "Suggest"),  # NEW: LLM suggestion
        ("c", "check", "Check"),       # NEW: Run checks
        ("D", "doctor", "Doctor"),     # NEW: Diagnostics
        ("b", "build", "Build"),
        ("/", "search", "Search"),     # NEW: Quick search
        ("v", "split", "Split View"),  # NEW: Compare mode
    ]
```

### Step 2: Implement Check Screen
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/check.py`:

```python
from textual.screen import Screen
from textual.widgets import DataTable, Select, Button
from fabulae.features.check.service import run_checks
from fabulae.features.check.models import CheckCategory, CheckSeverity

class CheckScreen(Screen):
    """Display semantic check results."""

    def __init__(self, project: Project):
        super().__init__()
        self.project = project
        self.results: CheckResult | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield Select(
            [("all", "All"), ("consistency", "Consistency"), ...],
            id="category-filter",
        )
        yield Select(
            [("all", "All"), ("error", "Errors"), ("warning", "Warnings")],
            id="severity-filter",
        )
        yield DataTable(id="issues")
        yield Footer()

    async def on_mount(self) -> None:
        # Run checks asynchronously
        self.run_worker(self._run_checks())

    async def _run_checks(self) -> None:
        config = resolve_config(None, None, None, None)
        self.results = await run_checks(
            self.project,
            list(CheckCategory),
            config,
        )
        self._populate_table()

    def _populate_table(self) -> None:
        table = self.query_one("#issues", DataTable)
        table.add_columns("Severity", "Category", "Message", "Location")
        for issue in self.results.issues:
            table.add_row(
                issue.severity.value,
                issue.category.value,
                issue.message[:50] + "..." if len(issue.message) > 50 else issue.message,
                issue.location or "—",
            )
```

### Step 3: Implement Doctor Screen
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/doctor.py`:

```python
from textual.screen import Screen
from textual.widgets import Static, Button
from fabulae.features.doctor.service import run_doctor

class DoctorScreen(Screen):
    """Display environment diagnostics."""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id="report")
        with Horizontal():
            yield Button("Refresh", id="refresh")
            yield Button("Back", id="back")
        yield Footer()

    async def on_mount(self) -> None:
        await self._run_diagnostics()

    async def _run_diagnostics(self) -> None:
        report = await run_doctor(self.app.project_path)
        self._render_report(report)

    def _render_report(self, report: DoctorReport) -> None:
        # Render report similar to CLI formatter but for TUI
        output = []
        for category in report.categories:
            output.append(f"[bold]{category.name}[/bold]")
            for check in category.checks:
                icon = STATUS_ICONS[check.status]
                output.append(f"  {icon} {check.name}: {check.message}")
        self.query_one("#report", Static).update("\n".join(output))
```

### Step 4: Implement LLM Suggestion Modal
**Model: Sonnet**

Create `src/fabulae/features/tui/modals/suggest.py`:

```python
from textual.screen import ModalScreen
from textual.widgets import Input, Button, Static
from fabulae.features.entities.service import suggest_entity

class SuggestModal(ModalScreen):
    """Modal for LLM-powered entity suggestions."""

    def __init__(self, entity_type: str, project: Project):
        super().__init__()
        self.entity_type = entity_type
        self.project = project
        self.suggestion = None

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(f"Suggest New {self.entity_type.title()}")
            yield Input(placeholder="Idea (optional)...", id="idea")
            yield Button("Generate", variant="primary", id="generate")
            yield Static("", id="preview")
            with Horizontal():
                yield Button("Accept", id="accept", disabled=True)
                yield Button("Regenerate", id="regenerate", disabled=True)
                yield Button("Cancel", id="cancel")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id in ("generate", "regenerate"):
            await self._generate_suggestion()
        elif event.button.id == "accept":
            self.dismiss(self.suggestion)
        elif event.button.id == "cancel":
            self.dismiss(None)

    async def _generate_suggestion(self) -> None:
        idea = self.query_one("#idea", Input).value or None
        config = resolve_config(None, None, None, None)

        with self.app.suspend():
            self.suggestion = await suggest_entity(
                self.entity_type,
                self.project,
                idea=idea,
                config=config,
            )

        # Show preview
        self.query_one("#preview", Static).update(
            self._format_preview(self.suggestion)
        )
        self.query_one("#accept", Button).disabled = False
        self.query_one("#regenerate", Button).disabled = False
```

### Step 5: Implement Search Screen
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/search.py`:

```python
from textual.screen import ModalScreen
from textual.widgets import Input, ListView, ListItem

class SearchScreen(ModalScreen):
    """Quick search across all entities."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("enter", "select", "Select"),
    ]

    def __init__(self, project: Project):
        super().__init__()
        self.project = project

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search...", id="query")
        yield ListView(id="results")

    def on_input_changed(self, event: Input.Changed) -> None:
        query = event.value.lower()
        results = self._search(query)
        self._update_results(results)

    def _search(self, query: str) -> list[tuple[str, str, str]]:
        """Search all entities for query match."""
        results = []

        # Search characters
        for char in self.project.characters:
            if query in char.name.lower() or query in char.id.lower():
                results.append(("character", char.id, char.name))

        # Search scenes
        for scene in self.project.plot.scenes or []:
            if query in scene.id.lower() or query in (scene.title or "").lower():
                results.append(("scene", scene.id, scene.title or scene.id))

        # Search world facts
        if self.project.world:
            for fact in self.project.world.facts:
                if query in fact.id.lower():
                    results.append(("world_fact", fact.id, fact.id))

        return results
```

### Step 6: Implement Split/Compare View
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/compare.py`:

```python
from textual.screen import Screen
from textual.containers import Horizontal
from fabulae.features.tui.widgets.entity_view import EntityView

class CompareScreen(Screen):
    """Side-by-side entity comparison."""

    def __init__(self, project: Project, left: tuple[str, str], right: tuple[str, str]):
        super().__init__()
        self.project = project
        self.left_entity = left  # (type, id)
        self.right_entity = right

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield EntityView(id="left-view")
            yield EntityView(id="right-view")
        yield Footer()

    def on_mount(self) -> None:
        left_view = self.query_one("#left-view", EntityView)
        right_view = self.query_one("#right-view", EntityView)

        left_view.show_entity(self.left_entity[0], self.left_entity[1], self.project)
        right_view.show_entity(self.right_entity[0], self.right_entity[1], self.project)
```

### Step 7: Implement Build Output Viewer
**Model: Sonnet**

Create `src/fabulae/features/tui/screens/output.py`:

```python
from textual.screen import Screen
from textual.widgets import DirectoryTree, Markdown

class OutputScreen(Screen):
    """View build output files."""

    def __init__(self, build_dir: Path):
        super().__init__()
        self.build_dir = build_dir

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DirectoryTree(str(self.build_dir), id="files")
            yield Markdown(id="preview")
        with Horizontal():
            yield Button("Export", id="export")
            yield Button("Rebuild", id="rebuild")
            yield Button("Back", id="back")
        yield Footer()

    def on_directory_tree_file_selected(self, event) -> None:
        path = Path(event.path)
        if path.suffix in [".md", ".txt"]:
            content = path.read_text()
            self.query_one("#preview", Markdown).update(content)
```

### Step 8: Add Vim-Style Navigation
**Model: Haiku**

Add optional vim keybindings:

```python
# In app.py or a separate keybindings module

VIM_BINDINGS = [
    ("j", "cursor_down", "Down"),
    ("k", "cursor_up", "Up"),
    ("h", "collapse", "Collapse"),
    ("l", "expand", "Expand"),
    ("g g", "go_top", "Go to top"),
    ("G", "go_bottom", "Go to bottom"),
]

class FabulaeApp(App):
    def __init__(self, *args, vim_mode: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        if vim_mode:
            self.BINDINGS.extend(VIM_BINDINGS)
```

### Step 9: Add Theme Support
**Model: Haiku**

Create `src/fabulae/features/tui/themes.py`:

```python
THEMES = {
    "default": {
        "primary": "#007acc",
        "secondary": "#6c757d",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
    },
    "dark": {
        "primary": "#0d6efd",
        "secondary": "#6c757d",
        "success": "#198754",
        "warning": "#ffc107",
        "error": "#dc3545",
    },
    "light": {
        "primary": "#0d6efd",
        "secondary": "#6c757d",
        "success": "#198754",
        "warning": "#ffc107",
        "error": "#dc3545",
    },
}
```

Add theme selection to CLI:

```bash
fabulae tui --theme dark
```

### Step 10: Update Extended Styles
**Model: Haiku**

Extend `src/fabulae/features/tui/styles.tcss` with new screen styles:

```css
/* Check screen */
CheckScreen DataTable {
    height: 100%;
}

CheckScreen .error {
    color: $error;
}

CheckScreen .warning {
    color: $warning;
}

/* Compare screen */
CompareScreen #left-view, CompareScreen #right-view {
    width: 50%;
    border-right: solid $primary;
}

/* Search modal */
SearchScreen {
    align: center top;
    padding-top: 5;
}

SearchScreen .modal-dialog {
    width: 80%;
    max-width: 100;
}

/* Output viewer */
OutputScreen #files {
    width: 25%;
}

OutputScreen #preview {
    width: 75%;
    padding: 1 2;
}
```

### Step 11: Write Tests
**Model: Sonnet**

Create `tests/unit/features/tui_advanced_test.py`:

1. Test check screen displays results
2. Test doctor screen displays diagnostics
3. Test search finds entities
4. Test compare view shows both entities
5. Test output viewer loads files
6. Test vim keybindings (when enabled)

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - TUI properly integrates check and doctor features
   - No duplicate logic between TUI and CLI
   - Error handling is appropriate
   - Type hints are complete

2. **Integration Check:**
   - All new code integrates properly with existing code
   - Check and doctor services work correctly from TUI
   - Imports are correct
   - No circular dependencies

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Manual Testing:**
   - Test all new screens (check, doctor, search, compare, output)
   - Test LLM suggestions work in TUI
   - Test keyboard shortcuts
   - Test theme switching
   - Test vim mode

5. **Documentation Review:**
   - Update `README.md` with advanced TUI features
   - Update `CLAUDE.md` if architectural patterns changed
   - Document new keyboard shortcuts

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/tui/app.py` | Modify | Add new screens and bindings |
| `src/fabulae/features/tui/screens/check.py` | Create | Check results screen |
| `src/fabulae/features/tui/screens/doctor.py` | Create | Diagnostics screen |
| `src/fabulae/features/tui/screens/search.py` | Create | Search modal |
| `src/fabulae/features/tui/screens/compare.py` | Create | Split view screen |
| `src/fabulae/features/tui/screens/output.py` | Create | Build output viewer |
| `src/fabulae/features/tui/modals/suggest.py` | Create | LLM suggestion modal |
| `src/fabulae/features/tui/themes.py` | Create | Theme definitions |
| `src/fabulae/features/tui/styles.tcss` | Modify | Add new screen styles |
| `src/fabulae/features/tui/cli.py` | Modify | Add --theme, --vim options |
| `tests/unit/features/tui_advanced_test.py` | Create | Advanced TUI tests |

## Keyboard Shortcuts (Extended)

| Key | Action | Description |
|-----|--------|-------------|
| `q` | Quit | Exit the TUI |
| `a` | Add | Add new entity |
| `e` | Edit | Edit selected entity |
| `d` | Delete | Delete selected entity |
| `s` | Suggest | LLM-powered suggestion |
| `c` | Check | Run semantic checks |
| `D` | Doctor | Run diagnostics |
| `b` | Build | Build project output |
| `/` | Search | Quick search |
| `v` | Split | Compare two entities |
| `?` | Help | Show help overlay |
| `↑/↓` | Navigate | Move through tree |
| `Enter` | Select | Select/expand tree node |
| `Esc` | Back | Close modal/cancel |

**Vim Mode (optional):**
| Key | Action | Description |
|-----|--------|-------------|
| `j` | Down | Move cursor down |
| `k` | Up | Move cursor up |
| `h` | Collapse | Collapse tree node |
| `l` | Expand | Expand tree node |
| `gg` | Top | Go to top |
| `G` | Bottom | Go to bottom |

## Acceptance Criteria

- [ ] Check screen displays semantic check results
- [ ] Check results can be filtered by category/severity
- [ ] Doctor screen displays all diagnostics
- [ ] LLM suggestions work with preview and accept/reject
- [ ] Search finds entities across all types
- [ ] Compare view shows two entities side by side
- [ ] Build output viewer displays generated files
- [ ] Vim keybindings work when enabled
- [ ] Theme switching works
- [ ] All tests pass
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Future Enhancements

- Undo/redo support for entity changes
- Live preview during edit
- Export to additional formats from TUI
- Plugin system for extending views
- Custom keybinding configuration
- Project templates from TUI
- Multi-project support (workspace)
