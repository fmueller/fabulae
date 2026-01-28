"""Main project view screen for the Fabulae TUI."""

from __future__ import annotations

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.screen import Screen
from textual.widgets import Footer, Header, Static, Tree

from fabulae.features.tui.loaders import load_project_relaxed
from fabulae.features.tui.modals.add_entity import AddEntityModal
from fabulae.features.tui.modals.confirm import ConfirmModal
from fabulae.features.tui.modals.edit_entity import EditEntityModal
from fabulae.features.tui.screens.build import BuildScreen
from fabulae.features.tui.state import TuiProjectState
from fabulae.features.tui.widgets.entity_view import EntityView
from fabulae.features.tui.widgets.project_tree import ProjectTree
from fabulae.models import (
    Beat,
    Chapter,
    Character,
    Fragment,
    Project,
    Scene,
    Stanza,
    Style,
    World,
    WorldFact,
    save_project,
)


class ProjectScreen(Screen[None]):
    """Main project viewing and editing screen."""

    BINDINGS = [
        ("a", "add", "Add"),
        ("e", "edit", "Edit"),
        ("d", "delete", "Delete"),
        ("b", "build", "Build"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, state: TuiProjectState) -> None:
        super().__init__()
        self.state = state
        if self.state.project is None:
            self.state.project = load_project_relaxed(self.state.project_path)
        assert self.state.project is not None
        self.project: Project = self.state.project

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield ProjectTree(self.project, id="sidebar")
            yield EntityView(id="content")
        yield Static("", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._show_default()
        if self.state.load_error:
            self._set_status(f"Loaded with warnings: {self.state.load_error}")

    def _show_default(self) -> None:
        view = self.query_one(EntityView)
        project = self.project
        title = project.plot.title or project.config.title or "Untitled project"
        view.show_message(f"Select an entity to view details for {title}.")

    def _set_status(self, message: str) -> None:
        self.query_one("#status", Static).update(message)

    def _refresh_tree(self) -> None:
        tree = self.query_one(ProjectTree)
        tree.refresh_tree(self.project)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:  # type: ignore[type-arg]
        node = event.node
        data = node.data or {}
        entity_type = data.get("type")
        entity_id = data.get("id")
        view = self.query_one(EntityView)

        if entity_type == "character":
            character = self._find_character(entity_id)
            if character:
                view.show_character(character)
        elif entity_type == "world_fact":
            fact = self._find_world_fact(entity_id)
            if fact:
                view.show_world_fact(fact)
        elif entity_type == "scene":
            scene = self._find_scene(entity_id)
            if scene:
                view.show_scene(scene)
        elif entity_type == "beat":
            beat = self._find_beat(data)
            if beat:
                view.show_beat(beat)
        elif entity_type == "chapter":
            chapter = self._find_chapter(entity_id)
            if chapter:
                view.show_chapter(chapter)
        elif entity_type == "fragment":
            fragment = self._find_fragment(entity_id)
            if fragment:
                view.show_fragment(fragment)
        elif entity_type == "stanza":
            stanza = self._find_stanza(entity_id)
            if stanza:
                view.show_stanza(stanza)
        elif entity_type == "style":
            style = self.project.style
            view.show_style(style)
        else:
            self._show_default()

    async def action_build(self) -> None:
        await self.app.push_screen(BuildScreen(self.state))

    async def action_add(self) -> None:
        node_data = self._current_node_data()
        entity_type = self._resolve_entity_type(node_data)

        if entity_type is None:
            self._set_status("Select a category or entity to add.")
            return

        result = await self.app.push_screen(AddEntityModal(entity_type, node_data))  # type: ignore[func-returns-value]
        if not result:
            return

        self._apply_add(entity_type, result, node_data)

    async def action_edit(self) -> None:
        node_data = self._current_node_data()
        entity_type = node_data.get("type")
        if not entity_type:
            self._set_status("Select an entity to edit.")
            return

        entity = self._find_entity_for_edit(node_data)
        if entity is None and entity_type != "style":
            self._set_status("Nothing to edit for this selection.")
            return

        result = await self.app.push_screen(EditEntityModal(entity_type, entity))  # type: ignore[func-returns-value]
        if result is None:
            return

        self._apply_edit(entity_type, result, node_data)

    async def action_delete(self) -> None:
        node_data = self._current_node_data()
        entity_type = node_data.get("type")
        entity_id = node_data.get("id")

        if not entity_type or not entity_id:
            self._set_status("Select an entity to delete.")
            return

        confirm = await self.app.push_screen(ConfirmModal(f"Delete {entity_type} '{entity_id}'?"))  # type: ignore[func-returns-value]
        if not confirm:
            return

        self._apply_delete(entity_type, node_data)

    def _current_node_data(self) -> dict[str, Any]:
        tree = self.query_one(ProjectTree)
        node = tree.cursor_node
        return node.data if node and node.data else {}

    def _resolve_entity_type(self, node_data: dict[str, Any]) -> str | None:
        entity_type = node_data.get("type")
        if isinstance(entity_type, str) and entity_type in {
            "character",
            "world_fact",
            "scene",
            "chapter",
            "fragment",
            "stanza",
            "beat",
        }:
            return entity_type
        if entity_type == "beat_group":
            return "beat"
        if entity_type == "style":
            return "style"

        label = self._current_node_label()
        if label.startswith("Characters"):
            return "character"
        if label.startswith("World"):
            return "world_fact"
        if label.startswith("Plot"):
            format_type = self.project.plot.format or "novel"
            if format_type == "micro-prose":
                return "fragment"
            if format_type == "poem":
                return "stanza"
            return "scene"
        if label.startswith("Style"):
            return "style"
        return None

    def _current_node_label(self) -> str:
        tree = self.query_one(ProjectTree)
        if tree.cursor_node is None:
            return ""
        return str(tree.cursor_node.label)

    def _apply_add(self, entity_type: str, data: dict[str, Any], node_data: dict[str, Any]) -> None:
        project = self.project
        if entity_type == "character":
            project.characters.append(Character(**data))
        elif entity_type == "world_fact":
            if project.world is None:
                project.world = World()
            project.world.facts.append(WorldFact(**data))
        elif entity_type == "scene":
            project.plot.scenes.append(Scene(**data))
            self._assign_scene_to_structure(data.get("id"))
        elif entity_type == "beat":
            scene_id = node_data.get("scene_id") or node_data.get("id")
            scene = self._find_scene(scene_id)
            if scene:
                scene.beats.append(Beat(**data))
        elif entity_type == "chapter":
            project.plot.chapters.append(Chapter(**data))
        elif entity_type == "fragment":
            project.plot.fragments.append(Fragment(**data))
        elif entity_type == "stanza":
            project.plot.stanzas.append(Stanza(**data))
        elif entity_type == "style":
            project.style = Style(**data)
        else:
            self._set_status("Unsupported entity type.")
            return

        if self._save_project():
            self._refresh_tree()
            self._set_status("Entity added.")

    def _apply_edit(self, entity_type: str, data: dict[str, Any], node_data: dict[str, Any]) -> None:
        project = self.project
        entity_id = node_data.get("id")

        if entity_type == "character":
            character = self._find_character(entity_id)
            if character:
                self._update_model(character, data)
        elif entity_type == "world_fact":
            fact = self._find_world_fact(entity_id)
            if fact:
                self._update_model(fact, data)
        elif entity_type == "scene":
            scene = self._find_scene(entity_id)
            if scene:
                self._update_model(scene, data)
        elif entity_type == "beat":
            beat = self._find_beat(node_data)
            if beat:
                self._update_model(beat, data)
        elif entity_type == "chapter":
            chapter = self._find_chapter(entity_id)
            if chapter:
                self._update_model(chapter, data)
        elif entity_type == "fragment":
            fragment = self._find_fragment(entity_id)
            if fragment:
                self._update_model(fragment, data)
        elif entity_type == "stanza":
            stanza = self._find_stanza(entity_id)
            if stanza:
                self._update_model(stanza, data)
        elif entity_type == "style":
            if project.style is None:
                project.style = Style(**data)
            else:
                self._update_model(project.style, data)
        else:
            self._set_status("Unsupported entity type.")
            return

        if self._save_project():
            self._refresh_tree()
            self._set_status("Entity updated.")

    def _apply_delete(self, entity_type: str, node_data: dict[str, Any]) -> None:
        project = self.project
        entity_id = node_data.get("id")

        if entity_type == "character":
            for scene in project.plot.scenes:
                if entity_id in scene.characters:
                    scene.characters = [char_id for char_id in scene.characters if char_id != entity_id]
            project.characters = [c for c in project.characters if c.id != entity_id]
        elif entity_type == "world_fact" and project.world:
            for scene in project.plot.scenes:
                if scene.location == entity_id:
                    scene.location = None
                if entity_id in scene.world_fact_ids:
                    scene.world_fact_ids = [fact_id for fact_id in scene.world_fact_ids if fact_id != entity_id]
            project.world.facts = [f for f in project.world.facts if f.id != entity_id]
        elif entity_type == "scene":
            project.plot.scenes = [s for s in project.plot.scenes if s.id != entity_id]
            self._remove_scene_from_structure(entity_id)
        elif entity_type == "beat":
            scene_id = node_data.get("scene_id")
            scene_obj: Scene | None = self._find_scene(scene_id)
            if scene_obj:
                scene_obj.beats = [b for b in scene_obj.beats if b.id != entity_id]
        elif entity_type == "chapter":
            project.plot.chapters = [c for c in project.plot.chapters if c.id != entity_id]
        elif entity_type == "fragment":
            project.plot.fragments = [f for f in project.plot.fragments if f.id != entity_id]
        elif entity_type == "stanza":
            project.plot.stanzas = [s for s in project.plot.stanzas if s.id != entity_id]
        else:
            self._set_status("Unsupported entity type.")
            return

        if self._save_project():
            self._refresh_tree()
            self._set_status("Entity deleted.")

    def _save_project(self) -> bool:
        try:
            save_project(self.project, self.state.project_path)
        except ValueError as exc:
            self._set_status(f"Save failed: {exc}")
            return False
        return True

    @staticmethod
    def _update_model(model: Any, values: dict[str, Any]) -> None:
        for key, value in values.items():
            setattr(model, key, value)

    def _find_character(self, entity_id: str | None) -> Character | None:
        return next((c for c in self.project.characters if c.id == entity_id), None)

    def _find_world_fact(self, entity_id: str | None) -> WorldFact | None:
        if self.project.world is None:
            return None
        return next((f for f in self.project.world.facts if f.id == entity_id), None)

    def _find_scene(self, entity_id: str | None) -> Scene | None:
        return next((s for s in self.project.plot.scenes if s.id == entity_id), None)

    def _find_beat(self, node_data: dict[str, Any]) -> Beat | None:
        scene_id = node_data.get("scene_id")
        beat_id = node_data.get("id")
        scene = self._find_scene(scene_id)
        if scene is None:
            return None
        return next((b for b in scene.beats if b.id == beat_id), None)

    def _find_chapter(self, entity_id: str | None) -> Chapter | None:
        return next((c for c in self.project.plot.chapters if c.id == entity_id), None)

    def _find_fragment(self, entity_id: str | None) -> Fragment | None:
        return next((f for f in self.project.plot.fragments if f.id == entity_id), None)

    def _find_stanza(self, entity_id: str | None) -> Stanza | None:
        return next((s for s in self.project.plot.stanzas if s.id == entity_id), None)

    def _find_entity_for_edit(self, node_data: dict[str, Any]) -> Any:
        entity_type = node_data.get("type")
        entity_id = node_data.get("id")

        if entity_type == "character":
            return self._find_character(entity_id)
        if entity_type == "world_fact":
            return self._find_world_fact(entity_id)
        if entity_type == "scene":
            return self._find_scene(entity_id)
        if entity_type == "beat":
            return self._find_beat(node_data)
        if entity_type == "chapter":
            return self._find_chapter(entity_id)
        if entity_type == "fragment":
            return self._find_fragment(entity_id)
        if entity_type == "stanza":
            return self._find_stanza(entity_id)
        if entity_type == "style":
            return self.project.style
        return None

    def _assign_scene_to_structure(self, scene_id: str | None) -> None:
        if not scene_id:
            return
        plot = self.project.plot
        if plot.chapters:
            chapter = plot.chapters[0]
            if chapter.scene_ids is None:
                chapter.scene_ids = []
            if scene_id not in chapter.scene_ids:
                chapter.scene_ids.append(scene_id)
        elif plot.scene_ids is not None and scene_id not in plot.scene_ids:
            plot.scene_ids.append(scene_id)

    def _remove_scene_from_structure(self, scene_id: str | None) -> None:
        if not scene_id:
            return
        plot = self.project.plot
        if plot.chapters:
            for chapter in plot.chapters:
                if chapter.scene_ids:
                    chapter.scene_ids = [sid for sid in chapter.scene_ids if sid != scene_id]
        if plot.scene_ids:
            plot.scene_ids = [sid for sid in plot.scene_ids if sid != scene_id]
