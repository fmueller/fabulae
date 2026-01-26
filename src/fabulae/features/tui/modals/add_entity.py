"""Add entity modal for creating new entities."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from fabulae.models import (
    Character,
    Fragment,
    Scene,
    Stanza,
    WorldFact,
)


class AddCharacterModal(ModalScreen[Character | None]):
    """Modal for adding a new character."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static("Add Character", classes="modal-title")
            yield Static("ID (lowercase-with-hyphens):")
            yield Input(placeholder="character-id", id="id")
            yield Static("Name:")
            yield Input(placeholder="Character Name", id="name")
            yield Static("Role:")
            yield Input(placeholder="protagonist, antagonist, etc.", id="role")
            yield Static("Desire:")
            yield Input(placeholder="What they want", id="desire")
            yield Static("Flaw:")
            yield Input(placeholder="Their flaw", id="flaw")
            with Horizontal(classes="modal-buttons"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            entity_id = self.query_one("#id", Input).value.strip()
            name = self.query_one("#name", Input).value.strip()
            if not entity_id or not name:
                self.notify("ID and Name are required.", severity="error")
                return
            try:
                char = Character(
                    id=entity_id,
                    name=name,
                    role=self.query_one("#role", Input).value.strip() or None,
                    desire=self.query_one("#desire", Input).value.strip() or None,
                    flaw=self.query_one("#flaw", Input).value.strip() or None,
                )
                self.dismiss(char)
            except Exception as exc:
                self.notify(f"Validation error: {exc}", severity="error")
        else:
            self.dismiss(None)


class AddWorldFactModal(ModalScreen[WorldFact | None]):
    """Modal for adding a new world fact."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static("Add World Fact", classes="modal-title")
            yield Static("ID (lowercase-with-hyphens):")
            yield Input(placeholder="fact-id", id="id")
            yield Static("Name:")
            yield Input(placeholder="Fact Name", id="name")
            yield Static("Type (location/culture/history/rule/object):")
            yield Input(placeholder="location", id="type")
            with Horizontal(classes="modal-buttons"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            entity_id = self.query_one("#id", Input).value.strip()
            name = self.query_one("#name", Input).value.strip()
            fact_type = self.query_one("#type", Input).value.strip() or "location"
            if not entity_id or not name:
                self.notify("ID and Name are required.", severity="error")
                return
            try:
                fact = WorldFact(id=entity_id, name=name, type=fact_type)  # type: ignore[arg-type]
                self.dismiss(fact)
            except Exception as exc:
                self.notify(f"Validation error: {exc}", severity="error")
        else:
            self.dismiss(None)


class AddSceneModal(ModalScreen[Scene | None]):
    """Modal for adding a new scene."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static("Add Scene", classes="modal-title")
            yield Static("ID (lowercase-with-hyphens):")
            yield Input(placeholder="scene-id", id="id")
            yield Static("Summary:")
            yield Input(placeholder="Brief scene summary", id="summary")
            yield Static("Goal:")
            yield Input(placeholder="Scene goal", id="goal")
            with Horizontal(classes="modal-buttons"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            entity_id = self.query_one("#id", Input).value.strip()
            if not entity_id:
                self.notify("ID is required.", severity="error")
                return
            try:
                scene = Scene(
                    id=entity_id,
                    summary=self.query_one("#summary", Input).value.strip() or None,
                    goal=self.query_one("#goal", Input).value.strip() or None,
                )
                self.dismiss(scene)
            except Exception as exc:
                self.notify(f"Validation error: {exc}", severity="error")
        else:
            self.dismiss(None)


class AddFragmentModal(ModalScreen[Fragment | None]):
    """Modal for adding a new fragment."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static("Add Fragment", classes="modal-title")
            yield Static("ID (lowercase-with-hyphens):")
            yield Input(placeholder="fragment-id", id="id")
            yield Static("Content:")
            yield Input(placeholder="Fragment content", id="content")
            with Horizontal(classes="modal-buttons"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            entity_id = self.query_one("#id", Input).value.strip()
            content = self.query_one("#content", Input).value.strip()
            if not entity_id or not content:
                self.notify("ID and Content are required.", severity="error")
                return
            try:
                fragment = Fragment(id=entity_id, content=content)
                self.dismiss(fragment)
            except Exception as exc:
                self.notify(f"Validation error: {exc}", severity="error")
        else:
            self.dismiss(None)


class AddStanzaModal(ModalScreen[Stanza | None]):
    """Modal for adding a new stanza."""

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static("Add Stanza", classes="modal-title")
            yield Static("ID (lowercase-with-hyphens):")
            yield Input(placeholder="stanza-id", id="id")
            yield Static("Lines (comma-separated):")
            yield Input(placeholder="Line 1, Line 2, Line 3", id="lines")
            with Horizontal(classes="modal-buttons"):
                yield Button("Add", variant="primary", id="add")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add":
            entity_id = self.query_one("#id", Input).value.strip()
            lines_text = self.query_one("#lines", Input).value.strip()
            if not entity_id or not lines_text:
                self.notify("ID and Lines are required.", severity="error")
                return
            try:
                lines = [line.strip() for line in lines_text.split(",") if line.strip()]
                stanza = Stanza(id=entity_id, lines=lines)
                self.dismiss(stanza)
            except Exception as exc:
                self.notify(f"Validation error: {exc}", severity="error")
        else:
            self.dismiss(None)
