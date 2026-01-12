"""Tests for create-from-idea generation."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from pathlib import Path
from typing import Literal, cast

import pytest
from typer.testing import CliRunner

from fabulae.features.create import cli as create_cli
from fabulae.features.create import service as create_service
from fabulae.features.create.schemas import (
    BeatOutput,
    ChapterOutput,
    CharacterOutput,
    CharacterPlanItem,
    CharacterPlanOutput,
    CreateOptions,
    FragmentOutput,
    FragmentPlanItem,
    FragmentPlanOutput,
    NarrativePatternOutput,
    NarrativePatternsOutput,
    NarrativeRoleOutput,
    OutlineSceneOutput,
    PlotOutlineOutput,
    PlotPatternAssignmentOutput,
    PlotPatternBeatAssignmentOutput,
    PlotPatternBeatOutput,
    PlotPatternOutput,
    PlotPatternRoleOutput,
    PlotPatternsOutput,
    PoemPlanOutput,
    SceneOutput,
    StanzaOutput,
    StanzaPlanItem,
    StyleOutput,
    WorldFactOutput,
    WorldFactPlanItem,
    WorldPlanOutput,
)
from fabulae.llm import LLMConfig
from fabulae.main import app
from fabulae.models import (
    Fragment,
    LiteratureFormat,
    Plot,
    PlotPattern,
    Project,
    ProjectConfig,
    ProjectPaths,
    Scene,
    Stanza,
    load_yaml_file,
)

runner = CliRunner()


class DummyResult:
    def __init__(self, output: object) -> None:
        self.output = output


class DummyAgent:
    def __init__(self, output: object) -> None:
        self._output = output

    async def run(self, *_args: object, **_kwargs: object) -> DummyResult:
        return DummyResult(self._output)


def _fake_agent_factory(outputs_by_type: dict[type[object], list[object]]) -> Callable[..., DummyAgent]:
    def fake_create_agent(result_type: type[object], _prompt: str, _config: LLMConfig) -> DummyAgent:
        queue = outputs_by_type.get(result_type)
        if not queue:
            raise AssertionError(f"Unexpected output type or empty queue: {result_type}")
        return DummyAgent(queue.pop(0))

    return fake_create_agent


def _character_plan(format_name: LiteratureFormat) -> CharacterPlanOutput:
    count = create_service.FORMAT_COUNT_RANGES[format_name]["characters"][0]
    characters = [
        CharacterPlanItem(id=f"char-{index+1:02d}", name=f"Character {index+1}", role="role")
        for index in range(count)
    ]
    return CharacterPlanOutput(characters=characters)


def _character_outputs(plan: CharacterPlanOutput) -> list[CharacterOutput]:
    return [
        CharacterOutput(id=item.id, name=item.name, role=item.role, desire="desire")
        for item in plan.characters
    ]


def _world_plan(format_name: LiteratureFormat) -> WorldPlanOutput:
    count = create_service.FORMAT_COUNT_RANGES[format_name]["world_facts"][0]
    facts: list[WorldFactPlanItem] = []
    for index in range(count):
        fact_type: Literal["location", "rule"] = "location" if index == 0 else "rule"
        facts.append(
            WorldFactPlanItem(
                id=f"fact-{index+1:02d}",
                type=fact_type,
                name=f"Fact {index+1}",
                purpose="Purpose",
            )
        )
    return WorldPlanOutput(
        setting="Test setting",
        time_period="Now",
        tone="Moody",
        motifs=["rain"],
        facts=facts,
    )


def _world_fact_outputs(plan: WorldPlanOutput) -> list[WorldFactOutput]:
    return [
        WorldFactOutput(id=fact.id, type=fact.type, name=fact.name, facts=["Detail"])
        for fact in plan.facts
    ]


def _plot_patterns() -> PlotPatternsOutput:
    return PlotPatternsOutput(
        plot_patterns=[
            PlotPatternOutput(
                id="three-act",
                name="Three-Act",
                description="Classic rise-fall arc.",
                roles=[PlotPatternRoleOutput(id="protagonist", description="drives the central goal")],
                required_beats=[
                    PlotPatternBeatOutput(type="inciting-incident", description="the disruption"),
                    PlotPatternBeatOutput(type="climax", description="final confrontation"),
                ],
            )
        ]
    )


def test_plot_pattern_summary_includes_beat_descriptions() -> None:
    plot_patterns_output = _plot_patterns()
    patterns = [
        PlotPattern.model_validate(pattern.model_dump(exclude_none=True))
        for pattern in plot_patterns_output.plot_patterns
    ]

    summary = create_service._summarize_plot_patterns(patterns)

    assert "inciting-incident: the disruption" in summary
    assert "climax: final confrontation" in summary


def _narrative_patterns(plot_patterns: PlotPatternsOutput) -> NarrativePatternsOutput:
    plot_pattern_id = plot_patterns.plot_patterns[0].id if plot_patterns.plot_patterns else None
    return NarrativePatternsOutput(
        narrative_patterns=[
            NarrativePatternOutput(
                id="close-third",
                name="Close Third",
                description="Tight third-person with limited access.",
                plot_pattern=plot_pattern_id,
                roles=[NarrativeRoleOutput(id="observer", description="filters tone")],
                themes=["identity"],
                motifs=["mirrors"],
                tone="noir",
                notes=["track internal shifts"],
            )
        ]
    )


def _plot_pattern_assignment(
    outline: PlotOutlineOutput,
    plot_patterns: PlotPatternsOutput,
) -> PlotPatternAssignmentOutput:
    beat_types = [
        beat.type
        for beat in plot_patterns.plot_patterns[0].required_beats
        if plot_patterns.plot_patterns
    ]
    assignments = []
    for index, beat_type in enumerate(beat_types):
        scene_id = outline.scenes[index % len(outline.scenes)].id
        assignments.append(PlotPatternBeatAssignmentOutput(type=beat_type, scene=scene_id))
    return PlotPatternAssignmentOutput(
        plot_pattern=plot_patterns.plot_patterns[0].id if plot_patterns.plot_patterns else None,
        plot_pattern_beats=assignments,
    )


def _plot_outline(format_name: Literal["novel", "novella", "short-story"]) -> PlotOutlineOutput:
    count_ranges = create_service.FORMAT_COUNT_RANGES[format_name]
    chapters_count = count_ranges["chapters"][0]
    scenes_count = count_ranges["scenes"][0]
    beats_range = count_ranges["beats"]
    beats_per_scene = create_service.FORMAT_BEATS_PER_SCENE[format_name]

    beat_count = max(beats_per_scene[0], math.ceil(beats_range[0] / scenes_count))
    beat_count = min(beat_count, beats_per_scene[1])

    scenes: list[OutlineSceneOutput] = []
    chapters: list[ChapterOutput] = []
    scene_ids: list[str] | None = None

    if chapters_count:
        chapter_ids = [f"chapter-{index+1:02d}" for index in range(chapters_count)]
        chapter_scene_map: dict[str, list[str]] = {chapter_id: [] for chapter_id in chapter_ids}
        for index in range(scenes_count):
            chapter_id = chapter_ids[index % chapters_count]
            scene_id = f"scene-{index+1:02d}"
            chapter_scene_map[chapter_id].append(scene_id)
            scenes.append(
                OutlineSceneOutput(
                    id=scene_id,
                    chapter=chapter_id,
                    summary=f"Scene {index+1} summary",
                    beat_count=beat_count,
                )
            )
        chapters = [
            ChapterOutput(id=chapter_id, scene_ids=scene_ids)
            for chapter_id, scene_ids in chapter_scene_map.items()
        ]
    else:
        scenes = [
            OutlineSceneOutput(
                id=f"scene-{index+1:02d}",
                summary=f"Scene {index+1} summary",
                beat_count=beat_count,
            )
            for index in range(scenes_count)
        ]
        scene_ids = [scene.id for scene in scenes]

    return PlotOutlineOutput(
        format=format_name,
        title="Test Title",
        premise="Test premise.",
        themes=["theme"],
        chapters=chapters,
        scenes=scenes,
        scene_ids=scene_ids,
    )


def _scene_outputs(
    outline: PlotOutlineOutput,
    plot_patterns: PlotPatternsOutput | None = None,
    assignment: PlotPatternAssignmentOutput | None = None,
) -> list[SceneOutput]:
    required_order: list[str] = []
    assignment_map: dict[str, str] = {}
    if plot_patterns and assignment and assignment.plot_pattern:
        pattern = next(
            (pattern for pattern in plot_patterns.plot_patterns if pattern.id == assignment.plot_pattern),
            None,
        )
        if pattern:
            required_order = [beat.type for beat in pattern.required_beats]
            assignment_map = {beat.type: beat.scene for beat in assignment.plot_pattern_beats}
    outputs: list[SceneOutput] = []
    for scene in outline.scenes:
        required_beats = [beat for beat in required_order if assignment_map.get(beat) == scene.id]
        beats = [
            BeatOutput(
                id=f"{scene.id}-beat-{index+1:02d}",
                kind=(required_beats[index] if index < len(required_beats) else "setup"),
                summary="Beat summary",
            )
            for index in range(scene.beat_count)
        ]
        outputs.append(
            SceneOutput(
                id=scene.id,
                chapter=scene.chapter,
                summary=scene.summary,
                beats=beats,
                characters=[],
                world_fact_ids=[],
            )
        )
    return outputs


def _fragment_plan() -> FragmentPlanOutput:
    count = create_service.FORMAT_COUNT_RANGES["micro-prose"]["fragments"][0]
    fragments = [
        FragmentPlanItem(id=f"frag-{index+1:02d}", target_words=50, intent="Intent")
        for index in range(count)
    ]
    return FragmentPlanOutput(
        title="Micro Title",
        premise="Micro premise.",
        themes=["spark"],
        fragments=fragments,
    )


def _fragment_outputs(plan: FragmentPlanOutput) -> list[FragmentOutput]:
    return [
        FragmentOutput(id=fragment.id, content="Fragment content.", target_words=fragment.target_words)
        for fragment in plan.fragments
    ]


def _poem_plan() -> PoemPlanOutput:
    stanza_count = create_service.FORMAT_COUNT_RANGES["poem"]["stanzas"][0]
    stanzas = [
        StanzaPlanItem(id=f"stanza-{index+1:02d}", line_count=3, intent="Intent")
        for index in range(stanza_count)
    ]
    return PoemPlanOutput(
        title="Poem Title",
        premise="Poem premise.",
        themes=["light"],
        poem_form="free verse",
        stanzas=stanzas,
    )


def _stanza_outputs(plan: PoemPlanOutput) -> list[StanzaOutput]:
    outputs: list[StanzaOutput] = []
    for stanza in plan.stanzas:
        lines = [f"Line {index+1}" for index in range(stanza.line_count)]
        outputs.append(StanzaOutput(id=stanza.id, lines=lines))
    return outputs


def _minimal_project(format_name: LiteratureFormat) -> Project:
    if format_name in {"novel", "novella", "short-story"}:
        plot = Plot(format=format_name, premise="Premise.", scenes=[Scene(id="scene-01")])
    elif format_name == "micro-prose":
        plot = Plot(
            format=format_name,
            premise="Premise.",
            fragments=[Fragment(id="frag-01", content="Fragment.")],
        )
    else:
        plot = Plot(
            format="poem",
            premise="Premise.",
            stanzas=[Stanza(id="stanza-01", lines=["Line"])],
        )
    config = ProjectConfig(version="0.1.0", paths=ProjectPaths())
    return Project(config=config, plot=plot)


@pytest.mark.parametrize("format_name", ["novel", "novella", "short-story", "micro-prose", "poem"])
def test_generate_project_from_idea_builds_project(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    format_name: str,
) -> None:
    style_output = StyleOutput(language="en", pov="third", tense="past", voice="observant")
    format_value = cast(LiteratureFormat, format_name)

    character_plan = _character_plan(format_value)
    world_plan = _world_plan(format_value)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
    }

    if format_value in {"novel", "novella", "short-story"}:
        outline = _plot_outline(cast(Literal["novel", "novella", "short-story"], format_value))
        plot_patterns = _plot_patterns()
        narrative_patterns = _narrative_patterns(plot_patterns)
        assignment = _plot_pattern_assignment(outline, plot_patterns)
        outputs_by_type[PlotPatternsOutput] = [plot_patterns]
        outputs_by_type[NarrativePatternsOutput] = [narrative_patterns]
        outputs_by_type[PlotOutlineOutput] = [outline]
        outputs_by_type[PlotPatternAssignmentOutput] = [assignment]
        outputs_by_type[SceneOutput] = cast(list[object], _scene_outputs(outline, plot_patterns, assignment))
    elif format_value == "micro-prose":
        fragment_plan = _fragment_plan()
        outputs_by_type[FragmentPlanOutput] = [fragment_plan]
        outputs_by_type[FragmentOutput] = cast(list[object], _fragment_outputs(fragment_plan))
    else:
        poem_plan = _poem_plan()
        outputs_by_type[PoemPlanOutput] = [poem_plan]
        outputs_by_type[StanzaOutput] = cast(list[object], _stanza_outputs(poem_plan))

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))

    project = asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    assert project.plot.format == format_name
    if format_name in {"novel", "novella", "short-story"}:
        assert project.plot.scenes
    if format_name == "micro-prose":
        assert project.plot.fragments
    if format_name == "poem":
        assert project.plot.stanzas or project.plot.lines


def test_create_command_reads_idea_from_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    idea_path = tmp_path / "idea.txt"
    idea_path.write_text("Idea from file.", encoding="utf-8")
    target = tmp_path / "project"
    captured: list[str] = []

    def fake_generate(
        idea: str,
        format_name: LiteratureFormat,
        _config: LLMConfig,
        output_dir: Path,
        idea_language: str | None = None,
        progress: Callable[[str], None] | None = None,
        options: object = None,
    ) -> Project:
        captured.append(idea)
        return _minimal_project(format_name)

    monkeypatch.setattr(create_cli, "generate_project_from_idea_sync", fake_generate)

    result = runner.invoke(
        app,
        ["create", str(target), "--idea", str(idea_path), "--format", "short-story"],
    )
    assert result.exit_code == 0
    assert captured == ["Idea from file."]


def test_create_command_prompts_for_idea(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    captured: list[str] = []

    def fake_generate(
        idea: str,
        format_name: LiteratureFormat,
        _config: LLMConfig,
        output_dir: Path,
        idea_language: str | None = None,
        progress: Callable[[str], None] | None = None,
        options: object = None,
    ) -> Project:
        captured.append(idea)
        return _minimal_project(format_name)

    monkeypatch.setattr(create_cli, "generate_project_from_idea_sync", fake_generate)

    result = runner.invoke(
        app,
        ["create", str(target), "--format", "poem"],
        input="A prompted idea.\n",
    )
    assert result.exit_code == 0
    assert captured == ["A prompted idea."]


def test_create_command_rejects_existing_directory(tmp_path: Path) -> None:
    existing = tmp_path / "project"
    existing.mkdir()
    result = runner.invoke(app, ["create", str(existing), "--idea", "Test", "--format", "novel"])
    assert result.exit_code != 0
    assert "already exists" in result.output


@pytest.mark.parametrize(
    ("format_name", "expected_format"),
    [
        ("novel", "novel"),
        ("novella", "novella"),
        ("short-story", "short-story"),
        ("micro-prose", "micro-prose"),
        ("poem", "poem"),
    ],
)
def test_create_command_writes_format_to_plot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    format_name: str,
    expected_format: str,
) -> None:
    target = tmp_path / f"project-{format_name}"

    def fake_generate(
        idea: str,
        format_name: LiteratureFormat,
        _config: LLMConfig,
        output_dir: Path,
        idea_language: str | None = None,
        progress: Callable[[str], None] | None = None,
        options: object = None,
    ) -> Project:
        return _minimal_project(format_name)

    monkeypatch.setattr(create_cli, "generate_project_from_idea_sync", fake_generate)

    result = runner.invoke(
        app,
        ["create", str(target), "--idea", "Test", "--format", format_name],
    )
    assert result.exit_code == 0
    plot_data = load_yaml_file(target / "plot.yml")
    assert plot_data["format"] == expected_format


def test_create_command_rejects_invalid_language(tmp_path: Path) -> None:
    target = tmp_path / "project"
    result = runner.invoke(
        app,
        ["create", str(target), "--idea", "Test", "--format", "novel", "--language", "english"],
    )
    assert result.exit_code != 0
    assert "Language must be an ISO 639-1 code" in result.output


def test_create_command_passes_language_override(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    captured: list[str | None] = []

    def fake_generate(
        idea: str,
        format_name: LiteratureFormat,
        _config: LLMConfig,
        output_dir: Path,
        idea_language: str | None = None,
        progress: Callable[[str], None] | None = None,
        options: object = None,
    ) -> Project:
        captured.append(idea_language)
        return _minimal_project(format_name)

    monkeypatch.setattr(create_cli, "generate_project_from_idea_sync", fake_generate)

    result = runner.invoke(
        app,
        ["create", str(target), "--idea", "Test", "--format", "novel", "--language", "fr"],
    )
    assert result.exit_code == 0
    assert captured == ["fr"]


def test_create_command_passes_seed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "project"
    captured: list[int | None] = []

    def fake_generate(
        idea: str,
        format_name: LiteratureFormat,
        config: LLMConfig,
        output_dir: Path,
        idea_language: str | None = None,
        progress: Callable[[str], None] | None = None,
        options: object = None,
    ) -> Project:
        captured.append(config.seed)
        return _minimal_project(format_name)

    monkeypatch.setattr(create_cli, "generate_project_from_idea_sync", fake_generate)

    result = runner.invoke(
        app,
        ["create", str(target), "--idea", "Test", "--format", "novel", "--seed", "123"],
    )
    assert result.exit_code == 0
    assert captured == [123]


def test_generate_project_writes_artifacts_and_language(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="es", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("es", 0.9))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "Una idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(narrative_patterns_mode="artifact"),
        )
    )

    config = load_yaml_file(tmp_path / "fabulae.yml")
    style = load_yaml_file(tmp_path / "style.yml")
    defaults = cast(dict[str, object], config.get("defaults", {}))
    assert defaults.get("language") == "es"
    assert style.get("language") == "es"
    assert (tmp_path / "characters.yml").exists()
    assert (tmp_path / "world.yml").exists()
    assert (tmp_path / "plot.yml").exists()
    assert (tmp_path / "plot_patterns.yml").exists()
    # narrative_patterns.yml is not written to project root by default (artifact mode)
    assert not (tmp_path / "narrative_patterns.yml").exists()
    assert (tmp_path / ".fabulae-create" / "characters_plan.yml").exists()
    assert (tmp_path / ".fabulae-create" / "plot_outline.yml").exists()
    assert (tmp_path / ".fabulae-create" / "plot_patterns.yml").exists()
    assert (tmp_path / ".fabulae-create" / "narrative_patterns.yml").exists()
    assert (tmp_path / ".fabulae-create" / "plot_pattern_assignments.yml").exists()


def test_generate_project_retries_on_validation_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language=None, pov="third")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    invalid_plan = CharacterPlanOutput(
        characters=[
            CharacterPlanItem(id="hero", name="Hero"),
            CharacterPlanItem(id="hero", name="Clone"),
        ]
    )
    fixed_plan = CharacterPlanOutput(
        characters=[
            CharacterPlanItem(id="hero", name="Hero"),
            CharacterPlanItem(id="ally", name="Ally"),
        ]
    )

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [invalid_plan, fixed_plan],
        CharacterOutput: cast(
            list[object],
            [
                CharacterOutput(id="hero", name="Hero"),
                CharacterOutput(id="ally", name="Ally"),
            ],
        ),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }

    prompts: list[str] = []

    class DummyAgentWithPrompt(DummyAgent):
        async def run(self, *args: object, **kwargs: object) -> DummyResult:
            user_prompt = cast(str, args[0]) if args else cast(str, kwargs.get("user_prompt", ""))
            prompts.append(user_prompt)
            return DummyResult(self._output)

    def fake_create_agent(result_type: type[object], _prompt: str, _config: LLMConfig) -> DummyAgentWithPrompt:
        queue = outputs_by_type.get(result_type)
        if not queue:
            raise AssertionError(f"Unexpected output type or empty queue: {result_type}")
        return DummyAgentWithPrompt(queue.pop(0))

    monkeypatch.setattr(create_service, "create_agent", fake_create_agent)
    monkeypatch.setattr(create_service, "detect_language", lambda _text: (None, None))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    assert any("Fix this error" in prompt for prompt in prompts)


def test_plot_pattern_assignment_requires_required_beats(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    invalid_assignment = PlotPatternAssignmentOutput(
        plot_pattern=plot_patterns.plot_patterns[0].id,
        plot_pattern_beats=[
            PlotPatternBeatAssignmentOutput(
                type=plot_patterns.plot_patterns[0].required_beats[0].type,
                scene=outline.scenes[0].id,
            )
        ],
    )
    valid_assignment = _plot_pattern_assignment(outline, plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [invalid_assignment, valid_assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, valid_assignment)),
    }

    prompts: list[str] = []

    class DummyAgentWithPrompt(DummyAgent):
        async def run(self, *args: object, **kwargs: object) -> DummyResult:
            user_prompt = cast(str, args[0]) if args else cast(str, kwargs.get("user_prompt", ""))
            prompts.append(user_prompt)
            return DummyResult(self._output)

    def fake_create_agent(result_type: type[object], _prompt: str, _config: LLMConfig) -> DummyAgentWithPrompt:
        queue = outputs_by_type.get(result_type)
        if not queue:
            raise AssertionError(f"Unexpected output type or empty queue: {result_type}")
        return DummyAgentWithPrompt(queue.pop(0))

    monkeypatch.setattr(create_service, "create_agent", fake_create_agent)
    monkeypatch.setattr(create_service, "detect_language", lambda _text: (None, None))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(narrative_patterns_mode="artifact"),
        )
    )

    assert any("Fix this error" in prompt for prompt in prompts)


def test_plot_pattern_consistency_warns_after_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    invalid_plot_patterns = PlotPatternsOutput(
        plot_patterns=[
            PlotPatternOutput(
                id="three-act",
                name="Three-Act",
                description="Classic rise-fall arc.",
                roles=[PlotPatternRoleOutput(id="protagonist", description="drives the central goal")],
                required_beats=[
                    PlotPatternBeatOutput(type="inciting-incident", description="a shift"),
                    PlotPatternBeatOutput(type="climax", description="a shift"),
                ],
            )
        ]
    )
    assignment = _plot_pattern_assignment(outline, invalid_plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [invalid_plot_patterns, invalid_plot_patterns, invalid_plot_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, invalid_plot_patterns, assignment)),
    }

    def fake_create_agent(result_type: type[object], _prompt: str, _config: LLMConfig) -> DummyAgent:
        queue = outputs_by_type.get(result_type)
        if not queue:
            raise AssertionError(f"Unexpected output type or empty queue: {result_type}")
        return DummyAgent(queue.pop(0))

    warnings: list[str] = []

    monkeypatch.setattr(create_service, "create_agent", fake_create_agent)
    monkeypatch.setattr(create_service, "detect_language", lambda _text: (None, None))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            progress=warnings.append,
        )
    )

    assert any("Plot pattern consistency" in warning for warning in warnings)


def test_narrative_pattern_id_conflict_retries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    assignment = _plot_pattern_assignment(outline, plot_patterns)
    conflict_id = plot_patterns.plot_patterns[0].id
    invalid_narrative_patterns = NarrativePatternsOutput(
        narrative_patterns=[
            NarrativePatternOutput(
                id=conflict_id,
                name="Conflicting Pattern",
                description="Conflicts with plot pattern id.",
                plot_pattern=conflict_id,
                roles=[NarrativeRoleOutput(id="observer", description="filters tone")],
            )
        ]
    )
    valid_narrative_patterns = _narrative_patterns(plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [invalid_narrative_patterns, valid_narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }

    prompts: list[str] = []

    class DummyAgentWithPrompt(DummyAgent):
        async def run(self, *args: object, **kwargs: object) -> DummyResult:
            user_prompt = cast(str, args[0]) if args else cast(str, kwargs.get("user_prompt", ""))
            prompts.append(user_prompt)
            return DummyResult(self._output)

    def fake_create_agent(result_type: type[object], _prompt: str, _config: LLMConfig) -> DummyAgentWithPrompt:
        queue = outputs_by_type.get(result_type)
        if not queue:
            raise AssertionError(f"Unexpected output type or empty queue: {result_type}")
        return DummyAgentWithPrompt(queue.pop(0))

    monkeypatch.setattr(create_service, "create_agent", fake_create_agent)
    monkeypatch.setattr(create_service, "detect_language", lambda _text: (None, None))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(narrative_patterns_mode="artifact"),
        )
    )

    assert any("Fix this error" in prompt for prompt in prompts)


def test_generate_project_normalizes_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = CharacterPlanOutput(
        characters=[
            CharacterPlanItem(id="Hero One", name="Hero", role="protagonist"),
            CharacterPlanItem(id="Side Friend", name="Friend", role="ally"),
        ]
    )
    character_outputs = [
        CharacterOutput(id="Hero One", name="Hero", role="protagonist"),
        CharacterOutput(id="Side Friend", name="Friend", role="ally"),
    ]
    world_plan = WorldPlanOutput(
        setting="Setting",
        facts=[
            WorldFactPlanItem(id="Dr. Voss Lab", type="location", name="Dr. Voss Lab"),
            WorldFactPlanItem(id="Sensory Hurdles", type="object", name="Hurdles"),
        ],
    )
    world_fact_outputs = [
        WorldFactOutput(id="Dr. Voss Lab", type="location", name="Dr. Voss Lab"),
        WorldFactOutput(id="Sensory Hurdles", type="object", name="Hurdles"),
    ]
    outline = PlotOutlineOutput(
        format="short-story",
        premise="A premise.",
        scenes=[
            OutlineSceneOutput(id="Scene One", summary="Opening.", beat_count=3),
            OutlineSceneOutput(id="Scene Two", summary="Next.", beat_count=3),
        ],
        scene_ids=["Scene One", "Scene Two"],
    )
    plot_patterns = PlotPatternsOutput(
        plot_patterns=[
            PlotPatternOutput(
                id="Hero Journey",
                name="Hero Journey",
                description="Classic arc.",
                roles=[PlotPatternRoleOutput(id="narrator", description="narrates the tale")],
                required_beats=[
                    PlotPatternBeatOutput(type="call-to-adventure", description="call to adventure"),
                    PlotPatternBeatOutput(type="return-home", description="return"),
                ],
            )
        ]
    )
    narrative_patterns = NarrativePatternsOutput(
        narrative_patterns=[
            NarrativePatternOutput(
                id="Poet Voice",
                name="Poet Voice",
                description="Poetic narrator.",
                plot_pattern="Hero Journey",
                roles=[NarrativeRoleOutput(id="observer", description="observes")],
            )
        ]
    )
    assignment = _plot_pattern_assignment(outline, plot_patterns)
    scene_outputs = [
        SceneOutput(
            id="Scene One",
            summary="Opening.",
            location="Dr. Voss Lab",
            world_fact_ids=["Sensory Hurdles"],
            beats=[
                BeatOutput(id="beat-01", kind="call-to-adventure"),
                BeatOutput(id="beat-02", kind="turn"),
                BeatOutput(id="beat-03", kind="payoff"),
            ],
        ),
        SceneOutput(
            id="Scene Two",
            summary="Next.",
            beats=[
                BeatOutput(id="beat-04", kind="return-home"),
                BeatOutput(id="beat-05", kind="turn"),
                BeatOutput(id="beat-06", kind="payoff"),
            ],
        ),
    ]

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], character_outputs),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], world_fact_outputs),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(narrative_patterns_mode="artifact"),
        )
    )

    world_data = load_yaml_file(tmp_path / "world.yml")
    plot_data = load_yaml_file(tmp_path / "plot.yml")
    patterns_data = load_yaml_file(tmp_path / "plot_patterns.yml")
    narrative_data = load_yaml_file(tmp_path / ".fabulae-create" / "narrative_patterns.yml")
    world_ids = {fact["id"] for fact in cast(list[dict[str, object]], world_data.get("facts", []))}
    assert "dr-voss-lab" in world_ids
    assert "sensory-hurdles" in world_ids
    pattern_ids = {
        pattern["id"]
        for pattern in cast(list[dict[str, object]], patterns_data.get("plot_patterns", []))
    }
    assert "hero-journey" in pattern_ids
    narrative_ids = {
        pattern["id"]
        for pattern in cast(list[dict[str, object]], narrative_data.get("narrative_patterns", []))
    }
    assert "poet-voice" in narrative_ids
    scenes = cast(list[dict[str, object]], plot_data["scenes"])
    assert scenes[0]["location"] == "dr-voss-lab"
    assert scenes[0]["world_fact_ids"] == ["sensory-hurdles"]


def test_world_fact_generation_overrides_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    world_fact_outputs = _world_fact_outputs(world_plan)
    world_fact_outputs[0] = WorldFactOutput(
        id="wrong-id",
        type=world_fact_outputs[0].type,
        name=world_fact_outputs[0].name,
        facts=world_fact_outputs[0].facts,
    )
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], world_fact_outputs),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    world_data = load_yaml_file(tmp_path / "world.yml")
    world_ids = {fact["id"] for fact in cast(list[dict[str, object]], world_data.get("facts", []))}
    assert world_plan.facts[0].id in world_ids


def test_character_generation_overrides_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    character_outputs = _character_outputs(character_plan)
    character_outputs[0] = CharacterOutput(
        id="wrong-id",
        name=character_outputs[0].name,
        role=character_outputs[0].role,
    )
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], character_outputs),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    characters_data = load_yaml_file(tmp_path / "characters.yml")
    character_ids = {
        character["id"]
        for character in cast(list[dict[str, object]], characters_data.get("characters", []))
    }
    assert character_plan.characters[0].id in character_ids


def test_scene_generation_overrides_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)
    scene_outputs = _scene_outputs(outline, plot_patterns, assignment)
    scene_outputs[0] = scene_outputs[0].model_copy(update={"id": "wrong-scene"})

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    plot_data = load_yaml_file(tmp_path / "plot.yml")
    plot_scene_ids = {scene["id"] for scene in cast(list[dict[str, object]], plot_data.get("scenes", []))}
    assert outline.scenes[0].id in plot_scene_ids


def test_scene_generation_overrides_beat_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)
    scene_outputs = _scene_outputs(outline, plot_patterns, assignment)
    scene_outputs[0] = scene_outputs[0].model_copy(
        update={
            "beats": [
                BeatOutput(id="wrong-beat-1", kind=plot_patterns.plot_patterns[0].required_beats[0].type),
                BeatOutput(id="wrong-beat-2", kind="turn"),
                BeatOutput(id="wrong-beat-3", kind="payoff"),
            ]
        }
    )

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    plot_data = load_yaml_file(tmp_path / "plot.yml")
    scenes = cast(list[dict[str, object]], plot_data.get("scenes", []))
    first_scene = scenes[0]
    beat_ids = [beat["id"] for beat in cast(list[dict[str, object]], first_scene.get("beats", []))]
    expected_ids = [
        f"{outline.scenes[0].id}-beat-01",
        f"{outline.scenes[0].id}-beat-02",
        f"{outline.scenes[0].id}-beat-03",
    ]
    assert beat_ids == expected_ids


def test_scene_generation_filters_unknown_characters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)
    scene_outputs = _scene_outputs(outline, plot_patterns, assignment)
    scene_outputs[0] = scene_outputs[0].model_copy(
        update={"characters": [character_plan.characters[0].id, "unknown-char"]}
    )

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    plot_data = load_yaml_file(tmp_path / "plot.yml")
    scenes = cast(list[dict[str, object]], plot_data.get("scenes", []))
    first_scene = scenes[0]
    assert first_scene["characters"] == [character_plan.characters[0].id]


def test_fragment_generation_overrides_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("micro-prose")
    world_plan = _world_plan("micro-prose")
    fragment_plan = _fragment_plan()
    fragment_outputs = _fragment_outputs(fragment_plan)
    fragment_outputs[0] = fragment_outputs[0].model_copy(update={"id": "wrong-frag"})

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        FragmentPlanOutput: [fragment_plan],
        FragmentOutput: cast(list[object], fragment_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "micro-prose",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    plot_data = load_yaml_file(tmp_path / "plot.yml")
    fragment_ids = {
        fragment["id"]
        for fragment in cast(list[dict[str, object]], plot_data.get("fragments", []))
    }
    assert fragment_plan.fragments[0].id in fragment_ids


def test_stanza_generation_overrides_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("poem")
    world_plan = _world_plan("poem")
    poem_plan = _poem_plan()
    stanza_outputs = _stanza_outputs(poem_plan)
    stanza_outputs[0] = stanza_outputs[0].model_copy(update={"id": "wrong-stanza"})

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PoemPlanOutput: [poem_plan],
        StanzaOutput: cast(list[object], stanza_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "poem",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    plot_data = load_yaml_file(tmp_path / "plot.yml")
    stanza_ids = {
        stanza["id"]
        for stanza in cast(list[dict[str, object]], plot_data.get("stanzas", []))
    }
    assert poem_plan.stanzas[0].id in stanza_ids


def test_soft_count_range_accepts_extended_upper_bound() -> None:
    warning = create_service._soft_count_warning("Lines", 22, (3, 18))
    assert warning is None


def test_soft_count_range_rejects_overflow() -> None:
    warning = create_service._soft_count_warning("Lines", 28, (3, 18))
    assert warning is not None


def test_soft_count_range_allows_zero_when_min_is_zero() -> None:
    warning = create_service._soft_count_warning("Fragments", 0, (0, 3))
    assert warning is None


def test_soft_count_range_rejects_above_soft_max_when_min_is_zero() -> None:
    warning = create_service._soft_count_warning("Fragments", 6, (0, 3))
    assert warning is not None


def test_create_warns_but_does_not_fail_on_scene_count(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("novella")
    world_plan = _world_plan("novella")
    outline = PlotOutlineOutput(
        format="novella",
        premise="A premise.",
        scenes=[
            OutlineSceneOutput(id=f"scene-{index+1:02d}", summary="Scene", beat_count=2)
            for index in range(12)
        ],
        scene_ids=[f"scene-{index+1:02d}" for index in range(12)],
    )
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)
    scene_outputs = _scene_outputs(outline, plot_patterns, assignment)
    messages: list[str] = []

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "novella",
            LLMConfig(),
            output_dir=tmp_path,
            progress=messages.append,
        )
    )

    assert any("Warning:" in message for message in messages)


def test_create_warns_on_narrative_world_conflicts(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    assignment = _plot_pattern_assignment(outline, plot_patterns)
    narrative_patterns = NarrativePatternsOutput(
        narrative_patterns=[
            NarrativePatternOutput(
                id="noir-lens",
                name="Noir Lens",
                description="Hardboiled narration.",
                plot_pattern=plot_patterns.plot_patterns[0].id,
                roles=[NarrativeRoleOutput(id="observer", description="dry commentary")],
                tone="bright",
            )
        ]
    )
    scene_outputs = _scene_outputs(outline, plot_patterns, assignment)
    messages: list[str] = []

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            progress=messages.append,
            options=CreateOptions(
                narrative_patterns_mode="artifact",
                use_narrative_patterns_in_prompts=True,
            ),
        )
    )

    assert any("Narrative patterns differ from world metadata" in message for message in messages)


def test_create_narrative_patterns_off_does_not_write_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that narrative_patterns_mode='off' does not generate or write narrative patterns."""
    from fabulae.features.create.schemas import CreateOptions

    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        # No NarrativePatternsOutput in queue - should not be requested
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }
    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    options = CreateOptions(narrative_patterns_mode="off")
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=options,
        )
    )

    # Verify no narrative patterns files exist
    assert not (tmp_path / "narrative_patterns.yml").exists()
    assert not (tmp_path / ".fabulae-create" / "narrative_patterns.yml").exists()


def test_create_narrative_patterns_artifact_writes_only_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that narrative_patterns_mode='artifact' writes only to .fabulae-create/."""
    from fabulae.features.create.schemas import CreateOptions

    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }
    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    options = CreateOptions(narrative_patterns_mode="artifact")
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=options,
        )
    )

    # Verify artifact exists but root file does not
    assert (tmp_path / ".fabulae-create" / "narrative_patterns.yml").exists()
    assert not (tmp_path / "narrative_patterns.yml").exists()


def test_create_narrative_patterns_project_writes_both(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that narrative_patterns_mode='project' writes to both locations."""
    from fabulae.features.create.schemas import CreateOptions

    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }
    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    options = CreateOptions(narrative_patterns_mode="project")
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=options,
        )
    )

    # Verify both files exist
    assert (tmp_path / ".fabulae-create" / "narrative_patterns.yml").exists()
    assert (tmp_path / "narrative_patterns.yml").exists()


def test_create_use_narrative_patterns_in_prompts_controls_prompt_context(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that use_narrative_patterns_in_prompts controls whether patterns appear in prompts."""
    from fabulae.features.create.schemas import CreateOptions

    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline = _plot_outline("short-story")
    plot_patterns = _plot_patterns()
    narrative_patterns = _narrative_patterns(plot_patterns)
    assignment = _plot_pattern_assignment(outline, plot_patterns)

    captured_user_prompts: list[str] = []

    class CapturingAgent(DummyAgent):
        async def run(self, *_args: object, **_kwargs: object) -> DummyResult:
            if _args:
                captured_user_prompts.append(str(_args[0]))
            return DummyResult(self._output)

    def capture_agent(result_type: type[object], _prompt: str, _config: LLMConfig) -> CapturingAgent:
        queue = outputs_by_type.get(result_type)
        if not queue:
            raise AssertionError(f"Unexpected output type or empty queue: {result_type}")
        return CapturingAgent(queue.pop(0))

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        PlotPatternsOutput: [plot_patterns],
        NarrativePatternsOutput: [narrative_patterns],
        PlotOutlineOutput: [outline],
        PlotPatternAssignmentOutput: [assignment],
        SceneOutput: cast(list[object], _scene_outputs(outline, plot_patterns, assignment)),
    }
    monkeypatch.setattr(create_service, "create_agent", capture_agent)
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    # Test with use_narrative_patterns_in_prompts=True
    options = CreateOptions(narrative_patterns_mode="artifact", use_narrative_patterns_in_prompts=True)
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=options,
        )
    )

    # Check that narrative patterns appear in user prompts when enabled
    assert any("Narrative Patterns" in p for p in captured_user_prompts)
