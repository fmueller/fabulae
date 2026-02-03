"""Modal for adding entities in the TUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Select, Static, TextArea


@dataclass(frozen=True)
class FieldSpec:
    name: str
    label: str
    kind: str = "input"
    options: list[tuple[str, str]] | None = None


class AddEntityModal(ModalScreen[dict[str, Any] | None]):
    """Modal screen for adding a new entity."""

    def __init__(self, entity_type: str, context: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.entity_type = entity_type
        self.context = context or {}
        self._field_specs = _field_specs(entity_type)

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(f"Add {self.entity_type.replace('_', ' ').title()}", classes="modal-title")
            yield Static("", id="error-message", classes="error-text")
            for field in self._field_specs:
                yield Static(field.label)
                if field.kind == "select" and field.options:
                    yield Select(field.options, id=field.name)
                elif field.kind == "text-area":
                    yield TextArea(id=field.name)
                else:
                    yield Input(id=field.name)
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    def _show_error(self, message: str) -> None:
        self.query_one("#error-message", Static).update(message)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        if event.button.id != "save":
            return

        data: dict[str, Any] = {}
        for field in self._field_specs:
            if field.kind == "select":
                value = self.query_one(f"#{field.name}", Select).value
            elif field.kind == "text-area":
                value = self.query_one(f"#{field.name}", TextArea).text
            else:
                value = self.query_one(f"#{field.name}", Input).value
            data[field.name] = value

        # Validate before normalizing
        errors = _validate_form_data(self.entity_type, data)
        if errors:
            self._show_error(errors[0])
            return

        self.dismiss(_normalize_form_data(self.entity_type, data))


def _field_specs(entity_type: str) -> list[FieldSpec]:
    if entity_type == "character":
        return [
            FieldSpec("id", "ID"),
            FieldSpec("name", "Name"),
            FieldSpec("role", "Role"),
            FieldSpec("desire", "Desire"),
            FieldSpec("need", "Need"),
            FieldSpec("flaw", "Flaw"),
            FieldSpec("secret", "Secret"),
            FieldSpec("traits", "Traits (comma-separated)"),
        ]
    if entity_type == "world_fact":
        return [
            FieldSpec("id", "ID"),
            FieldSpec(
                "type",
                "Type",
                kind="select",
                options=[
                    ("location", "Location"),
                    ("culture", "Culture"),
                    ("history", "History"),
                    ("rule", "Rule"),
                    ("object", "Object"),
                ],
            ),
            FieldSpec("name", "Name"),
            FieldSpec("facts", "Facts (comma-separated)", kind="text-area"),
        ]
    if entity_type == "scene":
        return [
            FieldSpec("id", "ID"),
            FieldSpec("location", "Location ID"),
            FieldSpec("time", "Time"),
            FieldSpec("characters", "Characters (comma-separated)"),
            FieldSpec("world_fact_ids", "World facts (comma-separated)"),
            FieldSpec("summary", "Summary", kind="text-area"),
            FieldSpec("goal", "Goal"),
            FieldSpec("conflict", "Conflict"),
            FieldSpec("outcome", "Outcome"),
        ]
    if entity_type == "beat":
        return [
            FieldSpec("id", "ID"),
            FieldSpec("kind", "Kind"),
            FieldSpec("summary", "Summary", kind="text-area"),
            FieldSpec("target_words", "Target words"),
            FieldSpec("goal", "Goal"),
            FieldSpec("conflict", "Conflict"),
            FieldSpec("outcome", "Outcome"),
            FieldSpec("pace", "Pace"),
            FieldSpec("constraints", "Constraints (comma-separated)"),
        ]
    if entity_type == "chapter":
        return [
            FieldSpec("id", "ID"),
            FieldSpec("title", "Title"),
            FieldSpec("summary", "Summary", kind="text-area"),
            FieldSpec("scene_ids", "Scene IDs (comma-separated)"),
        ]
    if entity_type == "fragment":
        return [
            FieldSpec("id", "ID"),
            FieldSpec("content", "Content", kind="text-area"),
            FieldSpec("target_words", "Target words"),
            FieldSpec("notes", "Notes"),
        ]
    if entity_type == "stanza":
        return [
            FieldSpec("id", "ID"),
            FieldSpec("lines", "Lines", kind="text-area"),
            FieldSpec("meter", "Meter"),
            FieldSpec("rhyme_scheme", "Rhyme scheme"),
        ]
    if entity_type == "style":
        return [
            FieldSpec("language", "Language"),
            FieldSpec("pov", "POV"),
            FieldSpec("tense", "Tense"),
            FieldSpec("voice", "Voice"),
            FieldSpec("register_", "Register"),
            FieldSpec("constraints", "Constraints (comma-separated)", kind="text-area"),
        ]
    return []


def _validate_form_data(entity_type: str, data: dict[str, Any]) -> list[str]:
    """Validate form data and return list of error messages."""
    errors: list[str] = []

    # Validate required ID field
    entity_id = data.get("id", "")
    if entity_id and not _is_valid_id(entity_id):
        errors.append("ID must be lowercase alphanumeric with hyphens (e.g., scene-01)")

    # Validate integer fields
    if entity_type in ("beat", "fragment"):
        target_words = data.get("target_words", "")
        if target_words and not _is_valid_int(target_words):
            errors.append("Target words must be a number")

    return errors


def _is_valid_id(value: str) -> bool:
    """Check if value is a valid entity ID."""
    import re

    return bool(re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", value))


def _is_valid_int(value: str) -> bool:
    """Check if value can be converted to an integer."""
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return False


def _normalize_form_data(entity_type: str, raw: dict[str, Any]) -> dict[str, Any]:
    def list_from(value: str | None) -> list[str]:
        if value is None:
            return []
        parts = [item.strip() for item in value.replace("\n", ",").split(",")]
        return [item for item in parts if item]

    data: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, str) and not value.strip():
            value = None
        data[key] = value

    if entity_type == "character":
        data["traits"] = list_from(raw.get("traits"))
    if entity_type == "world_fact":
        data["facts"] = list_from(raw.get("facts"))
    if entity_type == "scene":
        data["characters"] = list_from(raw.get("characters"))
        data["world_fact_ids"] = list_from(raw.get("world_fact_ids"))
    if entity_type == "beat":
        data["constraints"] = list_from(raw.get("constraints"))
        data["target_words"] = _to_int(raw.get("target_words"))
    if entity_type == "chapter":
        data["scene_ids"] = list_from(raw.get("scene_ids")) or None
    if entity_type == "fragment":
        data["target_words"] = _to_int(raw.get("target_words"))
    if entity_type == "stanza":
        data["lines"] = list_from(raw.get("lines"))
    if entity_type == "style":
        data["constraints"] = list_from(raw.get("constraints"))

    return {key: value for key, value in data.items() if value is not None}


def _to_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
