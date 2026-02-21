"""Modal for editing entities in the TUI."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Select, Static, TextArea

from fabulae.features.tui.modals.add_entity import FieldSpec, _field_specs, _normalize_form_data


class EditEntityModal(ModalScreen[dict[str, Any] | None]):
    """Modal screen for editing an existing entity."""

    def __init__(self, entity_type: str, entity: Any) -> None:
        super().__init__()
        self.entity_type = entity_type
        self.entity = entity
        self._field_specs = _field_specs(entity_type)

    def compose(self) -> ComposeResult:
        with Vertical(classes="modal-dialog"):
            yield Static(f"Edit {self.entity_type.replace('_', ' ').title()}", classes="modal-title")
            for field in self._field_specs:
                if field.name == "id":
                    continue
                yield Static(field.label)
                if field.kind == "select" and field.options:
                    select = Select(field.options, id=field.name)
                    select.value = self._value_for(field)
                    yield select
                elif field.kind == "text-area":
                    text_area = TextArea(id=field.name)
                    text_area.text = self._value_for(field)
                    yield text_area
                else:
                    input_field = Input(id=field.name)
                    input_field.value = self._value_for(field)
                    yield input_field
            with Horizontal():
                yield Button("Save", variant="primary", id="save")
                yield Button("Cancel", id="cancel")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss(None)
            return

        if event.button.id != "save":
            return

        data: dict[str, Any] = {}
        for field in self._field_specs:
            if field.name == "id":
                continue
            if field.kind == "select":
                value = self.query_one(f"#{field.name}", Select).value
            elif field.kind == "text-area":
                value = self.query_one(f"#{field.name}", TextArea).text
            else:
                value = self.query_one(f"#{field.name}", Input).value
            data[field.name] = value

        self.dismiss(_normalize_form_data(self.entity_type, data))

    def _value_for(self, field: FieldSpec) -> str:
        if self.entity is None:
            return ""

        value = getattr(self.entity, field.name, "")
        if value is None:
            return ""
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)
        return str(value)
