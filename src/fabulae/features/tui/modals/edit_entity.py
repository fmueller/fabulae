"""Edit entity modal for modifying existing entities."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from fabulae.models import Character, WorldFact


class EditCharacterModal(ModalScreen[Character | None]):
    """Modal for editing an existing character."""

    def __init__(self, character: Character) -> None:
        super().__init__()
        self._character = character

    def compose(self) -> ComposeResult:
        char = self._character
        with Vertical(classes="modal-dialog"):
            yield Static(f"Edit Character: {char.name}", classes="modal-title")
            yield Static("Name:")
            yield Input(value=char.name, id="name")
            yield Static("Role:")
            yield Input(value=char.role or "", id="role")
            yield Static("Desire:")
            yield Input(value=char.desire or "", id="desire")
            yield Static("Need:")
            yield Input(value=char.need or "", id="need")
            yield Static("Flaw:")
            yield Input(value=char.flaw or "", id="flaw")
            yield Static("Secret:")
            yield Input(value=char.secret or "", id="secret")
            yield Static("Traits (comma-separated):")
            yield Input(value=", ".join(char.traits), id="traits")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            name = self.query_one("#name", Input).value.strip()
            if not name:
                self.notify("Name is required.", severity="error")
                return
            traits_text = self.query_one("#traits", Input).value.strip()
            traits = [t.strip() for t in traits_text.split(",") if t.strip()] if traits_text else []
            try:
                updated = Character(
                    id=self._character.id,
                    name=name,
                    role=self.query_one("#role", Input).value.strip() or None,
                    desire=self.query_one("#desire", Input).value.strip() or None,
                    need=self.query_one("#need", Input).value.strip() or None,
                    flaw=self.query_one("#flaw", Input).value.strip() or None,
                    secret=self.query_one("#secret", Input).value.strip() or None,
                    traits=traits,
                )
                self.dismiss(updated)
            except Exception as exc:
                self.notify(f"Validation error: {exc}", severity="error")
        else:
            self.dismiss(None)


class EditWorldFactModal(ModalScreen[WorldFact | None]):
    """Modal for editing an existing world fact."""

    def __init__(self, fact: WorldFact) -> None:
        super().__init__()
        self._fact = fact

    def compose(self) -> ComposeResult:
        fact = self._fact
        with Vertical(classes="modal-dialog"):
            yield Static(f"Edit World Fact: {fact.name}", classes="modal-title")
            yield Static("Name:")
            yield Input(value=fact.name, id="name")
            yield Static("Type (location/culture/history/rule/object):")
            yield Input(value=fact.type, id="type")
            yield Static("Facts (comma-separated):")
            yield Input(value=", ".join(fact.facts), id="facts")
            with Horizontal(classes="modal-buttons"):
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save":
            name = self.query_one("#name", Input).value.strip()
            if not name:
                self.notify("Name is required.", severity="error")
                return
            fact_type = self.query_one("#type", Input).value.strip() or "location"
            facts_text = self.query_one("#facts", Input).value.strip()
            facts = [f.strip() for f in facts_text.split(",") if f.strip()] if facts_text else []
            try:
                updated = WorldFact(
                    id=self._fact.id,
                    name=name,
                    type=fact_type,  # type: ignore[arg-type]
                    facts=facts,
                )
                self.dismiss(updated)
            except Exception as exc:
                self.notify(f"Validation error: {exc}", severity="error")
        else:
            self.dismiss(None)
