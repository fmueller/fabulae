"""Welcome/Create screen for the Fabulae TUI."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Input, Select, Static

from fabulae import __version__
from fabulae.features.create.shapes.loader import get_shape_ids
from fabulae.models import AVAILABLE_FORMATS, LiteratureFormat


class WelcomeScreen(Screen[tuple[str, LiteratureFormat, str | None] | None]):
    """Welcome screen for creating new projects."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
    ]

    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self.project_path = project_path

    def compose(self) -> ComposeResult:
        format_options: list[tuple[str, str]] = [(f, f) for f in AVAILABLE_FORMATS]
        shape_ids = get_shape_ids()
        shape_options: list[tuple[str, str]] = [("(none)", "none")] + [(s, s) for s in shape_ids]

        with Vertical(id="welcome-container"):
            yield Static(f"Fabulae v{__version__}", id="title")
            yield Static("Create a new narrative project", id="subtitle")
            yield Static("Enter your story idea:")
            yield Input(
                placeholder="A detective with synesthesia investigates murders...",
                id="idea-input",
            )
            with Horizontal(classes="form-row"):
                yield Static("Format: ", id="format-label")
                yield Select(format_options, value="novel", id="format-select")
            with Horizontal(classes="form-row"):
                yield Static("Shape:  ", id="shape-label")
                yield Select(shape_options, value="none", id="shape-select")
            with Horizontal(classes="form-buttons"):
                yield Button("Create Project", variant="primary", id="create")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            idea = self.query_one("#idea-input", Input).value.strip()
            if not idea:
                self.notify("Please enter a story idea.", severity="error")
                return
            format_select = self.query_one("#format-select", Select)
            shape_select = self.query_one("#shape-select", Select)
            format_value: LiteratureFormat = str(format_select.value)  # type: ignore[assignment]
            shape_value = str(shape_select.value)
            shape: str | None = None if shape_value == "none" else shape_value
            self.dismiss((idea, format_value, shape))
        elif event.button.id == "cancel":
            self.dismiss(None)

    def action_cancel(self) -> None:
        self.dismiss(None)
