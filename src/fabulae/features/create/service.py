"""Service layer for create-from-idea project generation."""

from __future__ import annotations

import asyncio
import math
import random
import re
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Generic, TypeVar, cast

from pydantic import ValidationError

from fabulae.features.create.errors import (
    ErrorType,
    classify_error,
    format_json_retry_hint,
    is_json_error,
    is_transient_error,
)
from fabulae.features.create.progress import CreateProgress
from fabulae.features.create.schemas import (
    CharacterOutput,
    CharacterPlanOutput,
    CreateOptions,
    FragmentOutput,
    FragmentPlanOutput,
    OutlineSceneOutput,
    PlotOutlineOutput,
    PoemPlanOutput,
    SceneBeatTemplate,
    SceneOutput,
    StanzaOutput,
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
    Plot,
    Project,
    ProjectConfig,
    ProjectPaths,
    Scene,
    Stanza,
    Style,
    World,
    WorldFact,
    _dump_plot,
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
    },
    "novella": {
        "chapters": (6, 16),
        "scenes": (18, 48),
        "beats": (72, 192),
        "characters": (4, 8),
        "world_facts": (6, 12),
    },
    "short-story": {
        "chapters": (0, 6),
        "scenes": (2, 8),
        "beats": (6, 24),
        "characters": (2, 5),
        "world_facts": (2, 6),
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


class ErrorMode(Enum):
    STRICT = "strict"
    WARN = "warn"
    STRICT_THEN_WARN = "strict_then_warn"


@dataclass
class StageResult(Generic[T]):
    output: T
    warnings: list[str] = field(default_factory=list)
    attempts: int = 1


@dataclass
class SceneContext:
    """Context needed to generate and validate an individual scene."""

    idea: str
    format_name: LiteratureFormat
    style: StyleOutput
    style_hint: str
    scene_outline: OutlineSceneOutput
    characters: list[Character]
    world_facts: list[WorldFact]
    beat_template: SceneBeatTemplate | None
    available_characters: set[str]
    available_world_facts: set[str]
    available_location_ids: set[str]
    available_character_summary: str
    available_location_summary: str
    world_summary: str
    prior_scene_summaries: list[str]
    beats_per_scene: tuple[int, int]


def _build_user_prompt(idea: str, format_name: LiteratureFormat, context: dict[str, object] | None = None) -> str:
    sections: dict[str, object] = {"Idea": idea.strip(), "Format": format_name}
    if context:
        sections.update(context)
    return format_project_context(sections)


def _format_stage_warning(warning_label: str | None, max_retries: int, error: str | None) -> str:
    details = error or "Unknown error"
    if warning_label:
        return f"Warning: {warning_label} validation failed after {max_retries} retries: {details}"
    return f"Warning: Validation failed after {max_retries} retries: {details}"


def _format_retry_prompt(
    user_prompt: str,
    error: str,
    attempt: int,
    max_retries: int,
    *,
    include_json_hint: bool = False,
) -> str:
    """Format an actionable retry prompt with the validation error.

    Provides specific guidance to help the LLM understand what went wrong
    and how to fix it. This is especially important for smaller LLMs.

    Args:
        user_prompt: The original user prompt.
        error: The error message from the previous attempt.
        attempt: The current retry attempt number.
        max_retries: Maximum number of retries allowed.
        include_json_hint: If True, add extra JSON formatting guidance.
    """
    guidance_lines = [
        f"\n\n--- RETRY {attempt}/{max_retries} ---",
        "Your previous response had a validation error:",
        f"ERROR: {error}",
        "",
        "Please fix the issue by:",
        "1. Reading the error message carefully",
        "2. Checking that all IDs match the assigned IDs exactly (lowercase-hyphenated)",
        "3. Ensuring required fields are present and have correct types",
        "4. Verifying counts match requirements (beat_count, line_count, etc.)",
        "5. Outputting ONLY valid JSON (no markdown, no explanation)",
    ]

    if include_json_hint:
        guidance_lines.append(format_json_retry_hint())

    guidance_lines.extend(
        [
            "",
            "ORIGINAL REQUEST:",
            user_prompt,
        ]
    )
    return "\n".join(guidance_lines)


async def run_stage(
    *,
    result_type: type[T],
    system_prompt: str,
    user_prompt: str,
    config: LLMConfig,
    expected_language: str | None,
    extract_text: Callable[[T], str],
    normalize: Callable[[T], T] | None = None,
    validate: Callable[[T], str | None] | None = None,
    warn_validate: Callable[[T], str | None] | None = None,
    warning_label: str | None = None,
    progress: Callable[[str], None] | None = None,
    max_retries: int = 2,
    error_mode: ErrorMode = ErrorMode.STRICT,
    stage_name: str | None = None,
) -> StageResult[T]:
    prompt_state = {"system": system_prompt}
    warnings: list[str] = []

    async def _invoke_stage(current_prompt: str) -> T:
        async def runner() -> T:
            agent = create_agent(result_type, prompt_state["system"], config)
            result = await agent.run(current_prompt)
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

    attempt = 0
    current_prompt = user_prompt
    last_output: T | None = None
    last_error: str | None = None
    last_error_type: ErrorType | None = None

    while True:
        try:
            output = await _invoke_stage(current_prompt)
            if normalize:
                output = normalize(output)
            last_output = output
            last_error_type = None  # Reset on success
        except Exception as exc:
            # Classify the error to determine retry strategy
            last_error_type = classify_error(exc)
            last_error = f"Output error: {exc}"

            # For non-transient errors, fail immediately without retrying
            if not is_transient_error(last_error_type):
                error_msg = "Failed to generate valid output"
                if stage_name:
                    error_msg = f"[{stage_name}] {error_msg}"
                raise CreateProjectError(f"{error_msg}: {last_error}") from exc
        else:
            strict_error = validate(output) if validate else None
            warn_error = None
            if strict_error is None and warn_validate:
                warn_error = warn_validate(output)
            if strict_error is None and warn_error is None:
                return StageResult(output=output, warnings=warnings, attempts=attempt + 1)
            last_error = strict_error or warn_error
            last_error_type = ErrorType.VALIDATION_ERROR

        attempt += 1
        if attempt > max_retries:
            if last_output is None or error_mode == ErrorMode.STRICT:
                error_msg = "Failed to generate valid output"
                if stage_name:
                    error_msg = f"[{stage_name}] {error_msg}"
                raise CreateProjectError(f"{error_msg}: {last_error}")
            warning_message = _format_stage_warning(warning_label, max_retries, last_error)
            warnings.append(warning_message)
            if progress:
                progress(warning_message)
            return StageResult(output=last_output, warnings=warnings, attempts=attempt)

        # Include JSON-specific hints for JSON-related errors
        include_json_hint = last_error_type is not None and is_json_error(last_error_type)
        current_prompt = _format_retry_prompt(
            user_prompt,
            last_error or "Unknown error",
            attempt,
            max_retries,
            include_json_hint=include_json_hint,
        )


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
        # Validate each chapter's scene_ids
        all_referenced_scenes: set[str] = set()
        for chapter in output.chapters:
            if chapter.scene_ids is None:
                continue
            if len(set(chapter.scene_ids)) != len(chapter.scene_ids):
                return f"Chapter {chapter.id!r} has duplicate scene IDs."
            # Check for unknown scenes
            unknown = set(chapter.scene_ids) - scene_ids
            if unknown:
                return f"Chapter {chapter.id!r} references unknown scenes: {sorted(unknown)!r}."
            # Check for scenes referenced by multiple chapters
            duplicates = all_referenced_scenes & set(chapter.scene_ids)
            if duplicates:
                return f"Chapter {chapter.id!r} references scenes already in another chapter: {sorted(duplicates)!r}."
            all_referenced_scenes.update(chapter.scene_ids)
        # Check for orphan scenes (scenes not in any chapter)
        orphan_scenes = scene_ids - all_referenced_scenes
        if orphan_scenes:
            return f"Scenes not assigned to any chapter: {sorted(orphan_scenes)!r}."
        if output.scene_ids is not None:
            return "scene_ids must be null when chapters are present."
    else:
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


def _validate_scene_output(
    output: SceneOutput,
    expected_scene: OutlineSceneOutput,
    available_characters: set[str],
    available_world_facts: set[str],
    beats_per_scene: tuple[int, int],
) -> str | None:
    if output.id != expected_scene.id:
        return f"Scene ID {output.id!r} does not match expected {expected_scene.id!r}."
    if len(output.beats) != expected_scene.beat_count:
        return f"Scene {output.id!r} must have {expected_scene.beat_count} beats, got {len(output.beats)}."
    if len(output.beats) < beats_per_scene[0] or len(output.beats) > beats_per_scene[1]:
        return (
            f"Scene {output.id!r} beat count {len(output.beats)} is outside {beats_per_scene[0]}-{beats_per_scene[1]}."
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
        return f"Stanza {output.id!r} must have {expected_line_count} lines, got {len(output.lines)}."
    try:
        Stanza.model_validate(output.model_dump(exclude_none=True))
    except ValidationError as exc:
        return f"Stanza validation error: {exc}"
    return None


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
        expected_kind = template_item.kind
        actual_kind = output.beats[index].kind
        if actual_kind != expected_kind:
            return f"Scene {output.id!r} beat {index + 1} should be kind {expected_kind!r}, got {actual_kind!r}."
    return None


def _build_scene_prompt_context(scene_context: SceneContext) -> dict[str, object]:
    context: dict[str, object] = {
        "Scene Outline": scene_context.scene_outline.model_dump(exclude_none=True),
        "Style": scene_context.style.model_dump(exclude_none=True),
        "Characters": scene_context.available_character_summary,
        "World": scene_context.world_summary,
    }
    if scene_context.beat_template:
        context["Beat Template"] = scene_context.beat_template.model_dump(exclude_none=True)
    return context


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


def _coerce_style(output: StyleOutput) -> Style | None:
    payload = output.model_dump(exclude_none=True, by_alias=True)
    if not payload:
        return None
    return Style.model_validate(payload)


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
    if output.location:
        update["location"] = _normalize_id(output.location)
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
    create_progress: CreateProgress | None = None,
) -> Project:
    """Generate a complete Fabulae project from an idea.

    This is a thin dispatcher that routes to format-specific pipelines:
    - prose formats (novel, novella, short-story) -> generate_prose()
    - micro-prose -> generate_micro_prose()
    - poem -> generate_poem()

    Args:
        idea: The core idea or premise for the narrative
        format_name: The literature format to generate
        config: LLM configuration for generation
        output_dir: Directory to save the project files
        idea_language: Optional language override
        progress: Optional progress callback function (deprecated, use create_progress)
        options: Optional creation options
        create_progress: Optional CreateProgress instance for timing and status

    Returns:
        A complete Project object with all narrative elements

    Raises:
        ValueError: If format is invalid or idea is empty
        CreateProjectError: If generation fails
    """
    _validate_format(format_name)
    if not idea.strip():
        raise ValueError("Idea must not be empty.")

    if options is None:
        options = CreateOptions()

    # Create output directory and artifacts directory
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir = _artifact_root(output_dir)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    # Log start of generation (legacy callback)
    if progress:
        progress(f"Starting {format_name} generation from idea...")

    # Use provided progress reporter or create a new one
    if create_progress is None:
        create_progress = CreateProgress()

    # Dispatch to appropriate pipeline based on format and pipeline option
    if format_name in ("novel", "novella", "short-story"):
        if options.pipeline == "sequential":
            from fabulae.features.create.pipelines.sequential import generate_prose_sequential

            project = await generate_prose_sequential(
                idea=idea,
                format=format_name,
                options=options,
                llm_config=config,
                progress=create_progress,
                artifacts_dir=output_dir,
            )
        else:
            from fabulae.features.create.pipelines.prose import generate_prose

            project = await generate_prose(
                idea=idea,
                format=format_name,
                options=options,
                llm_config=config,
                progress=create_progress,
                artifacts_dir=output_dir,
            )
    elif format_name == "micro-prose":
        if options.pipeline == "sequential":
            from fabulae.features.create.pipelines.micro_prose_sequential import (
                generate_micro_prose_sequential,
            )

            project = await generate_micro_prose_sequential(
                idea=idea,
                options=options,
                llm_config=config,
                progress=create_progress,
                artifacts_dir=output_dir,
            )
        else:
            from fabulae.features.create.pipelines.micro_prose import generate_micro_prose

            project = await generate_micro_prose(
                idea=idea,
                options=options,
                llm_config=config,
                progress=create_progress,
                artifacts_dir=output_dir,
            )
    elif format_name == "poem":
        if options.pipeline == "sequential":
            from fabulae.features.create.pipelines.poem_sequential import generate_poem_sequential

            project = await generate_poem_sequential(
                idea=idea,
                options=options,
                llm_config=config,
                progress=create_progress,
                artifacts_dir=output_dir,
            )
        else:
            from fabulae.features.create.pipelines.poem import generate_poem

            project = await generate_poem(
                idea=idea,
                options=options,
                llm_config=config,
                progress=create_progress,
                artifacts_dir=output_dir,
            )
    else:
        # This should never happen due to _validate_format, but for safety
        raise ValueError(f"Unsupported format: {format_name}")

    return project


def generate_project_from_idea_sync(
    idea: str,
    format_name: LiteratureFormat,
    config: LLMConfig,
    output_dir: Path,
    idea_language: str | None = None,
    progress: Callable[[str], None] | None = None,
    options: CreateOptions | None = None,
    create_progress: CreateProgress | None = None,
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
            create_progress=create_progress,
        )
    )


__all__ = [
    "CreateProjectError",
    "ErrorMode",
    "SceneContext",
    "StageResult",
    "generate_project_from_idea",
    "generate_project_from_idea_sync",
    "run_stage",
]
