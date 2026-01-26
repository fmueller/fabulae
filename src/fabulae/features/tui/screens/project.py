"""Project view screen for the Fabulae TUI."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Tree

from fabulae.features.tui.modals.add_entity import (
    AddCharacterModal,
    AddFragmentModal,
    AddSceneModal,
    AddStanzaModal,
    AddWorldFactModal,
)
from fabulae.features.tui.modals.confirm import ConfirmModal
from fabulae.features.tui.modals.edit_entity import (
    EditCharacterModal,
    EditWorldFactModal,
)
from fabulae.features.tui.widgets.entity_view import EntityView
from fabulae.features.tui.widgets.project_tree import ProjectTree
from fabulae.models import (
    Character,
    World,
    WorldFact,
    load_project,
    save_project,
)


class ProjectScreen(Screen[None]):
    """Main project viewing and editing screen."""

    BINDINGS = [
        ("a", "add_entity", "Add"),
        ("e", "edit_entity", "Edit"),
        ("d", "delete_entity", "Delete"),
        ("b", "build", "Build"),
        ("q", "quit_app", "Quit"),
    ]

    def __init__(self, project_path: Path) -> None:
        super().__init__()
        self.project_path = project_path
        self.project = load_project(project_path)

    def compose(self) -> ComposeResult:
        title = self.project.plot.title or self.project.config.title or "Untitled"
        fmt = self.project.plot.format or "novel"
        yield Header(show_clock=False)
        with Horizontal():
            yield ProjectTree(self.project, id="sidebar")
            yield EntityView("Select an entity from the tree to view details.", id="content")
        yield Footer()
        self.title = f"Fabulae - {title} [{fmt}]"

    def on_tree_node_selected(self, event: Tree.NodeSelected[tuple[str, str | None]]) -> None:
        """Handle tree node selection to display entity details."""
        if event.node.data is not None:
            entity_type, entity_id = event.node.data
            entity_view = self.query_one("#content", EntityView)
            entity_view.show_entity(entity_type, entity_id, self.project)

    def _get_selected_entity_info(self) -> tuple[str, str | None] | None:
        """Get the entity type and ID from the currently selected tree node."""
        tree = self.query_one("#sidebar", ProjectTree)
        node = tree.cursor_node
        if node is not None and node.data is not None:
            return node.data
        return None

    def _refresh_view(self) -> None:
        """Reload project and refresh the tree and detail view."""
        self.project = load_project(self.project_path)
        tree = self.query_one("#sidebar", ProjectTree)
        tree.rebuild(self.project)
        entity_view = self.query_one("#content", EntityView)
        entity_view.update("Select an entity from the tree to view details.")

    def _get_entity_type_from_context(self) -> str | None:
        """Determine entity type from the current tree selection context."""
        info = self._get_selected_entity_info()
        if info is not None:
            return info[0]
        return None

    async def _push_modal(self, modal: Any) -> Any:
        """Push a modal screen and wait for its result.

        Uses Any to avoid generic type inference issues with different modal types.
        """
        return await self.app.push_screen_wait(modal)

    async def action_add_entity(self) -> None:
        """Add a new entity based on current selection context."""
        entity_type = self._get_entity_type_from_context()
        fmt = self.project.plot.format or "novel"

        if entity_type == "character" or entity_type is None:
            char_result: Character | None = await self._push_modal(AddCharacterModal())
            if char_result is not None:
                self.project.characters.append(char_result)
                save_project(self.project, self.project_path)
                self._refresh_view()
                self.notify(f"Added character: {char_result.name}")

        elif entity_type == "world_fact":
            fact_result: WorldFact | None = await self._push_modal(AddWorldFactModal())
            if fact_result is not None:
                if self.project.world is None:
                    self.project.world = World(facts=[fact_result])
                else:
                    self.project.world.facts.append(fact_result)
                save_project(self.project, self.project_path)
                self._refresh_view()
                self.notify(f"Added world fact: {fact_result.name}")

        elif entity_type == "scene" and fmt in ("novel", "novella", "short-story"):
            scene_result = await self._push_modal(AddSceneModal())
            if scene_result is not None:
                self.project.plot.scenes.append(scene_result)
                save_project(self.project, self.project_path)
                self._refresh_view()
                self.notify(f"Added scene: {scene_result.id}")

        elif entity_type == "fragment" and fmt == "micro-prose":
            fragment_result = await self._push_modal(AddFragmentModal())
            if fragment_result is not None:
                self.project.plot.fragments.append(fragment_result)
                save_project(self.project, self.project_path)
                self._refresh_view()
                self.notify(f"Added fragment: {fragment_result.id}")

        elif entity_type == "stanza" and fmt == "poem":
            stanza_result = await self._push_modal(AddStanzaModal())
            if stanza_result is not None:
                self.project.plot.stanzas.append(stanza_result)
                save_project(self.project, self.project_path)
                self._refresh_view()
                self.notify(f"Added stanza: {stanza_result.id}")

        else:
            self.notify("Select an entity category to add to.", severity="warning")

    async def action_edit_entity(self) -> None:
        """Edit the selected entity."""
        info = self._get_selected_entity_info()
        if info is None:
            self.notify("Select an entity to edit.", severity="warning")
            return

        entity_type, entity_id = info

        if entity_type == "character" and entity_id:
            char = self._find_character(entity_id)
            if char:
                edit_result: Character | None = await self._push_modal(EditCharacterModal(char))
                if edit_result is not None:
                    self.project.characters = [
                        edit_result if c.id == entity_id else c for c in self.project.characters
                    ]
                    save_project(self.project, self.project_path)
                    self._refresh_view()
                    self.notify(f"Updated character: {edit_result.name}")

        elif entity_type == "world_fact" and entity_id:
            fact = self._find_world_fact(entity_id)
            if fact:
                fact_edit_result: WorldFact | None = await self._push_modal(EditWorldFactModal(fact))
                if fact_edit_result is not None and self.project.world:
                    self.project.world.facts = [
                        fact_edit_result if f.id == entity_id else f for f in self.project.world.facts
                    ]
                    save_project(self.project, self.project_path)
                    self._refresh_view()
                    self.notify(f"Updated world fact: {fact_edit_result.name}")

        else:
            self.notify("Edit is only supported for characters and world facts.", severity="warning")

    async def action_delete_entity(self) -> None:
        """Delete the selected entity."""
        info = self._get_selected_entity_info()
        if info is None:
            self.notify("Select an entity to delete.", severity="warning")
            return

        entity_type, entity_id = info
        if entity_id is None:
            self.notify("Cannot delete this item.", severity="warning")
            return

        confirmed: bool = await self._push_modal(
            ConfirmModal("Delete Entity", f"Delete {entity_type} '{entity_id}'?")
        )
        if not confirmed:
            return

        deleted = False
        if entity_type == "character":
            original_count = len(self.project.characters)
            self.project.characters = [c for c in self.project.characters if c.id != entity_id]
            deleted = len(self.project.characters) < original_count

        elif entity_type == "world_fact" and self.project.world:
            original_count = len(self.project.world.facts)
            self.project.world.facts = [f for f in self.project.world.facts if f.id != entity_id]
            deleted = len(self.project.world.facts) < original_count

        elif entity_type == "scene":
            original_count = len(self.project.plot.scenes)
            self.project.plot.scenes = [s for s in self.project.plot.scenes if s.id != entity_id]
            # Also remove from chapter scene_ids
            for chapter in self.project.plot.chapters:
                if chapter.scene_ids:
                    chapter.scene_ids = [sid for sid in chapter.scene_ids if sid != entity_id]
            deleted = len(self.project.plot.scenes) < original_count

        elif entity_type == "fragment":
            original_count = len(self.project.plot.fragments)
            self.project.plot.fragments = [f for f in self.project.plot.fragments if f.id != entity_id]
            deleted = len(self.project.plot.fragments) < original_count

        elif entity_type == "stanza":
            original_count = len(self.project.plot.stanzas)
            self.project.plot.stanzas = [s for s in self.project.plot.stanzas if s.id != entity_id]
            deleted = len(self.project.plot.stanzas) < original_count

        if deleted:
            try:
                save_project(self.project, self.project_path)
                self._refresh_view()
                self.notify(f"Deleted {entity_type}: {entity_id}")
            except Exception as exc:
                # Reload to restore valid state
                self.project = load_project(self.project_path)
                self._refresh_view()
                self.notify(f"Delete failed (validation): {exc}", severity="error")
        else:
            self.notify(f"Entity not found: {entity_id}", severity="warning")

    def action_build(self) -> None:
        """Switch to build screen."""
        from fabulae.features.tui.screens.build import BuildScreen

        self.app.push_screen(BuildScreen(self.project, self.project_path))

    def action_quit_app(self) -> None:
        """Quit the application."""
        self.app.exit()

    def _find_character(self, entity_id: str) -> Character | None:
        for char in self.project.characters:
            if char.id == entity_id:
                return char
        return None

    def _find_world_fact(self, entity_id: str) -> WorldFact | None:
        if self.project.world:
            for fact in self.project.world.facts:
                if fact.id == entity_id:
                    return fact
        return None
