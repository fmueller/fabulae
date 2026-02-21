"""Project tree widget for the Fabulae TUI."""

from __future__ import annotations

from typing import Any

from textual.widgets import Tree

from fabulae.models import Project, WorldFact


class ProjectTree(Tree[dict[str, object]]):
    """Tree view of project structure."""

    def __init__(self, project: Project, id: str | None = None) -> None:
        super().__init__("Project", id=id)
        self.project = project
        self._build_tree()
        self.root.expand()

    def refresh_tree(self, project: Project) -> None:
        self.project = project
        self.root.children.clear()  # type: ignore[attr-defined]
        self._build_tree()
        self.root.expand()

    def _build_tree(self) -> None:
        characters = self.root.add(f"Characters ({len(self.project.characters)})")
        for character in self.project.characters:
            characters.add_leaf(character.name or character.id, data={"type": "character", "id": character.id})

        world = self.root.add(self._world_label())
        if self.project.world:
            grouped = self._group_world_facts(self.project.world.facts)
            for label, facts in grouped.items():
                group_node = world.add(label)
                for fact in facts:
                    group_node.add_leaf(
                        fact.name or fact.id,
                        data={"type": "world_fact", "id": fact.id},
                    )

        plot = self.root.add("Plot")
        if self.project.plot.chapters:
            for chapter in self.project.plot.chapters:
                chapter_node = plot.add(
                    chapter.title or chapter.id,
                    data={"type": "chapter", "id": chapter.id},
                )
                scene_ids = chapter.scene_ids or []
                for scene_id in scene_ids:
                    scene_node = chapter_node.add(scene_id, data={"type": "scene", "id": scene_id})
                    self._add_beats(scene_node, scene_id)
        elif self.project.plot.scenes:
            for scene in self.project.plot.scenes:
                scene_node = plot.add(scene.id, data={"type": "scene", "id": scene.id})
                self._add_beats(scene_node, scene.id)
        elif self.project.plot.fragments:
            for fragment in self.project.plot.fragments:
                plot.add(fragment.id, data={"type": "fragment", "id": fragment.id})
        elif self.project.plot.stanzas:
            for stanza in self.project.plot.stanzas:
                plot.add(stanza.id, data={"type": "stanza", "id": stanza.id})
        elif self.project.plot.lines:
            for index, _line in enumerate(self.project.plot.lines, 1):
                plot.add_leaf(f"Line {index}")

        style_label = "Style" if self.project.style else "Style (missing)"
        self.root.add_leaf(style_label, data={"type": "style", "id": None})

    def _add_beats(self, scene_node: Any, scene_id: str) -> None:
        scene = next((s for s in self.project.plot.scenes if s.id == scene_id), None)
        if scene is None or not scene.beats:
            return
        beats_node = scene_node.add("Beats", data={"type": "beat_group", "scene_id": scene_id})
        for beat in scene.beats:
            beats_node.add_leaf(beat.id, data={"type": "beat", "id": beat.id, "scene_id": scene_id})

    def _world_label(self) -> str:
        count = len(self.project.world.facts) if self.project.world else 0
        return f"World ({count})"

    @staticmethod
    def _group_world_facts(facts: list[WorldFact]) -> dict[str, list[WorldFact]]:
        groups: dict[str, list[WorldFact]] = {}
        for fact in facts:
            label = fact.type.replace("_", " ").title()
            groups.setdefault(label, []).append(fact)
        return groups
