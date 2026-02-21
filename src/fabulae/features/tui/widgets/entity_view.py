"""Entity detail view for the Fabulae TUI."""

from __future__ import annotations

from textual.widgets import Markdown

from fabulae.models import Beat, Chapter, Character, Fragment, Scene, Stanza, Style, WorldFact


class EntityView(Markdown):
    """Displays formatted details of a selected entity."""

    def show_message(self, message: str) -> None:
        self.update(message)

    def show_character(self, character: Character) -> None:
        content = f"""
## {character.name}

**Role:** {character.role or "—"}

**Desire:** {character.desire or "—"}

**Need:** {character.need or "—"}

**Flaw:** {character.flaw or "—"}

**Secret:** {character.secret or "—"}

**Traits:** {", ".join(character.traits) if character.traits else "—"}
"""
        self.update(content)

    def show_world_fact(self, fact: WorldFact) -> None:
        content = f"""
## {fact.name}

**Type:** {fact.type}

**Facts:**
{_format_list(fact.facts)}
"""
        self.update(content)

    def show_scene(self, scene: Scene) -> None:
        beats_text = "\n".join(f"- {beat.summary or beat.id}" for beat in scene.beats)
        content = f"""
## {scene.id}

**Summary:** {scene.summary or "—"}

**Location:** {scene.location or "—"}

**Time:** {scene.time or "—"}

**Characters:** {", ".join(scene.characters) if scene.characters else "—"}

**World facts:** {", ".join(scene.world_fact_ids) if scene.world_fact_ids else "—"}

**Beats:**
{beats_text or "No beats defined"}
"""
        self.update(content)

    def show_beat(self, beat: Beat) -> None:
        content = f"""
## {beat.id}

**Kind:** {beat.kind}

**Summary:** {beat.summary or "—"}

**Goal:** {beat.goal or "—"}

**Conflict:** {beat.conflict or "—"}

**Outcome:** {beat.outcome or "—"}

**Pace:** {beat.pace or "—"}

**Constraints:** {", ".join(beat.constraints) if beat.constraints else "—"}
"""
        self.update(content)

    def show_chapter(self, chapter: Chapter) -> None:
        scenes = ", ".join(chapter.scene_ids or []) or "—"
        content = f"""
## {chapter.title or chapter.id}

**Summary:** {chapter.summary or "—"}

**Scene IDs:** {scenes}
"""
        self.update(content)

    def show_fragment(self, fragment: Fragment) -> None:
        content = f"""
## {fragment.id}

**Content:**
{fragment.content}

**Target words:** {fragment.target_words or "—"}

**Notes:** {fragment.notes or "—"}
"""
        self.update(content)

    def show_stanza(self, stanza: Stanza) -> None:
        content = "\n".join(stanza.lines) if stanza.lines else "—"
        markdown = f"""
## {stanza.id}

**Lines:**
{content}

**Meter:** {stanza.meter or "—"}

**Rhyme scheme:** {stanza.rhyme_scheme or "—"}
"""
        self.update(markdown)

    def show_style(self, style: Style | None) -> None:
        if style is None:
            self.update("No style defined.")
            return
        content = f"""
## Style

**Language:** {style.language or "—"}

**POV:** {style.pov or "—"}

**Tense:** {style.tense or "—"}

**Voice:** {style.voice or "—"}

**Register:** {style.register_ or "—"}

**Constraints:** {", ".join(style.constraints) if style.constraints else "—"}
"""
        self.update(content)


def _format_list(items: list[str]) -> str:
    if not items:
        return "—"
    return "\n".join(f"- {item}" for item in items)
