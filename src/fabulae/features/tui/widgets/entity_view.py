"""Entity detail view widget."""

from __future__ import annotations

from typing import Any

from textual.widgets import Static

from fabulae.models import (
    Chapter,
    Character,
    Fragment,
    Project,
    Scene,
    Stanza,
    Style,
    WorldFact,
)


class EntityView(Static):
    """Displays formatted details of selected entity."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.last_content: str = ""

    def update(self, content: object = "") -> None:  # type: ignore[override]
        """Update content and track it for testing."""
        self.last_content = str(content)
        super().update(content)  # type: ignore[arg-type]

    def show_character(self, char: Character) -> None:
        """Display character details."""
        lines = [
            f"Character: {char.name}",
            "=" * 40,
            f"ID: {char.id}",
            f"Role: {char.role or '---'}",
            f"Desire: {char.desire or '---'}",
            f"Need: {char.need or '---'}",
            f"Flaw: {char.flaw or '---'}",
            f"Secret: {char.secret or '---'}",
        ]
        if char.traits:
            lines.append(f"Traits: {', '.join(char.traits)}")
        self.update("\n".join(lines))

    def show_world_fact(self, fact: WorldFact) -> None:
        """Display world fact details."""
        lines = [
            f"World Fact: {fact.name}",
            "=" * 40,
            f"ID: {fact.id}",
            f"Type: {fact.type}",
        ]
        if fact.facts:
            lines.append("Facts:")
            for item in fact.facts:
                lines.append(f"  - {item}")
        self.update("\n".join(lines))

    def show_scene(self, scene: Scene) -> None:
        """Display scene details."""
        lines = [
            f"Scene: {scene.id}",
            "=" * 40,
            f"Summary: {scene.summary or '---'}",
            f"Goal: {scene.goal or '---'}",
            f"Conflict: {scene.conflict or '---'}",
            f"Outcome: {scene.outcome or '---'}",
            f"Location: {scene.location or '---'}",
            f"Time: {scene.time or '---'}",
        ]
        if scene.characters:
            lines.append(f"Characters: {', '.join(scene.characters)}")
        if scene.beats:
            lines.append(f"\nBeats ({len(scene.beats)}):")
            for beat in scene.beats:
                lines.append(f"  [{beat.kind}] {beat.summary or beat.id}")
        self.update("\n".join(lines))

    def show_chapter(self, chapter: Chapter) -> None:
        """Display chapter details."""
        lines = [
            f"Chapter: {chapter.title or chapter.id}",
            "=" * 40,
            f"ID: {chapter.id}",
            f"Summary: {chapter.summary or '---'}",
        ]
        if chapter.scene_ids:
            lines.append(f"\nScenes ({len(chapter.scene_ids)}):")
            for scene_id in chapter.scene_ids:
                lines.append(f"  - {scene_id}")
        self.update("\n".join(lines))

    def show_fragment(self, fragment: Fragment) -> None:
        """Display fragment details."""
        lines = [
            f"Fragment: {fragment.id}",
            "=" * 40,
            f"Content: {fragment.content}",
        ]
        if fragment.target_words:
            lines.append(f"Target Words: {fragment.target_words}")
        if fragment.notes:
            lines.append(f"Notes: {fragment.notes}")
        self.update("\n".join(lines))

    def show_stanza(self, stanza: Stanza) -> None:
        """Display stanza details."""
        lines = [
            f"Stanza: {stanza.id}",
            "=" * 40,
        ]
        if stanza.meter:
            lines.append(f"Meter: {stanza.meter}")
        if stanza.rhyme_scheme:
            lines.append(f"Rhyme Scheme: {stanza.rhyme_scheme}")
        lines.append("\nLines:")
        for line in stanza.lines:
            lines.append(f"  {line}")
        self.update("\n".join(lines))

    def show_style(self, style: Style) -> None:
        """Display style details."""
        lines = [
            "Style",
            "=" * 40,
            f"Language: {style.language or '---'}",
            f"POV: {style.pov or '---'}",
            f"Tense: {style.tense or '---'}",
            f"Voice: {style.voice or '---'}",
            f"Register: {style.register_ or '---'}",
        ]
        if style.constraints:
            lines.append("Constraints:")
            for constraint in style.constraints:
                lines.append(f"  - {constraint}")
        self.update("\n".join(lines))

    def show_entity(self, entity_type: str, entity_id: str | None, project: Project) -> None:
        """Show entity details based on type and ID."""
        if entity_type == "character" and entity_id:
            for char in project.characters:
                if char.id == entity_id:
                    self.show_character(char)
                    return

        elif entity_type == "world_fact" and entity_id:
            if project.world:
                for fact in project.world.facts:
                    if fact.id == entity_id:
                        self.show_world_fact(fact)
                        return

        elif entity_type == "scene" and entity_id:
            for scene in project.plot.scenes:
                if scene.id == entity_id:
                    self.show_scene(scene)
                    return

        elif entity_type == "chapter" and entity_id:
            for chapter in project.plot.chapters:
                if chapter.id == entity_id:
                    self.show_chapter(chapter)
                    return

        elif entity_type == "fragment" and entity_id:
            for fragment in project.plot.fragments:
                if fragment.id == entity_id:
                    self.show_fragment(fragment)
                    return

        elif entity_type == "stanza" and entity_id:
            for stanza in project.plot.stanzas:
                if stanza.id == entity_id:
                    self.show_stanza(stanza)
                    return

        elif entity_type == "style" and project.style:
            self.show_style(project.style)
            return

        self.update("Select an entity from the tree to view details.")
