"""Service layer for create-from-idea project generation."""

from __future__ import annotations

import asyncio
import math
import random
import re
import unicodedata
from collections.abc import Callable
from pathlib import Path
from typing import TypeVar, cast

from pydantic import ValidationError

from fabulae import __version__
from fabulae.features.create.prompts import (
    build_character_plan_prompt,
    build_character_prompt,
    build_fragment_plan_prompt,
    build_fragment_prompt,
    build_narrative_patterns_prompt,
    build_plot_outline_prompt,
    build_plot_pattern_assignment_prompt,
    build_plot_patterns_prompt,
    build_poem_plan_prompt,
    build_scene_prompt,
    build_stanza_prompt,
    build_style_prompt,
    build_world_fact_prompt,
    build_world_plan_prompt,
)
from fabulae.features.create.schemas import (
    BeatTemplateItem,
    CharacterOutput,
    CharacterPlanOutput,
    CreateOptions,
    FragmentOutput,
    FragmentPlanOutput,
    NarrativePatternsOutput,
    OutlineSceneOutput,
    PlotOutlineOutput,
    PlotPatternAssignmentOutput,
    PlotPatternsOutput,
    PoemPlanOutput,
    SceneBeatTemplate,
    SceneOutput,
    StanzaOutput,
    StanzaPlanItem,
    StyleOutput,
    WorldFactOutput,
    WorldPlanOutput,
)
from fabulae.llm import LLMConfig, create_agent
from fabulae.llm.language_guard import (
    LanguageGuardConfig,
    detect_language,
    run_with_language_guard,
)
from fabulae.models import (
    AVAILABLE_FORMATS,
    Character,
    CharactersFile,
    Fragment,
    LiteratureFormat,
    NarrativePattern,
    Plot,
    PlotPattern,
    Project,
    ProjectConfig,
    ProjectDefaults,
    ProjectPaths,
    Scene,
    Stanza,
    Style,
    World,
    WorldFact,
    _dump_plot,
    _validate_project,
    save_yaml_file,
)
from fabulae.prompts import build_language_guard_prompt, format_project_context

T = TypeVar("T")

FORMAT_COUNT_RANGES: dict[LiteratureFormat, dict[str, tuple[int, int]]] = {
    "novel": {
        "chapters": (12, 30),
        "scenes": (36, 90),
        "beats": (180, 360),
        "characters": (6, 12),
        "world_facts": (10, 20),
        "plot_patterns": (1, 2),
        "narrative_patterns": (0, 1),
    },
    "novella": {
        "chapters": (6, 16),
        "scenes": (18, 48),
        "beats": (72, 192),
        "characters": (4, 8),
        "world_facts": (6, 12),
        "plot_patterns": (1, 2),
        "narrative_patterns": (0, 1),
    },
    "short-story": {
        "chapters": (0, 6),
        "scenes": (2, 8),
        "beats": (6, 24),
        "characters": (2, 5),
        "world_facts": (2, 6),
        "plot_patterns": (1, 1),
        "narrative_patterns": (0, 1),
    },
    "micro-prose": {
        "fragments": (1, 5),
        "characters": (0, 2),
        "world_facts": (0, 3),
    },
    "poem": {
        "stanzas": (1, 6),
        "lines": (3, 18),
        "characters": (0, 2),
        "world_facts": (0, 3),
    },
}

FORMAT_BEATS_PER_SCENE: dict[LiteratureFormat, tuple[int, int]] = {
    "novel": (3, 6),
    "novella": (2, 5),
    "short-story": (2, 4),
    "micro-prose": (0, 0),
    "poem": (0, 0),
}

DEFAULT_FILLER_BEAT_KINDS = (
    "bridge",
    "complication",
    "reaction",
    "escalation",
    "turn",
    "setup",
)

_ROLE_REF_RE = re.compile(r"\brole:([a-z0-9]+(?:-[a-z0-9]+)*)\b")


class CreateProjectError(RuntimeError):
    """Raised when create-from-idea generation fails."""


def _build_user_prompt(idea: str, format_name: LiteratureFormat, context: dict[str, object] | None = None) -> str:
    sections: dict[str, object] = {"Idea": idea.strip(), "Format": format_name}
    if context:
        sections.update(context)
    return format_project_context(sections)


def _resolve_language(
    idea: str,
    override: str | None,
    config: LanguageGuardConfig,
) -> str | None:
    if override:
        return override.strip().lower()
    detected, confidence = detect_language(idea)
    if detected and confidence is not None and confidence >= config.min_confidence:
        return detected
    return None


def _rng(seed: int | None) -> random.Random:
    return random.Random(seed)


def _count_range(format_name: LiteratureFormat, key: str) -> tuple[int, int]:
    return FORMAT_COUNT_RANGES[format_name][key]


def _soft_count_warning(label: str, count: int, count_range: tuple[int, int]) -> str | None:
    min_count, max_count = count_range
    min_allowed = 0 if min_count == 0 else max(1, math.floor(min_count * 0.5))
    max_allowed = max_count if max_count == 0 else math.ceil(max_count * 1.5)
    if count < min_allowed or count > max_allowed:
        return (
            f"{label} count {count} is outside the soft range {min_allowed}-{max_allowed} "
            f"(target {min_count}-{max_count})."
        )
    return None


def _random_partition(total: int, slots: int, rng: random.Random) -> list[int]:
    if slots <= 0:
        return []
    if total <= 0:
        return [0] * slots
    if slots == 1:
        return [total]
    cuts = sorted(rng.sample(range(1, total + slots), slots - 1))
    counts: list[int] = []
    prev = 0
    for cut in cuts:
        counts.append(cut - prev - 1)
        prev = cut
    counts.append(total + slots - prev - 1)
    return counts


def _validate_style_output(expected_language: str | None) -> Callable[[StyleOutput], str | None]:
    def _validator(output: StyleOutput) -> str | None:
        try:
            Style.model_validate(output.model_dump(exclude_none=True, by_alias=True))
        except ValidationError as exc:
            return f"Style validation error: {exc}"
        if expected_language:
            if not output.language:
                return f"Style language is missing. Expected {expected_language!r}."
            if output.language.lower() != expected_language:
                return f"Style language {output.language!r} does not match {expected_language!r}."
        return None

    return _validator


def _validate_character_plan_output(output: CharacterPlanOutput) -> str | None:
    seen: set[str] = set()
    for character in output.characters:
        if character.id in seen:
            return f"Duplicate character ID: {character.id!r}."
        seen.add(character.id)
        if not character.name:
            return f"Character {character.id!r} is missing a name."
    return None


def _validate_character_output(
    output: CharacterOutput,
    expected_id: str,
    existing_ids: set[str],
) -> str | None:
    if output.id != expected_id:
        return f"Character ID {output.id!r} does not match expected {expected_id!r}."
    if output.id in existing_ids:
        return f"Duplicate character ID: {output.id!r}."
    try:
        Character.model_validate(output.model_dump(exclude_none=True))
    except ValidationError as exc:
        return f"Character validation error: {exc}"
    return None


def _validate_world_plan_output(output: WorldPlanOutput) -> str | None:
    seen: set[str] = set()
    for fact in output.facts:
        if fact.id in seen:
            return f"Duplicate world fact ID: {fact.id!r}."
        seen.add(fact.id)
        if not fact.name:
            return f"World fact {fact.id!r} is missing a name."
    return None


def _validate_world_fact_output(
    output: WorldFactOutput,
    expected_id: str,
    existing_ids: set[str],
) -> str | None:
    if output.id != expected_id:
        return f"World fact ID {output.id!r} does not match expected {expected_id!r}."
    if output.id in existing_ids:
        return f"Duplicate world fact ID: {output.id!r}."
    try:
        WorldFact.model_validate(output.model_dump(exclude_none=True))
    except ValidationError as exc:
        return f"World fact validation error: {exc}"
    return None


def _validate_plot_outline_output(
    output: PlotOutlineOutput,
) -> str | None:
    chapter_ids = {chapter.id for chapter in output.chapters}
    scene_ids = {scene.id for scene in output.scenes}
    if len(scene_ids) != len(output.scenes):
        return "Scene IDs must be unique."
    if len(chapter_ids) != len(output.chapters):
        return "Chapter IDs must be unique."

    if output.chapters:
        for scene in output.scenes:
            if scene.chapter is None:
                return f"Scene {scene.id!r} must reference a chapter when chapters exist."
            if scene.chapter not in chapter_ids:
                return f"Scene {scene.id!r} references unknown chapter {scene.chapter!r}."
        for chapter in output.chapters:
            if chapter.scene_ids is None:
                continue
            if len(set(chapter.scene_ids)) != len(chapter.scene_ids):
                return f"Chapter {chapter.id!r} has duplicate scene IDs."
            missing = {scene.id for scene in output.scenes if scene.chapter == chapter.id} - set(
                chapter.scene_ids
            )
            extra = set(chapter.scene_ids) - {scene.id for scene in output.scenes if scene.chapter == chapter.id}
            if extra:
                return f"Chapter {chapter.id!r} references unknown scenes: {sorted(extra)!r}."
            if missing:
                return f"Chapter {chapter.id!r} does not list all scenes: {sorted(missing)!r}."
        if output.scene_ids is not None:
            return "scene_ids must be null when chapters are present."
    else:
        if any(scene.chapter is not None for scene in output.scenes):
            return "Scenes must not reference chapters when no chapters exist."
        if output.scene_ids is not None:
            if len(set(output.scene_ids)) != len(output.scene_ids):
                return "scene_ids contains duplicate IDs."
            missing = scene_ids - set(output.scene_ids)
            if missing:
                return f"scene_ids does not list all scenes: {sorted(missing)!r}."
            extra = set(output.scene_ids) - scene_ids
            if extra:
                return f"scene_ids references unknown scenes: {sorted(extra)!r}."
    return None


def _validate_plot_patterns_output(
    output: PlotPatternsOutput,
    count_range: tuple[int, int],
) -> str | None:
    if not output.plot_patterns and count_range[0] > 0:
        return "Plot patterns are missing."
    seen: set[str] = set()
    for pattern in output.plot_patterns:
        if pattern.id in seen:
            return f"Duplicate plot pattern ID: {pattern.id!r}."
        seen.add(pattern.id)
        if not pattern.name:
            return f"Plot pattern {pattern.id!r} is missing a name."
        if not pattern.description:
            return f"Plot pattern {pattern.id!r} is missing a description."
        role_ids = {role.id for role in pattern.roles}
        if len(role_ids) != len(pattern.roles):
            return f"Plot pattern {pattern.id!r} has duplicate role IDs."
        beat_types = {beat.type for beat in pattern.required_beats}
        if len(beat_types) != len(pattern.required_beats):
            return f"Plot pattern {pattern.id!r} has duplicate beat types."
        if not pattern.required_beats:
            return f"Plot pattern {pattern.id!r} must define at least one required beat."
    return None


def _validate_plot_pattern_consistency(output: PlotPatternsOutput) -> str | None:
    for pattern in output.plot_patterns:
        role_ids = {role.id for role in pattern.roles}
        seen_descriptions: set[str] = set()
        for beat in pattern.required_beats:
            description = (beat.description or "").strip()
            if not description:
                return f"Plot pattern {pattern.id!r} beat {beat.type!r} is missing a description."
            normalized = description.lower()
            if normalized in seen_descriptions:
                return f"Plot pattern {pattern.id!r} has duplicate beat descriptions."
            seen_descriptions.add(normalized)
            referenced_roles = set(_ROLE_REF_RE.findall(description))
            unknown_roles = sorted(role for role in referenced_roles if role not in role_ids)
            if unknown_roles:
                return (
                    f"Plot pattern {pattern.id!r} beat {beat.type!r} references unknown role IDs: "
                    f"{unknown_roles!r}."
                )
    return None


def _validate_narrative_patterns_output(
    output: NarrativePatternsOutput,
    count_range: tuple[int, int],
    available_plot_patterns: set[str],
) -> str | None:
    if not output.narrative_patterns and count_range[0] > 0:
        return "Narrative patterns are missing."
    seen: set[str] = set()
    for pattern in output.narrative_patterns:
        if pattern.id in seen:
            return f"Duplicate narrative pattern ID: {pattern.id!r}."
        seen.add(pattern.id)
        if pattern.id in available_plot_patterns:
            return (
                f"Narrative pattern ID {pattern.id!r} conflicts with a plot pattern ID."
            )
        if not pattern.name:
            return f"Narrative pattern {pattern.id!r} is missing a name."
        if not pattern.description:
            return f"Narrative pattern {pattern.id!r} is missing a description."
        if pattern.plot_pattern and pattern.plot_pattern not in available_plot_patterns:
            return (
                f"Narrative pattern {pattern.id!r} references unknown plot pattern "
                f"{pattern.plot_pattern!r}."
            )
        role_ids = {role.id for role in pattern.roles}
        if len(role_ids) != len(pattern.roles):
            return f"Narrative pattern {pattern.id!r} has duplicate role IDs."
    return None


def _validate_plot_pattern_assignment_output(
    output: PlotPatternAssignmentOutput,
    available_plot_patterns: dict[str, PlotPattern],
    scene_ids: set[str],
    scene_beat_counts: dict[str, int] | None = None,
) -> str | None:
    if output.plot_pattern is None:
        if available_plot_patterns:
            return "plot_pattern is required when plot patterns are provided."
        if output.plot_pattern_beats:
            return "plot_pattern_beats requires plot_pattern to be set."
        return None
    if output.plot_pattern not in available_plot_patterns:
        return f"Plot pattern {output.plot_pattern!r} is not in the available plot patterns."
    required_beats = {beat.type for beat in available_plot_patterns[output.plot_pattern].required_beats}
    assigned_beats = {beat.type for beat in output.plot_pattern_beats}
    if len(assigned_beats) != len(output.plot_pattern_beats):
        return "plot_pattern_beats contains duplicate beat types."
    missing = required_beats - assigned_beats
    if missing:
        return f"plot_pattern_beats is missing required beats: {sorted(missing)!r}."
    unknown = assigned_beats - required_beats
    if unknown:
        return f"plot_pattern_beats references unknown beat types: {sorted(unknown)!r}."
    for beat in output.plot_pattern_beats:
        if beat.scene not in scene_ids:
            return f"plot_pattern_beats references unknown scene {beat.scene!r}."
    if scene_beat_counts:
        total_capacity = sum(scene_beat_counts.values())
        if len(required_beats) > total_capacity:
            return (
                "plot_pattern_beats has more required beats than total available beats "
                f"({len(required_beats)} > {total_capacity})."
            )
        assigned_per_scene: dict[str, int] = {}
        for beat in output.plot_pattern_beats:
            assigned_per_scene[beat.scene] = assigned_per_scene.get(beat.scene, 0) + 1
        for scene_id, count in assigned_per_scene.items():
            beat_count = scene_beat_counts.get(scene_id)
            if beat_count is not None and count > beat_count:
                return f"plot_pattern_beats assigns {count} beats to {scene_id!r} with beat_count {beat_count}."
    return None


def _validate_scene_output(
    output: SceneOutput,
    expected_scene: OutlineSceneOutput,
    available_characters: set[str],
    available_world_facts: set[str],
    beats_per_scene: tuple[int, int],
) -> str | None:
    if output.id != expected_scene.id:
        return f"Scene ID {output.id!r} does not match expected {expected_scene.id!r}."
    if expected_scene.chapter and output.chapter != expected_scene.chapter:
        return f"Scene {output.id!r} chapter {output.chapter!r} does not match expected {expected_scene.chapter!r}."
    if len(output.beats) != expected_scene.beat_count:
        return (
            f"Scene {output.id!r} must have {expected_scene.beat_count} beats, got {len(output.beats)}."
        )
    if len(output.beats) < beats_per_scene[0] or len(output.beats) > beats_per_scene[1]:
        return (
            f"Scene {output.id!r} beat count {len(output.beats)} is outside "
            f"{beats_per_scene[0]}-{beats_per_scene[1]}."
        )
    if output.characters:
        missing = set(output.characters) - available_characters
        if missing:
            return f"Scene {output.id!r} references unknown characters: {sorted(missing)!r}."
    if output.location and output.location not in available_world_facts:
        return f"Scene {output.id!r} references unknown location {output.location!r}."
    if output.world_fact_ids:
        missing = set(output.world_fact_ids) - available_world_facts
        if missing:
            return f"Scene {output.id!r} references unknown world facts: {sorted(missing)!r}."
    try:
        Scene.model_validate(output.model_dump(exclude_none=True))
    except ValidationError as exc:
        return f"Scene validation error: {exc}"
    return None


def _validate_fragment_plan_output(output: FragmentPlanOutput) -> str | None:
    if not output.premise:
        return "Fragment plan is missing a premise."
    seen: set[str] = set()
    for fragment in output.fragments:
        if fragment.id in seen:
            return f"Duplicate fragment ID: {fragment.id!r}."
        seen.add(fragment.id)
    return None


def _validate_fragment_output(
    output: FragmentOutput,
    expected_id: str,
    existing_ids: set[str],
) -> str | None:
    if output.id != expected_id:
        return f"Fragment ID {output.id!r} does not match expected {expected_id!r}."
    if output.id in existing_ids:
        return f"Duplicate fragment ID: {output.id!r}."
    try:
        Fragment.model_validate(output.model_dump(exclude_none=True))
    except ValidationError as exc:
        return f"Fragment validation error: {exc}"
    return None


def _validate_poem_plan_output(
    output: PoemPlanOutput,
) -> str | None:
    if not output.premise:
        return "Poem plan is missing a premise."
    seen: set[str] = set()
    for stanza in output.stanzas:
        if stanza.id in seen:
            return f"Duplicate stanza ID: {stanza.id!r}."
        seen.add(stanza.id)
    return None


def _validate_stanza_output(
    output: StanzaOutput,
    expected_id: str,
    expected_line_count: int,
    existing_ids: set[str],
) -> str | None:
    if output.id != expected_id:
        return f"Stanza ID {output.id!r} does not match expected {expected_id!r}."
    if output.id in existing_ids:
        return f"Duplicate stanza ID: {output.id!r}."
    if len(output.lines) != expected_line_count:
        return (
            f"Stanza {output.id!r} must have {expected_line_count} lines, got {len(output.lines)}."
        )
    try:
        Stanza.model_validate(output.model_dump(exclude_none=True))
    except ValidationError as exc:
        return f"Stanza validation error: {exc}"
    return None

def _normalize_id(value: str) -> str:
    cleaned = value.strip().lower()
    replacements = {
        "ä": "ae",
        "ö": "oe",
        "ü": "ue",
        "ß": "ss",
        "æ": "ae",
        "ø": "o",
        "å": "a",
    }
    for source, target in replacements.items():
        cleaned = cleaned.replace(source, target)
    cleaned = unicodedata.normalize("NFKD", cleaned).encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"[^a-z0-9]+", "-", cleaned)
    cleaned = cleaned.strip("-")
    if not cleaned:
        raise ValueError(f"Unable to normalize ID: {value!r}")
    return cleaned


def _normalize_id_list(values: list[str]) -> list[str]:
    return [_normalize_id(value) for value in values]


def _normalize_character_plan_output(output: CharacterPlanOutput) -> CharacterPlanOutput:
    normalized = []
    for character in output.characters:
        normalized.append(character.model_copy(update={"id": _normalize_id(character.id)}))
    return output.model_copy(update={"characters": normalized})


def _normalize_character_output(output: CharacterOutput) -> CharacterOutput:
    return output.model_copy(update={"id": _normalize_id(output.id)})


def _normalize_world_plan_output(output: WorldPlanOutput) -> WorldPlanOutput:
    normalized_facts = []
    for fact in output.facts:
        normalized_facts.append(fact.model_copy(update={"id": _normalize_id(fact.id)}))
    return output.model_copy(update={"facts": normalized_facts})


def _normalize_world_fact_output(output: WorldFactOutput) -> WorldFactOutput:
    return output.model_copy(update={"id": _normalize_id(output.id)})


def _normalize_plot_outline_output(output: PlotOutlineOutput) -> PlotOutlineOutput:
    normalized_chapters = []
    for chapter in output.chapters:
        chapter_update: dict[str, object] = {"id": _normalize_id(chapter.id)}
        if chapter.scene_ids is not None:
            chapter_update["scene_ids"] = _normalize_id_list(chapter.scene_ids)
        normalized_chapters.append(chapter.model_copy(update=chapter_update))

    normalized_scenes = []
    for scene in output.scenes:
        scene_update: dict[str, object] = {"id": _normalize_id(scene.id)}
        if scene.chapter:
            scene_update["chapter"] = _normalize_id(scene.chapter)
        normalized_scenes.append(scene.model_copy(update=scene_update))

    update: dict[str, object] = {
        "chapters": normalized_chapters,
        "scenes": normalized_scenes,
    }
    if output.scene_ids is not None:
        update["scene_ids"] = _normalize_id_list(output.scene_ids)
    return output.model_copy(update=update)


def _normalize_scene_output(output: SceneOutput) -> SceneOutput:
    update: dict[str, object] = {"id": _normalize_id(output.id)}
    if output.chapter:
        update["chapter"] = _normalize_id(output.chapter)
    if output.location:
        update["location"] = _normalize_id(output.location)
    if output.plot_pattern:
        update["plot_pattern"] = _normalize_id(output.plot_pattern)
    if output.plot_pattern_beat:
        update["plot_pattern_beat"] = _normalize_id(output.plot_pattern_beat)
    if output.characters:
        update["characters"] = _normalize_id_list(output.characters)
    if output.world_fact_ids:
        update["world_fact_ids"] = _normalize_id_list(output.world_fact_ids)
    normalized_beats = []
    for beat in output.beats:
        normalized_beats.append(
            beat.model_copy(
                update={
                    "id": _normalize_id(beat.id),
                    "kind": _normalize_id(beat.kind),
                }
            )
        )
    update["beats"] = normalized_beats
    return output.model_copy(update=update)


def _normalize_fragment_plan_output(output: FragmentPlanOutput) -> FragmentPlanOutput:
    normalized = []
    for fragment in output.fragments:
        normalized.append(fragment.model_copy(update={"id": _normalize_id(fragment.id)}))
    return output.model_copy(update={"fragments": normalized})


def _normalize_fragment_output(output: FragmentOutput) -> FragmentOutput:
    return output.model_copy(update={"id": _normalize_id(output.id)})


def _normalize_poem_plan_output(output: PoemPlanOutput) -> PoemPlanOutput:
    normalized = []
    for stanza in output.stanzas:
        normalized.append(stanza.model_copy(update={"id": _normalize_id(stanza.id)}))
    return output.model_copy(update={"stanzas": normalized})


def _normalize_stanza_output(output: StanzaOutput) -> StanzaOutput:
    return output.model_copy(update={"id": _normalize_id(output.id)})


def _normalize_plot_patterns_output(output: PlotPatternsOutput) -> PlotPatternsOutput:
    normalized_patterns = []
    for pattern in output.plot_patterns:
        role_updates = []
        for role in pattern.roles:
            role_updates.append(role.model_copy(update={"id": _normalize_id(role.id)}))
        beat_updates = []
        for beat in pattern.required_beats:
            beat_updates.append(beat.model_copy(update={"type": _normalize_id(beat.type)}))
        normalized_patterns.append(
            pattern.model_copy(
                update={
                    "id": _normalize_id(pattern.id),
                    "roles": role_updates,
                    "required_beats": beat_updates,
                }
            )
        )
    return output.model_copy(update={"plot_patterns": normalized_patterns})


def _normalize_narrative_patterns_output(output: NarrativePatternsOutput) -> NarrativePatternsOutput:
    normalized_patterns = []
    for pattern in output.narrative_patterns:
        role_updates = []
        for role in pattern.roles:
            role_updates.append(role.model_copy(update={"id": _normalize_id(role.id)}))
        updates: dict[str, object] = {
            "id": _normalize_id(pattern.id),
            "roles": role_updates,
        }
        if pattern.plot_pattern:
            updates["plot_pattern"] = _normalize_id(pattern.plot_pattern)
        normalized_patterns.append(pattern.model_copy(update=updates))
    return output.model_copy(update={"narrative_patterns": normalized_patterns})


def _normalize_plot_pattern_assignment_output(
    output: PlotPatternAssignmentOutput,
) -> PlotPatternAssignmentOutput:
    updates: dict[str, object] = {}
    if output.plot_pattern:
        updates["plot_pattern"] = _normalize_id(output.plot_pattern)
    normalized_beats = []
    for beat in output.plot_pattern_beats:
        normalized_beats.append(
            beat.model_copy(
                update={
                    "type": _normalize_id(beat.type),
                    "scene": _normalize_id(beat.scene),
                    "scene_beat": None,
                }
            )
        )
    if output.plot_pattern is None:
        normalized_beats = []
    updates["plot_pattern_beats"] = normalized_beats
    return output.model_copy(update=updates)


def _build_scene_beat_templates(
    plot_outline: PlotOutlineOutput,
    plot_patterns: list[PlotPattern],
    assignment: PlotPatternAssignmentOutput,
    rng: random.Random,
    randomize: bool,
) -> dict[str, SceneBeatTemplate]:
    if not assignment.plot_pattern:
        return {}
    pattern = next((pattern for pattern in plot_patterns if pattern.id == assignment.plot_pattern), None)
    if pattern is None:
        return {}
    required_order = [beat.type for beat in pattern.required_beats]
    assignment_map = {beat.type: beat.scene for beat in assignment.plot_pattern_beats}
    templates: dict[str, SceneBeatTemplate] = {}
    for scene in plot_outline.scenes:
        required_beats = [beat_type for beat_type in required_order if assignment_map.get(beat_type) == scene.id]
        remaining = max(scene.beat_count - len(required_beats), 0)
        gaps = len(required_beats) + 1
        if randomize:
            filler_counts = _random_partition(remaining, gaps, rng)
        else:
            filler_counts = [0] * gaps
            filler_counts[-1] = remaining
        beats: list[BeatTemplateItem] = []
        for gap_index, filler_count in enumerate(filler_counts):
            for _ in range(filler_count):
                filler_kind = rng.choice(DEFAULT_FILLER_BEAT_KINDS) if randomize else DEFAULT_FILLER_BEAT_KINDS[0]
                beats.append(BeatTemplateItem(kind=filler_kind, required=False, notes="filler"))
            if gap_index < len(required_beats):
                beat_kind = required_beats[gap_index]
                beats.append(BeatTemplateItem(kind=beat_kind, required=True, plot_pattern_beat=beat_kind))
        templates[scene.id] = SceneBeatTemplate(scene_id=scene.id, beat_count=scene.beat_count, beats=beats)
    return templates


def _order_plot_pattern_assignments(
    assignment: PlotPatternAssignmentOutput,
    plot_patterns: list[PlotPattern],
) -> PlotPatternAssignmentOutput:
    if not assignment.plot_pattern:
        return assignment
    pattern = next((pattern for pattern in plot_patterns if pattern.id == assignment.plot_pattern), None)
    if pattern is None:
        return assignment
    assignment_map = {beat.type: beat for beat in assignment.plot_pattern_beats}
    ordered_beats = [assignment_map[beat.type] for beat in pattern.required_beats if beat.type in assignment_map]
    return assignment.model_copy(update={"plot_pattern_beats": ordered_beats})


def _validate_scene_template(output: SceneOutput, template: SceneBeatTemplate | None) -> str | None:
    if template is None:
        return None
    if len(template.beats) != template.beat_count:
        return f"Scene {output.id!r} beat template length does not match beat_count."
    if len(output.beats) != template.beat_count:
        return f"Scene {output.id!r} must have {template.beat_count} beats, got {len(output.beats)}."
    for index, template_item in enumerate(template.beats):
        if not template_item.required:
            continue
        expected_kind = _normalize_id(template_item.kind)
        actual_kind = _normalize_id(output.beats[index].kind)
        if actual_kind != expected_kind:
            return (
                f"Scene {output.id!r} beat {index + 1} should be kind {expected_kind!r}, "
                f"got {actual_kind!r}."
            )
    return None



def _write_config(config: ProjectConfig, output_dir: Path) -> None:
    save_yaml_file(output_dir / "fabulae.yml", config.model_dump(exclude_none=True))


def _artifact_root(output_dir: Path) -> Path:
    return output_dir / ".fabulae-create"


def _write_artifact(output_dir: Path, name: str, payload: dict[str, object]) -> None:
    artifact_path = _artifact_root(output_dir) / name
    save_yaml_file(artifact_path, payload)


def _write_style(style: Style | None, config: ProjectConfig, output_dir: Path) -> None:
    if style is None:
        return
    paths = config.paths or ProjectPaths()
    save_yaml_file(output_dir / paths.style, style.model_dump(exclude_none=True, by_alias=True))


def _write_characters(characters: list[Character], config: ProjectConfig, output_dir: Path) -> None:
    paths = config.paths or ProjectPaths()
    save_yaml_file(
        output_dir / paths.characters,
        CharactersFile(characters=characters).model_dump(exclude_none=True),
    )


def _write_world(world: World | None, config: ProjectConfig, output_dir: Path) -> None:
    if world is None:
        return
    paths = config.paths or ProjectPaths()
    save_yaml_file(output_dir / paths.world, world.model_dump(exclude_none=True))


def _write_plot(plot: Plot, config: ProjectConfig, output_dir: Path) -> None:
    paths = config.paths or ProjectPaths()
    save_yaml_file(output_dir / paths.plot, _dump_plot(plot))


def _write_plot_patterns(
    plot_patterns: list[PlotPattern],
    config: ProjectConfig,
    output_dir: Path,
) -> None:
    if not plot_patterns:
        return
    paths = config.paths or ProjectPaths()
    save_yaml_file(
        output_dir / paths.plot_patterns,
        {"plot_patterns": [pattern.model_dump(exclude_none=True) for pattern in plot_patterns]},
    )


def _write_narrative_patterns(
    narrative_patterns: list[NarrativePattern],
    config: ProjectConfig,
    output_dir: Path,
) -> None:
    if not narrative_patterns:
        return
    paths = config.paths or ProjectPaths()
    save_yaml_file(
        output_dir / paths.narrative_patterns,
        {"narrative_patterns": [pattern.model_dump(exclude_none=True) for pattern in narrative_patterns]},
    )


def _style_hint(style: StyleOutput) -> str:
    parts = []
    if style.pov:
        parts.append(f"POV: {style.pov}")
    if style.tense:
        parts.append(f"Tense: {style.tense}")
    if style.voice:
        parts.append(f"Voice: {style.voice}")
    if style.register_:
        parts.append(f"Register: {style.register_}")
    if style.language:
        parts.append(f"Language: {style.language}")
    return "; ".join(parts)


def _summarize_characters(characters: list[Character]) -> str:
    lines = []
    for character in characters:
        role = f" ({character.role})" if character.role else ""
        lines.append(f"{character.id}: {character.name}{role}")
    return "\n".join(lines)


def _summarize_world_facts(facts: list[WorldFact]) -> str:
    lines = []
    for fact in facts:
        lines.append(f"{fact.id}: {fact.name} [{fact.type}]")
    return "\n".join(lines)


def _summarize_plot_patterns(patterns: list[PlotPattern]) -> str:
    lines = []
    for pattern in patterns:
        beat_types = "; ".join(
            f"{beat.type}: {beat.description}" if beat.description else beat.type for beat in pattern.required_beats
        )
        role_ids = ", ".join(role.id for role in pattern.roles)
        parts = [f"{pattern.id}: {pattern.name}", pattern.description]
        if role_ids:
            parts.append(f"roles: {role_ids}")
        if beat_types:
            parts.append(f"beats: {beat_types}")
        lines.append(" | ".join(part for part in parts if part))
    return "\n".join(lines)


def _summarize_narrative_patterns(patterns: list[NarrativePattern]) -> str:
    lines = []
    for pattern in patterns:
        parts = [f"{pattern.id}: {pattern.name}", pattern.description]
        if pattern.plot_pattern:
            parts.append(f"plot_pattern: {pattern.plot_pattern}")
        if pattern.themes:
            parts.append(f"themes: {', '.join(str(theme) for theme in pattern.themes)}")
        if pattern.motifs:
            parts.append(f"motifs: {', '.join(str(motif) for motif in pattern.motifs)}")
        lines.append(" | ".join(part for part in parts if part))
    return "\n".join(lines)


def _summarize_outline_summaries(summaries: list[str]) -> str:
    return "\n".join(summary for summary in summaries if summary)


def _summarize_fragments(fragments: list[Fragment]) -> str:
    return "\n".join(fragment.content for fragment in fragments if fragment.content)


def _summarize_stanzas(stanzas: list[Stanza]) -> str:
    lines: list[str] = []
    for stanza in stanzas:
        lines.extend(stanza.lines)
    return "\n".join(line for line in lines if line)


def _maybe_warn_range(
    progress: Callable[[str], None] | None,
    label: str,
    count: int,
    count_range: tuple[int, int],
) -> None:
    warning = _soft_count_warning(label, count, count_range)
    if warning and progress:
        progress(f"Warning: {warning}")


def _maybe_warn_pattern_conflicts(
    progress: Callable[[str], None] | None,
    selected_plot_pattern: str | None,
    narrative_patterns: list[NarrativePattern],
) -> None:
    if not progress or not selected_plot_pattern or not narrative_patterns:
        return
    conflicts = [
        pattern.id
        for pattern in narrative_patterns
        if pattern.plot_pattern and pattern.plot_pattern != selected_plot_pattern
    ]
    if conflicts:
        progress(
            "Warning: Narrative patterns reference different plot patterns than the selected plot pattern: "
            f"{sorted(conflicts)!r}."
        )


def _maybe_warn_narrative_world_conflicts(
    progress: Callable[[str], None] | None,
    narrative_patterns: list[NarrativePattern],
    world: WorldPlanOutput,
) -> None:
    if not progress or not narrative_patterns:
        return
    conflicts: list[str] = []
    for pattern in narrative_patterns:
        if pattern.setting and world.setting and pattern.setting.strip().lower() != world.setting.strip().lower():
            conflicts.append(f"{pattern.id}: setting")
        if (
            pattern.time_period
            and world.time_period
            and pattern.time_period.strip().lower() != world.time_period.strip().lower()
        ):
            conflicts.append(f"{pattern.id}: time_period")
        if pattern.tone and world.tone and pattern.tone.strip().lower() != world.tone.strip().lower():
            conflicts.append(f"{pattern.id}: tone")
    if conflicts:
        progress(
            "Warning: Narrative patterns differ from world metadata (setting/time_period/tone): "
            f"{sorted(conflicts)!r}."
        )


def _extract_text_from_style(output: StyleOutput) -> str:
    fields = [output.pov, output.tense, output.voice, output.register_]
    return "\n".join(value for value in fields if value)


def _extract_text_from_character_plan(output: CharacterPlanOutput) -> str:
    parts: list[str] = []
    for character in output.characters:
        parts.extend([character.name, character.role or "", character.purpose or ""])
    return "\n".join(part for part in parts if part)


def _extract_text_from_character(output: CharacterOutput) -> str:
    parts = [
        output.name,
        output.role or "",
        output.desire or "",
        output.need or "",
        output.flaw or "",
        output.secret or "",
        " ".join(output.traits),
    ]
    return "\n".join(part for part in parts if part)


def _extract_text_from_world_plan(output: WorldPlanOutput) -> str:
    parts: list[str] = []
    if output.setting:
        parts.append(output.setting)
    if output.time_period:
        parts.append(output.time_period)
    if output.tone:
        parts.append(output.tone)
    parts.extend(output.motifs)
    for fact in output.facts:
        parts.append(fact.name)
        if fact.purpose:
            parts.append(fact.purpose)
    return "\n".join(part for part in parts if part)


def _extract_text_from_world_fact(output: WorldFactOutput) -> str:
    parts = [output.name]
    parts.extend(output.facts)
    return "\n".join(part for part in parts if part)


def _extract_text_from_plot_patterns(output: PlotPatternsOutput) -> str:
    parts: list[str] = []
    for pattern in output.plot_patterns:
        parts.extend([pattern.name, pattern.description])
        for role in pattern.roles:
            parts.extend([role.id, role.description])
        for beat in pattern.required_beats:
            parts.extend([beat.type, beat.description])
    return "\n".join(part for part in parts if part)


def _extract_text_from_narrative_patterns(output: NarrativePatternsOutput) -> str:
    parts: list[str] = []
    for pattern in output.narrative_patterns:
        parts.extend([pattern.name, pattern.description])
        if pattern.plot_pattern:
            parts.append(pattern.plot_pattern)
        for role in pattern.roles:
            parts.extend([role.id, role.description])
        parts.extend(pattern.themes)
        parts.extend(pattern.motifs)
        if pattern.setting:
            parts.append(pattern.setting)
        if pattern.time_period:
            parts.append(pattern.time_period)
        if pattern.tone:
            parts.append(pattern.tone)
        parts.extend(pattern.notes)
    return "\n".join(part for part in parts if part)


def _extract_text_from_plot_pattern_assignment(output: PlotPatternAssignmentOutput) -> str:
    parts: list[str] = []
    if output.plot_pattern:
        parts.append(output.plot_pattern)
    for beat in output.plot_pattern_beats:
        parts.extend([beat.type, beat.scene])
    return "\n".join(part for part in parts if part)


def _extract_text_from_plot_outline(output: PlotOutlineOutput) -> str:
    parts: list[str] = [output.title or "", output.premise]
    parts.extend(output.themes)
    if output.hook:
        parts.extend([output.hook.line or "", output.hook.question or "", output.hook.promise or ""])
    if output.stakes:
        parts.extend([output.stakes.external or "", output.stakes.internal or ""])
    for chapter in output.chapters:
        parts.append(chapter.title or "")
        parts.append(chapter.summary or "")
    for scene in output.scenes:
        parts.extend([scene.summary or "", scene.goal or "", scene.conflict or "", scene.outcome or ""])
    return "\n".join(part for part in parts if part)


def _extract_text_from_scene(output: SceneOutput) -> str:
    parts: list[str] = [output.summary or "", output.goal or "", output.conflict or "", output.outcome or ""]
    for beat in output.beats:
        parts.extend([beat.summary or "", beat.goal or "", beat.conflict or "", beat.outcome or ""])
    return "\n".join(part for part in parts if part)


def _extract_text_from_fragment_plan(output: FragmentPlanOutput) -> str:
    parts: list[str] = [output.title or "", output.premise]
    parts.extend(output.themes)
    for fragment in output.fragments:
        if fragment.intent:
            parts.append(fragment.intent)
        if fragment.notes:
            parts.append(fragment.notes)
    return "\n".join(part for part in parts if part)


def _extract_text_from_fragment(output: FragmentOutput) -> str:
    parts = [output.content]
    if output.notes:
        parts.append(output.notes)
    return "\n".join(part for part in parts if part)


def _extract_text_from_poem_plan(output: PoemPlanOutput) -> str:
    parts: list[str] = [output.title or "", output.premise]
    parts.extend(output.themes)
    for stanza in output.stanzas:
        if stanza.intent:
            parts.append(stanza.intent)
    return "\n".join(part for part in parts if part)


def _extract_text_from_stanza(output: StanzaOutput) -> str:
    return "\n".join(line for line in output.lines if line)


async def _run_stage(
    result_type: type[T],
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    expected_language: str | None,
    extract_text: Callable[[T], str],
) -> T:
    prompt_state = {"system": system_prompt}
    if expected_language:
        prompt_state["system"] = f"{prompt_state['system']}\n\n{build_language_guard_prompt(expected_language)}"

    async def runner() -> T:
        agent = create_agent(result_type, prompt_state["system"], config)
        result = await agent.run(user_prompt)
        return cast(T, result.output)

    def reprompt(attempt: int) -> None:
        if not expected_language:
            return
        guard_prompt = build_language_guard_prompt(expected_language)
        prompt_state["system"] = f"{system_prompt}\n\n{guard_prompt}\n\nRetry attempt: {attempt}"

    output, _ = await run_with_language_guard(
        runner=runner,
        extract_text=extract_text,
        expected_language=expected_language,
        reprompt=reprompt,
    )
    return output


async def _run_stage_with_validation(
    *,
    result_type: type[T],
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    expected_language: str | None,
    extract_text: Callable[[T], str],
    normalize: Callable[[T], T] | None,
    validate: Callable[[T], str | None],
    max_retries: int = 2,
) -> T:
    attempt = 0
    current_prompt = user_prompt
    while True:
        error: str | None = None
        try:
            output = await _run_stage(
                result_type,
                system_prompt,
                current_prompt,
                config,
                expected_language,
                extract_text,
            )
            if normalize:
                output = normalize(output)
        except Exception as exc:
            error = f"Output error: {exc}"
        else:
            error = validate(output)
            if error is None:
                return output
        attempt += 1
        if attempt > max_retries:
            raise CreateProjectError(f"Failed to generate valid output: {error}")
        current_prompt = f"{user_prompt}\n\nFix this error:\n{error}"


async def _run_stage_with_validation_or_warn(
    *,
    result_type: type[T],
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    expected_language: str | None,
    extract_text: Callable[[T], str],
    normalize: Callable[[T], T] | None,
    validate: Callable[[T], str | None],
    warning_label: str,
    progress: Callable[[str], None] | None,
    max_retries: int = 2,
) -> T:
    attempt = 0
    current_prompt = user_prompt
    last_output: T | None = None
    last_error: str | None = None
    while True:
        error: str | None = None
        try:
            output = await _run_stage(
                result_type,
                system_prompt,
                current_prompt,
                config,
                expected_language,
                extract_text,
            )
            if normalize:
                output = normalize(output)
            last_output = output
        except Exception as exc:
            error = f"Output error: {exc}"
        else:
            error = validate(output)
            if error is None:
                return output
        last_error = error
        attempt += 1
        if attempt > max_retries:
            if progress and last_error:
                progress(
                    f"Warning: {warning_label} validation failed after {max_retries} retries: {last_error}"
                )
            if last_output is not None:
                return last_output
            raise CreateProjectError(f"Failed to generate valid output: {last_error}")
        current_prompt = f"{user_prompt}\n\nFix this error:\n{error}"


async def _run_stage_with_validation_and_warning(
    *,
    result_type: type[T],
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    expected_language: str | None,
    extract_text: Callable[[T], str],
    normalize: Callable[[T], T] | None,
    validate: Callable[[T], str | None],
    warn_validate: Callable[[T], str | None],
    warning_label: str,
    progress: Callable[[str], None] | None,
    max_retries: int = 2,
) -> T:
    attempt = 0
    current_prompt = user_prompt
    last_output: T | None = None
    while True:
        strict_error: str | None = None
        warn_error: str | None = None
        try:
            output = await _run_stage(
                result_type,
                system_prompt,
                current_prompt,
                config,
                expected_language,
                extract_text,
            )
            if normalize:
                output = normalize(output)
            last_output = output
        except Exception as exc:
            strict_error = f"Output error: {exc}"
        else:
            strict_error = validate(output)
            if strict_error is None:
                warn_error = warn_validate(output)
                if warn_error is None:
                    return output
        attempt += 1
        if attempt > max_retries:
            if strict_error is not None:
                raise CreateProjectError(f"Failed to generate valid output: {strict_error}")
            if progress and warn_error:
                progress(
                    f"Warning: {warning_label} validation failed after {max_retries} retries: {warn_error}"
                )
            if last_output is not None:
                return last_output
            raise CreateProjectError("Failed to generate valid output.")
        error = strict_error or warn_error
        current_prompt = f"{user_prompt}\n\nFix this error:\n{error}"


def _coerce_style(output: StyleOutput) -> Style | None:
    payload = output.model_dump(exclude_none=True, by_alias=True)
    if not payload:
        return None
    return Style.model_validate(payload)


def _validate_format(format_name: LiteratureFormat) -> None:
    if format_name not in AVAILABLE_FORMATS:
        available = ", ".join(AVAILABLE_FORMATS)
        raise ValueError(f"Unknown format: {format_name}. Available: {available}")


async def generate_project_from_idea(
    idea: str,
    format_name: LiteratureFormat,
    config: LLMConfig,
    output_dir: Path,
    idea_language: str | None = None,
    progress: Callable[[str], None] | None = None,
    options: CreateOptions | None = None,
) -> Project:
    """Generate a complete Fabulae project from an idea."""
    _validate_format(format_name)
    if not idea.strip():
        raise ValueError("Idea must not be empty.")
    
    if options is None:
        options = CreateOptions()

    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Write create options artifact for reproducibility
    _write_artifact(
        output_dir,
        "create_options.yml",
        {
            "narrative_patterns_mode": options.narrative_patterns_mode,
            "use_narrative_patterns_in_prompts": options.use_narrative_patterns_in_prompts,
        },
    )
    language_config = LanguageGuardConfig()
    expected_language = _resolve_language(idea, idea_language, language_config)
    config_model = ProjectConfig(
        version=__version__,
        title=None,
        paths=None,
        defaults=ProjectDefaults(language=expected_language) if expected_language else None,
    )
    _write_config(config_model, output_dir)
    rng = _rng(config.seed)

    if progress:
        progress("Generating style...")
    style_prompt = build_style_prompt(format_name)
    style_user_prompt = _build_user_prompt(idea, format_name, {"Language": expected_language or "auto-detect"})
    style_output = await _run_stage_with_validation(
        result_type=StyleOutput,
        system_prompt=style_prompt,
        user_prompt=style_user_prompt,
        config=config,
        expected_language=expected_language,
        extract_text=_extract_text_from_style,
        normalize=None,
        validate=_validate_style_output(expected_language),
    )
    if expected_language and style_output.language != expected_language:
        style_output = style_output.model_copy(update={"language": expected_language})
    style = _coerce_style(style_output)
    _write_style(style, config_model, output_dir)
    _write_artifact(output_dir, "style.yml", style_output.model_dump(exclude_none=True, by_alias=True))
    style_hint = _style_hint(style_output) if style_output else ""

    if progress:
        progress("Planning characters...")
    character_count_range = _count_range(format_name, "characters")
    characters_prompt = build_character_plan_prompt(format_name, style_hint or None, character_count_range)
    characters_user_prompt = _build_user_prompt(
        idea,
        format_name,
        {"Style": style_hint, "Count Targets": f"Characters: {character_count_range[0]}-{character_count_range[1]}"},
    )

    def validate_character_plan(output: CharacterPlanOutput) -> str | None:
        return _validate_character_plan_output(output)

    character_plan_output = await _run_stage_with_validation(
        result_type=CharacterPlanOutput,
        system_prompt=characters_prompt,
        user_prompt=characters_user_prompt,
        config=config,
        expected_language=expected_language,
        extract_text=_extract_text_from_character_plan,
        normalize=_normalize_character_plan_output,
        validate=validate_character_plan,
    )
    _maybe_warn_range(progress, "Character", len(character_plan_output.characters), character_count_range)
    _write_artifact(output_dir, "characters_plan.yml", character_plan_output.model_dump(exclude_none=True))

    if progress:
        progress("Generating characters...")
    character_outputs: dict[str, Character] = {}
    character_order = list(character_plan_output.characters)
    if config.seed is not None:
        rng.shuffle(character_order)
    for character_seed in character_order:
        existing_summary = _summarize_characters(list(character_outputs.values()))
        character_prompt = build_character_prompt(format_name, style_hint or None, existing_summary)
        character_user_prompt = _build_user_prompt(
            idea,
            format_name,
            {
                "Style": style_hint,
                "Character Seed": character_seed.model_dump(exclude_none=True),
            },
        )

        def normalize_character(output: CharacterOutput, expected_id: str = character_seed.id) -> CharacterOutput:
            normalized = _normalize_character_output(output)
            return normalized.model_copy(update={"id": expected_id})

        def validate_character(output: CharacterOutput, expected_id: str = character_seed.id) -> str | None:
            return _validate_character_output(output, expected_id, set(character_outputs))

        character_output = await _run_stage_with_validation(
            result_type=CharacterOutput,
            system_prompt=character_prompt,
            user_prompt=character_user_prompt,
            config=config,
            expected_language=expected_language,
            extract_text=_extract_text_from_character,
            normalize=normalize_character,
            validate=validate_character,
        )
        character = Character.model_validate(character_output.model_dump(exclude_none=True))
        character_outputs[character.id] = character
        _write_artifact(
            output_dir,
            f"characters/{character.id}.yml",
            character_output.model_dump(exclude_none=True),
        )
    characters = [
        character_outputs[seed.id]
        for seed in character_plan_output.characters
        if seed.id in character_outputs
    ]
    _write_characters(characters, config_model, output_dir)

    if progress:
        progress("Planning world...")
    world_count_range = _count_range(format_name, "world_facts")
    world_prompt = build_world_plan_prompt(format_name, style_hint or None, world_count_range)
    world_user_prompt = _build_user_prompt(
        idea,
        format_name,
        {
            "Style": style_hint,
            "Characters": _summarize_characters(characters),
            "Count Targets": f"World facts: {world_count_range[0]}-{world_count_range[1]}",
        },
    )

    def validate_world_plan(output: WorldPlanOutput) -> str | None:
        return _validate_world_plan_output(output)

    world_plan_output = await _run_stage_with_validation(
        result_type=WorldPlanOutput,
        system_prompt=world_prompt,
        user_prompt=world_user_prompt,
        config=config,
        expected_language=expected_language,
        extract_text=_extract_text_from_world_plan,
        normalize=_normalize_world_plan_output,
        validate=validate_world_plan,
    )
    _maybe_warn_range(progress, "World fact", len(world_plan_output.facts), world_count_range)
    _write_artifact(output_dir, "world_plan.yml", world_plan_output.model_dump(exclude_none=True))

    if progress:
        progress("Generating world facts...")
    world_fact_outputs: dict[str, WorldFact] = {}
    world_fact_order = list(world_plan_output.facts)
    if config.seed is not None:
        rng.shuffle(world_fact_order)
    for fact_seed in world_fact_order:
        existing_summary = _summarize_world_facts(list(world_fact_outputs.values()))
        world_fact_prompt = build_world_fact_prompt(format_name, style_hint or None, existing_summary)
        world_fact_user_prompt = _build_user_prompt(
            idea,
            format_name,
            {
                "Style": style_hint,
                "World Fact Seed": fact_seed.model_dump(exclude_none=True),
                "World Overview": {
                    "setting": world_plan_output.setting,
                    "time_period": world_plan_output.time_period,
                    "tone": world_plan_output.tone,
                    "motifs": world_plan_output.motifs,
                },
            },
        )

        def normalize_world_fact(output: WorldFactOutput, expected_id: str = fact_seed.id) -> WorldFactOutput:
            normalized = _normalize_world_fact_output(output)
            return normalized.model_copy(update={"id": expected_id})

        def validate_world_fact(output: WorldFactOutput, expected_id: str = fact_seed.id) -> str | None:
            return _validate_world_fact_output(output, expected_id, set(world_fact_outputs))

        fact_output = await _run_stage_with_validation(
            result_type=WorldFactOutput,
            system_prompt=world_fact_prompt,
            user_prompt=world_fact_user_prompt,
            config=config,
            expected_language=expected_language,
            extract_text=_extract_text_from_world_fact,
            normalize=normalize_world_fact,
            validate=validate_world_fact,
        )
        fact = WorldFact.model_validate(fact_output.model_dump(exclude_none=True))
        world_fact_outputs[fact.id] = fact
        _write_artifact(
            output_dir,
            f"world/{fact.id}.yml",
            fact_output.model_dump(exclude_none=True),
        )
    world_facts = [
        world_fact_outputs[seed.id]
        for seed in world_plan_output.facts
        if seed.id in world_fact_outputs
    ]
    world_payload = {
        "setting": world_plan_output.setting,
        "time_period": world_plan_output.time_period,
        "tone": world_plan_output.tone,
        "motifs": world_plan_output.motifs,
        "facts": [fact.model_dump(exclude_none=True) for fact in world_facts],
    }
    world = None
    if any(value for value in world_payload.values()):
        world = World.model_validate(world_payload)
    _write_world(world, config_model, output_dir)

    plot_patterns: list[PlotPattern] = []
    narrative_patterns: list[NarrativePattern] = []
    if format_name in {"novel", "novella", "short-story"}:
        if progress:
            progress("Generating plot patterns...")
        plot_pattern_range = _count_range(format_name, "plot_patterns")
        plot_patterns_prompt = build_plot_patterns_prompt(format_name, style_hint or None, plot_pattern_range)
        plot_patterns_user_prompt = _build_user_prompt(
            idea,
            format_name,
            {
                "Style": style_hint,
                "Characters": _summarize_characters(characters),
                "World": _summarize_world_facts(world_facts),
                "Count Targets": (
                    f"Plot patterns: {plot_pattern_range[0]}-{plot_pattern_range[1]}"
                ),
            },
        )

        def validate_plot_patterns(output: PlotPatternsOutput) -> str | None:
            return _validate_plot_patterns_output(output, plot_pattern_range)

        plot_patterns_output = await _run_stage_with_validation_and_warning(
            result_type=PlotPatternsOutput,
            system_prompt=plot_patterns_prompt,
            user_prompt=plot_patterns_user_prompt,
            config=config,
            expected_language=expected_language,
            extract_text=_extract_text_from_plot_patterns,
            normalize=_normalize_plot_patterns_output,
            validate=validate_plot_patterns,
            warn_validate=_validate_plot_pattern_consistency,
            warning_label="Plot pattern consistency",
            progress=progress,
        )
        _maybe_warn_range(progress, "Plot pattern", len(plot_patterns_output.plot_patterns), plot_pattern_range)
        plot_patterns = [
            PlotPattern.model_validate(pattern.model_dump(exclude_none=True))
            for pattern in plot_patterns_output.plot_patterns
        ]
        _write_artifact(
            output_dir,
            "plot_patterns.yml",
            plot_patterns_output.model_dump(exclude_none=True),
        )
        _write_plot_patterns(plot_patterns, config_model, output_dir)

        # Generate narrative patterns based on options
        if options.narrative_patterns_mode != "off":
            if progress:
                progress("Generating narrative patterns...")
            narrative_pattern_range = _count_range(format_name, "narrative_patterns")
            narrative_patterns_prompt = build_narrative_patterns_prompt(
                format_name, style_hint or None, narrative_pattern_range
            )
            narrative_patterns_user_prompt = _build_user_prompt(
                idea,
                format_name,
                {
                    "Style": style_hint,
                    "Style Details": style_output.model_dump(exclude_none=True, by_alias=True),
                    "Plot Patterns": _summarize_plot_patterns(plot_patterns),
                    "Characters": _summarize_characters(characters),
                    "World": _summarize_world_facts(world_facts),
                    "Count Targets": (
                        f"Narrative patterns: {narrative_pattern_range[0]}-{narrative_pattern_range[1]}"
                    ),
                },
            )

            def validate_narrative_patterns(output: NarrativePatternsOutput) -> str | None:
                return _validate_narrative_patterns_output(
                    output,
                    narrative_pattern_range,
                    {pattern.id for pattern in plot_patterns},
                )

            narrative_patterns_output = await _run_stage_with_validation(
                result_type=NarrativePatternsOutput,
                system_prompt=narrative_patterns_prompt,
                user_prompt=narrative_patterns_user_prompt,
                config=config,
                expected_language=expected_language,
                extract_text=_extract_text_from_narrative_patterns,
                normalize=_normalize_narrative_patterns_output,
                validate=validate_narrative_patterns,
            )
            _maybe_warn_range(
                progress,
                "Narrative pattern",
                len(narrative_patterns_output.narrative_patterns),
                narrative_pattern_range,
            )
            narrative_patterns = [
                NarrativePattern.model_validate(pattern.model_dump(exclude_none=True))
                for pattern in narrative_patterns_output.narrative_patterns
            ]
            if options.use_narrative_patterns_in_prompts:
                _maybe_warn_narrative_world_conflicts(progress, narrative_patterns, world_plan_output)
            # Always write to artifacts when generated
            _write_artifact(
                output_dir,
                "narrative_patterns.yml",
                narrative_patterns_output.model_dump(exclude_none=True),
            )
            # Only write to project root if mode is "project"
            if options.narrative_patterns_mode == "project":
                _write_narrative_patterns(narrative_patterns, config_model, output_dir)
        else:
            narrative_patterns = []

    plot: Plot
    if format_name in {"novel", "novella", "short-story"}:
        if progress:
            progress("Planning plot outline...")
        count_ranges = {
            "chapters": _count_range(format_name, "chapters"),
            "scenes": _count_range(format_name, "scenes"),
            "beats": _count_range(format_name, "beats"),
        }
        beats_per_scene = FORMAT_BEATS_PER_SCENE[format_name]
        plot_prompt = build_plot_outline_prompt(format_name, style_hint or None, count_ranges, beats_per_scene)
        
        # Build plot outline context
        plot_context: dict[str, object] = {
            "Style": style_output.model_dump(exclude_none=True),
            "Characters": _summarize_characters(characters),
            "World": _summarize_world_facts(world_facts),
            "Plot Patterns": _summarize_plot_patterns(plot_patterns),
        }
        # Only include narrative patterns if enabled and generated
        if options.use_narrative_patterns_in_prompts and narrative_patterns:
            plot_context["Narrative Patterns"] = _summarize_narrative_patterns(narrative_patterns)
        
        plot_user_prompt = _build_user_prompt(idea, format_name, plot_context)

        def validate_plot_outline(output: PlotOutlineOutput) -> str | None:
            return _validate_plot_outline_output(output)

        plot_outline_output = await _run_stage_with_validation(
            result_type=PlotOutlineOutput,
            system_prompt=plot_prompt,
            user_prompt=plot_user_prompt,
            config=config,
            expected_language=expected_language,
            extract_text=_extract_text_from_plot_outline,
            normalize=_normalize_plot_outline_output,
            validate=validate_plot_outline,
        )
        _maybe_warn_range(progress, "Chapter", len(plot_outline_output.chapters), count_ranges["chapters"])
        _maybe_warn_range(progress, "Scene", len(plot_outline_output.scenes), count_ranges["scenes"])
        total_beats = sum(scene.beat_count for scene in plot_outline_output.scenes)
        _maybe_warn_range(progress, "Total beats", total_beats, count_ranges["beats"])
        _maybe_warn_range(
            progress,
            "Beats per scene (avg)",
            round(total_beats / len(plot_outline_output.scenes))
            if plot_outline_output.scenes
            else 0,
            beats_per_scene,
        )
        _write_artifact(output_dir, "plot_outline.yml", plot_outline_output.model_dump(exclude_none=True))

        plot_pattern_assignment_output: PlotPatternAssignmentOutput | None = None
        beat_templates: dict[str, SceneBeatTemplate] = {}
        if plot_patterns:
            if progress:
                progress("Mapping plot pattern beats...")
            assignment_prompt = build_plot_pattern_assignment_prompt(format_name, style_hint or None)
            assignment_user_prompt = _build_user_prompt(
                idea,
                format_name,
                {
                    "Style": style_output.model_dump(exclude_none=True),
                    "Plot Patterns": _summarize_plot_patterns(plot_patterns),
                    "Plot Outline": plot_outline_output.model_dump(exclude_none=True),
                },
            )

            available_plot_patterns = {pattern.id: pattern for pattern in plot_patterns}
            scene_ids = {scene.id for scene in plot_outline_output.scenes}
            scene_beat_counts = {scene.id: scene.beat_count for scene in plot_outline_output.scenes}

            def validate_plot_pattern_assignment(output: PlotPatternAssignmentOutput) -> str | None:
                return _validate_plot_pattern_assignment_output(
                    output,
                    available_plot_patterns,
                    scene_ids,
                    scene_beat_counts,
                )

            assignment_output: PlotPatternAssignmentOutput = await _run_stage_with_validation(
                result_type=PlotPatternAssignmentOutput,
                system_prompt=assignment_prompt,
                user_prompt=assignment_user_prompt,
                config=config,
                expected_language=expected_language,
                extract_text=_extract_text_from_plot_pattern_assignment,
                normalize=_normalize_plot_pattern_assignment_output,
                validate=validate_plot_pattern_assignment,
            )
            assignment_output = _order_plot_pattern_assignments(assignment_output, plot_patterns)
            plot_pattern_assignment_output = assignment_output
            _write_artifact(
                output_dir,
                "plot_pattern_assignments.yml",
                assignment_output.model_dump(exclude_none=True),
            )
            _maybe_warn_pattern_conflicts(
                progress if options.use_narrative_patterns_in_prompts else None,
                assignment_output.plot_pattern,
                narrative_patterns,
            )
            randomize_templates = config.seed is not None
            beat_templates = _build_scene_beat_templates(
                plot_outline_output,
                plot_patterns,
                assignment_output,
                rng,
                randomize_templates,
            )
            if beat_templates:
                _write_artifact(
                    output_dir,
                    "scene_beat_templates.yml",
                    {
                        "scene_beat_templates": [
                            template.model_dump(exclude_none=True) for template in beat_templates.values()
                        ]
                    },
                )

        if progress:
            progress("Expanding scenes...")
        available_characters = {character.id for character in characters}
        available_world_facts = {fact.id for fact in world_facts}
        location_facts = [fact for fact in world_facts if fact.type == "location"]
        available_location_ids = {fact.id for fact in location_facts}
        available_plot_patterns = {pattern.id: pattern for pattern in plot_patterns}
        available_character_summary = _summarize_characters(characters)
        available_location_summary = _summarize_world_facts(location_facts)

        scene_outputs: dict[str, Scene] = {}
        prior_scene_summaries: list[str] = []
        for scene_outline in plot_outline_output.scenes:
            scene_template = beat_templates.get(scene_outline.id)
            scene_prompt = build_scene_prompt(
                format_name,
                style_hint or None,
                available_character_summary,
                available_location_summary,
                _summarize_outline_summaries(prior_scene_summaries),
            )
            # Build scene context
            scene_context: dict[str, object] = {
                "Scene Outline": scene_outline.model_dump(exclude_none=True),
                "Style": style_output.model_dump(exclude_none=True),
                "Characters": available_character_summary,
                "World": _summarize_world_facts(world_facts),
                "Plot Patterns": _summarize_plot_patterns(plot_patterns),
            }
            # Only include narrative patterns if enabled and generated
            if options.use_narrative_patterns_in_prompts and narrative_patterns:
                scene_context["Narrative Patterns"] = _summarize_narrative_patterns(narrative_patterns)
            scene_context["Plot Pattern Assignments"] = (
                plot_pattern_assignment_output.model_dump(exclude_none=True)
                if plot_pattern_assignment_output
                else None
            )
            if scene_template:
                scene_context["Beat Template"] = scene_template.model_dump(exclude_none=True)
            
            scene_user_prompt = _build_user_prompt(idea, format_name, scene_context)

            def normalize_scene(output: SceneOutput, expected: OutlineSceneOutput = scene_outline) -> SceneOutput:
                normalized = _normalize_scene_output(output)
                updates: dict[str, object] = {"id": expected.id}
                if expected.chapter:
                    updates["chapter"] = expected.chapter
                if normalized.characters:
                    updates["characters"] = [
                        char_id for char_id in normalized.characters if char_id in available_characters
                    ]
                if normalized.world_fact_ids:
                    updates["world_fact_ids"] = [
                        fact_id for fact_id in normalized.world_fact_ids if fact_id in available_world_facts
                    ]
                if normalized.location and normalized.location not in available_location_ids:
                    updates["location"] = None
                if normalized.plot_pattern:
                    if normalized.plot_pattern not in available_plot_patterns:
                        updates["plot_pattern"] = None
                        updates["plot_pattern_beat"] = None
                    else:
                        updates["plot_pattern"] = normalized.plot_pattern
                        if normalized.plot_pattern_beat:
                            beat_types = {
                                beat.type for beat in available_plot_patterns[normalized.plot_pattern].required_beats
                            }
                            updates["plot_pattern_beat"] = (
                                normalized.plot_pattern_beat
                                if normalized.plot_pattern_beat in beat_types
                                else None
                            )
                elif normalized.plot_pattern_beat:
                    updates["plot_pattern_beat"] = None
                beat_updates = []
                for index, beat in enumerate(normalized.beats, start=1):
                    beat_updates.append(
                        beat.model_copy(update={"id": _normalize_id(f"{expected.id}-beat-{index:02d}")})
                    )
                updates["beats"] = beat_updates
                return normalized.model_copy(update=updates)

            def validate_scene(
                output: SceneOutput,
                expected: OutlineSceneOutput = scene_outline,
                scene_template: SceneBeatTemplate | None = scene_template,
            ) -> str | None:
                error = _validate_scene_output(
                    output,
                    expected,
                    available_characters,
                    available_world_facts,
                    beats_per_scene,
                )
                if error:
                    return error
                return _validate_scene_template(output, scene_template)

            scene_output = await _run_stage_with_validation_or_warn(
                result_type=SceneOutput,
                system_prompt=scene_prompt,
                user_prompt=scene_user_prompt,
                config=config,
                expected_language=expected_language,
                extract_text=_extract_text_from_scene,
                normalize=normalize_scene,
                validate=validate_scene,
                warning_label=f"Scene {scene_outline.id!r}",
                progress=progress,
            )
            scene = Scene.model_validate(scene_output.model_dump(exclude_none=True))
            scene_outputs[scene.id] = scene
            if scene.summary:
                prior_scene_summaries.append(scene.summary)
            _write_artifact(output_dir, f"scenes/{scene.id}.yml", scene_output.model_dump(exclude_none=True))

        scenes = [scene_outputs[scene.id] for scene in plot_outline_output.scenes if scene.id in scene_outputs]
        chapters = [
            chapter.model_dump(exclude_none=True) for chapter in plot_outline_output.chapters
        ]
        plot_payload: dict[str, object] = {
            "format": format_name,
            "title": plot_outline_output.title,
            "premise": plot_outline_output.premise,
            "themes": plot_outline_output.themes,
            "hook": plot_outline_output.hook.model_dump(exclude_none=True) if plot_outline_output.hook else None,
            "stakes": plot_outline_output.stakes.model_dump(exclude_none=True)
            if plot_outline_output.stakes
            else None,
            "plot_pattern": (
                plot_pattern_assignment_output.plot_pattern
                if plot_pattern_assignment_output
                else None
            ),
            "plot_pattern_beats": (
                [beat.model_dump(exclude_none=True) for beat in plot_pattern_assignment_output.plot_pattern_beats]
                if plot_pattern_assignment_output
                else []
            ),
            "chapters": chapters,
            "scenes": [scene.model_dump(exclude_none=True) for scene in scenes],
            "scene_ids": None if plot_outline_output.chapters else plot_outline_output.scene_ids,
        }
        plot = Plot.model_validate(plot_payload)
    elif format_name == "micro-prose":
        if progress:
            progress("Planning micro-prose...")
        fragment_range = _count_range(format_name, "fragments")
        fragment_prompt = build_fragment_plan_prompt(format_name, style_hint or None, fragment_range)
        fragment_user_prompt = _build_user_prompt(
            idea,
            format_name,
            {
                "Style": style_hint,
                "Count Targets": f"Fragments: {fragment_range[0]}-{fragment_range[1]}",
            },
        )

        def validate_fragment_plan(output: FragmentPlanOutput) -> str | None:
            return _validate_fragment_plan_output(output)

        fragment_plan_output = await _run_stage_with_validation(
            result_type=FragmentPlanOutput,
            system_prompt=fragment_prompt,
            user_prompt=fragment_user_prompt,
            config=config,
            expected_language=expected_language,
            extract_text=_extract_text_from_fragment_plan,
            normalize=_normalize_fragment_plan_output,
            validate=validate_fragment_plan,
        )
        _maybe_warn_range(progress, "Fragment", len(fragment_plan_output.fragments), fragment_range)
        _write_artifact(output_dir, "fragments_plan.yml", fragment_plan_output.model_dump(exclude_none=True))

        if progress:
            progress("Generating fragments...")
        fragment_outputs: dict[str, Fragment] = {}
        fragment_order = list(fragment_plan_output.fragments)
        if config.seed is not None:
            rng.shuffle(fragment_order)
        for fragment_seed in fragment_order:
            fragment_prompt = build_fragment_prompt(
                format_name,
                style_hint or None,
                _summarize_fragments(list(fragment_outputs.values())),
            )
            fragment_user_prompt = _build_user_prompt(
                idea,
                format_name,
                {
                    "Fragment Seed": fragment_seed.model_dump(exclude_none=True),
                    "Style": style_hint,
                },
            )

            def normalize_fragment(output: FragmentOutput, expected_id: str = fragment_seed.id) -> FragmentOutput:
                normalized = _normalize_fragment_output(output)
                return normalized.model_copy(update={"id": expected_id})

            def validate_fragment(output: FragmentOutput, expected_id: str = fragment_seed.id) -> str | None:
                return _validate_fragment_output(output, expected_id, set(fragment_outputs))

            fragment_output = await _run_stage_with_validation(
                result_type=FragmentOutput,
                system_prompt=fragment_prompt,
                user_prompt=fragment_user_prompt,
                config=config,
                expected_language=expected_language,
                extract_text=_extract_text_from_fragment,
                normalize=normalize_fragment,
                validate=validate_fragment,
            )
            fragment = Fragment.model_validate(fragment_output.model_dump(exclude_none=True))
            fragment_outputs[fragment.id] = fragment
            _write_artifact(
                output_dir,
                f"fragments/{fragment.id}.yml",
                fragment_output.model_dump(exclude_none=True),
            )
        fragments = [
            fragment_outputs[seed.id]
            for seed in fragment_plan_output.fragments
            if seed.id in fragment_outputs
        ]
        plot_payload = {
            "format": format_name,
            "title": fragment_plan_output.title,
            "premise": fragment_plan_output.premise,
            "themes": fragment_plan_output.themes,
            "fragments": [fragment.model_dump(exclude_none=True) for fragment in fragments],
        }
        plot = Plot.model_validate(plot_payload)
    else:
        if progress:
            progress("Planning poem...")
        stanza_range = _count_range(format_name, "stanzas")
        line_range = _count_range(format_name, "lines")
        poem_prompt = build_poem_plan_prompt(format_name, style_hint or None, stanza_range, line_range)
        poem_user_prompt = _build_user_prompt(
            idea,
            format_name,
            {
                "Style": style_hint,
                "Count Targets": f"Stanzas: {stanza_range[0]}-{stanza_range[1]}",
            },
        )

        def validate_poem_plan(output: PoemPlanOutput) -> str | None:
            return _validate_poem_plan_output(output)

        poem_plan_output = await _run_stage_with_validation(
            result_type=PoemPlanOutput,
            system_prompt=poem_prompt,
            user_prompt=poem_user_prompt,
            config=config,
            expected_language=expected_language,
            extract_text=_extract_text_from_poem_plan,
            normalize=_normalize_poem_plan_output,
            validate=validate_poem_plan,
        )
        _maybe_warn_range(progress, "Stanza", len(poem_plan_output.stanzas), stanza_range)
        total_lines = sum(stanza.line_count for stanza in poem_plan_output.stanzas)
        _maybe_warn_range(progress, "Total lines", total_lines, line_range)
        _write_artifact(output_dir, "poem_plan.yml", poem_plan_output.model_dump(exclude_none=True))

        if progress:
            progress("Generating stanzas...")
        stanza_outputs: dict[str, Stanza] = {}
        stanza_order = list(poem_plan_output.stanzas)
        if config.seed is not None:
            rng.shuffle(stanza_order)
        for stanza_seed in stanza_order:
            stanza_prompt = build_stanza_prompt(
                format_name,
                style_hint or None,
                _summarize_stanzas(list(stanza_outputs.values())),
            )
            stanza_user_prompt = _build_user_prompt(
                idea,
                format_name,
                {
                    "Stanza Seed": stanza_seed.model_dump(exclude_none=True),
                    "Poem Metadata": {
                        "poem_form": poem_plan_output.poem_form,
                        "poem_meter": poem_plan_output.poem_meter,
                        "poem_rhyme_scheme": poem_plan_output.poem_rhyme_scheme,
                    },
                },
            )

            def normalize_stanza(output: StanzaOutput, expected: StanzaPlanItem = stanza_seed) -> StanzaOutput:
                normalized = _normalize_stanza_output(output)
                return normalized.model_copy(update={"id": expected.id})

            def validate_stanza(output: StanzaOutput, expected: StanzaPlanItem = stanza_seed) -> str | None:
                return _validate_stanza_output(
                    output, expected.id, expected.line_count, set(stanza_outputs)
                )

            stanza_output = await _run_stage_with_validation(
                result_type=StanzaOutput,
                system_prompt=stanza_prompt,
                user_prompt=stanza_user_prompt,
                config=config,
                expected_language=expected_language,
                extract_text=_extract_text_from_stanza,
                normalize=normalize_stanza,
                validate=validate_stanza,
            )
            stanza = Stanza.model_validate(stanza_output.model_dump(exclude_none=True))
            stanza_outputs[stanza.id] = stanza
            _write_artifact(output_dir, f"stanzas/{stanza.id}.yml", stanza_output.model_dump(exclude_none=True))
        stanzas = [
            stanza_outputs[seed.id]
            for seed in poem_plan_output.stanzas
            if seed.id in stanza_outputs
        ]
        plot_payload = {
            "format": format_name,
            "title": poem_plan_output.title,
            "premise": poem_plan_output.premise,
            "themes": poem_plan_output.themes,
            "poem_form": poem_plan_output.poem_form,
            "poem_meter": poem_plan_output.poem_meter,
            "poem_rhyme_scheme": poem_plan_output.poem_rhyme_scheme,
            "stanzas": [stanza.model_dump(exclude_none=True) for stanza in stanzas],
        }
        plot = Plot.model_validate(plot_payload)

    config_model.title = plot.title
    _write_plot(plot, config_model, output_dir)

    project = Project(
        config=config_model,
        plot=plot,
        characters=characters,
        world=world,
        style=style,
        plot_patterns=plot_patterns,
        narrative_patterns=narrative_patterns,
    )
    _validate_project(project)
    _write_config(config_model, output_dir)
    return project


def generate_project_from_idea_sync(
    idea: str,
    format_name: LiteratureFormat,
    config: LLMConfig,
    output_dir: Path,
    idea_language: str | None = None,
    progress: Callable[[str], None] | None = None,
    options: CreateOptions | None = None,
) -> Project:
    """Synchronous wrapper for generate_project_from_idea."""
    return asyncio.run(
        generate_project_from_idea(
            idea,
            format_name,
            config,
            output_dir=output_dir,
            idea_language=idea_language,
            progress=progress,
            options=options,
        )
    )


__all__ = ["CreateProjectError", "generate_project_from_idea", "generate_project_from_idea_sync"]
