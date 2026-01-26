"""Project tree widget for navigating project structure."""

from __future__ import annotations

from typing import Any

from textual.widgets import Tree

from fabulae.models import Project, Scene


class ProjectTree(Tree[tuple[str, str | None]]):
    """Tree view of project structure."""

    def __init__(self, project: Project, **kwargs: Any) -> None:
        super().__init__("Project", **kwargs)
        self.project = project
        self._build_tree()

    def _build_tree(self) -> None:
        self.root.expand()

        # Characters
        char_count = len(self.project.characters)
        chars_node = self.root.add(f"Characters ({char_count})")
        for char in self.project.characters:
            chars_node.add_leaf(char.name, data=("character", char.id))

        # World facts
        if self.project.world and self.project.world.facts:
            facts = self.project.world.facts
            world_node = self.root.add(f"World ({len(facts)})")

            locations = [f for f in facts if f.type == "location"]
            others = [f for f in facts if f.type != "location"]

            if locations:
                loc_node = world_node.add(f"Locations ({len(locations)})")
                for loc in locations:
                    loc_node.add_leaf(loc.name, data=("world_fact", loc.id))

            if others:
                other_node = world_node.add(f"Other Facts ({len(others)})")
                for fact in others:
                    other_node.add_leaf(f"{fact.name} [{fact.type}]", data=("world_fact", fact.id))

        # Plot structure (format-dependent)
        fmt = self.project.plot.format or "novel"
        plot_node = self.root.add("Plot")

        if fmt in ("novel", "novella", "short-story"):
            if self.project.plot.chapters:
                for chapter in self.project.plot.chapters:
                    title = chapter.title or chapter.id
                    scene_count = len(chapter.scene_ids) if chapter.scene_ids else 0
                    ch_node = plot_node.add(f"{title} ({scene_count} scenes)", data=("chapter", chapter.id))
                    if chapter.scene_ids:
                        for scene_id in chapter.scene_ids:
                            scene = self._find_scene(scene_id)
                            label = scene_id if scene is None else (scene.summary or scene.id)[:40]
                            ch_node.add_leaf(label, data=("scene", scene_id))
            elif self.project.plot.scenes:
                for scene in self.project.plot.scenes:
                    label = (scene.summary or scene.id)[:40]
                    plot_node.add_leaf(label, data=("scene", scene.id))

        elif fmt == "micro-prose":
            for fragment in self.project.plot.fragments:
                label = (fragment.content[:40] + "...") if len(fragment.content) > 40 else fragment.content
                plot_node.add_leaf(label, data=("fragment", fragment.id))

        elif fmt == "poem":
            for stanza in self.project.plot.stanzas:
                first_line = stanza.lines[0] if stanza.lines else stanza.id
                label = (first_line[:40] + "...") if len(first_line) > 40 else first_line
                plot_node.add_leaf(label, data=("stanza", stanza.id))

        # Style
        if self.project.style:
            self.root.add_leaf("Style", data=("style", None))

    def _find_scene(self, scene_id: str) -> Scene | None:
        for scene in self.project.plot.scenes:
            if scene.id == scene_id:
                return scene
        return None

    def rebuild(self, project: Project) -> None:
        """Rebuild the tree with updated project data."""
        self.project = project
        self.clear()
        self._build_tree()
