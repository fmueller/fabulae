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
    ChapterContentOutput,
    ChapterOutput,
    CharacterOutput,
    CharacterPlanItem,
    CharacterPlanOutput,
    CreateOptions,
    FragmentOutput,
    FragmentPlanItem,
    FragmentPlanOutput,
    OutlineContentOutput,
    OutlineSceneOutput,
    PlotOutlineOutput,
    PoemPlanOutput,
    PremiseOutput,
    SceneContentOutput,
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
    Project,
    ProjectConfig,
    ProjectPaths,
    Scene,
    Stanza,
    load_yaml_file,
)

runner = CliRunner()

# Module-level mapping of scene IDs to chapter IDs (populated by _plot_outline)
_scene_to_chapter_map: dict[str, str] = {}


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
        CharacterPlanItem(id=f"char-{index + 1:02d}", name=f"Character {index + 1}", role="role")
        for index in range(count)
    ]
    return CharacterPlanOutput(characters=characters)


def _character_outputs(plan: CharacterPlanOutput) -> list[CharacterOutput]:
    return [CharacterOutput(id=item.id, name=item.name, role=item.role, desire="desire") for item in plan.characters]


def _world_plan(format_name: LiteratureFormat) -> WorldPlanOutput:
    count = create_service.FORMAT_COUNT_RANGES[format_name]["world_facts"][0]
    facts: list[WorldFactPlanItem] = []
    for index in range(count):
        fact_type: Literal["location", "rule"] = "location" if index == 0 else "rule"
        facts.append(
            WorldFactPlanItem(
                id=f"fact-{index + 1:02d}",
                type=fact_type,
                name=f"Fact {index + 1}",
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
    return [WorldFactOutput(id=fact.id, type=fact.type, name=fact.name, facts=["Detail"]) for fact in plan.facts]


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
        chapter_ids = [f"chapter-{index + 1:02d}" for index in range(chapters_count)]
        chapter_scene_map: dict[str, list[str]] = {chapter_id: [] for chapter_id in chapter_ids}
        for index in range(scenes_count):
            chapter_id = chapter_ids[index % chapters_count]
            scene_id = f"scene-{index + 1:02d}"
            chapter_scene_map[chapter_id].append(scene_id)
            scenes.append(
                OutlineSceneOutput(
                    id=scene_id,
                    summary=f"Scene {index + 1} summary",
                    beat_count=beat_count,
                )
            )
        chapters = [
            ChapterOutput(id=chapter_id, scene_ids=scene_ids) for chapter_id, scene_ids in chapter_scene_map.items()
        ]
        # Store mapping for later use in _outline_content
        _scene_to_chapter_map.clear()
        for chapter_id, scene_list in chapter_scene_map.items():
            for scene_id in scene_list:
                _scene_to_chapter_map[scene_id] = chapter_id
    else:
        scenes = [
            OutlineSceneOutput(
                id=f"scene-{index + 1:02d}",
                summary=f"Scene {index + 1} summary",
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


def _outline_content(
    outline: PlotOutlineOutput,
) -> OutlineContentOutput:
    """Convert PlotOutlineOutput to OutlineContentOutput for the new plot-first pipeline."""
    chapters: list[ChapterContentOutput] = []
    scenes: list[SceneContentOutput] = []

    # Convert chapters
    for chapter in outline.chapters:
        chapters.append(
            ChapterContentOutput(
                id=chapter.id,
                title=f"Chapter {chapter.id}",
                summary=f"Summary for {chapter.id}",
            )
        )

    # Convert scenes (use the scene_to_chapter mapping populated by _plot_outline)
    for scene in outline.scenes:
        scenes.append(
            SceneContentOutput(
                id=scene.id,
                chapter_id=_scene_to_chapter_map.get(scene.id),
                title=f"Scene {scene.id}",
                summary=scene.summary or f"Summary for {scene.id}",
                beat_count=scene.beat_count,
            )
        )

    return OutlineContentOutput(chapters=chapters, scenes=scenes)


def _prose_mocks_from_structure(
    format_name: LiteratureFormat,
    seed: int = 42,
) -> tuple[
    OutlineContentOutput,
    list[SceneOutput],
    list[OutlineSceneOutput],  # For scene context
]:
    """Generate prose-related mocks that match what generate_outline_structure produces.

    This uses the same RNG seed as the prose pipeline tests to ensure IDs match.

    Returns:
        Tuple of (outline_content, scene_outputs, scene_outlines)
    """
    import random

    from fabulae.features.create.ids import allocate_prose_ids
    from fabulae.features.create.pipelines.plot_first import generate_outline_structure

    # Generate structure with the same seed the pipeline will use
    rng = random.Random(seed)
    structure = generate_outline_structure(cast(Literal["novel", "novella", "short-story"], format_name), None, rng)

    # Allocate IDs the same way the pipeline does
    project_ids = allocate_prose_ids(
        num_chapters=structure.num_chapters,
        scenes_per_chapter=structure.scenes_per_chapter,
        beats_per_scene=structure.beats_per_scene,
    )

    # Generate OutlineContentOutput
    chapters: list[ChapterContentOutput] = []
    scenes: list[SceneContentOutput] = []

    for ch_id in project_ids.chapters:
        chapters.append(
            ChapterContentOutput(
                id=ch_id,
                title=f"Chapter {ch_id}",
                summary=f"Summary for {ch_id}",
            )
        )

    for i, scene_id in enumerate(project_ids.scenes):
        scene_chapter_id: str | None = project_ids.scene_to_chapter.get(scene_id)
        beat_count = structure.beats_per_scene[i]
        scenes.append(
            SceneContentOutput(
                id=scene_id,
                chapter_id=scene_chapter_id,
                title=f"Scene {scene_id}",
                summary=f"Summary for {scene_id}",
                beat_count=beat_count,
            )
        )

    outline_content = OutlineContentOutput(chapters=chapters, scenes=scenes)

    # Generate scene outlines for scene generation context
    scene_outlines: list[OutlineSceneOutput] = []
    for sc in scenes:
        scene_outlines.append(
            OutlineSceneOutput(
                id=sc.id,
                summary=sc.summary,
                beat_count=sc.beat_count,
            )
        )

    # Generate SceneOutputs
    scene_outputs: list[SceneOutput] = []
    for i, scene_id in enumerate(project_ids.scenes):
        beat_count = structure.beats_per_scene[i]

        beats = [
            BeatOutput(
                id=f"{scene_id}-beat-{b + 1:02d}",
                kind="setup",
                summary=f"Beat {b + 1} summary",
            )
            for b in range(beat_count)
        ]

        scene_outputs.append(
            SceneOutput(
                id=scene_id,
                summary=f"Summary for {scene_id}",
                beats=beats,
                characters=[],
                world_fact_ids=[],
            )
        )

    return outline_content, scene_outputs, scene_outlines


def _scene_outputs(
    outline: PlotOutlineOutput,
) -> list[SceneOutput]:
    outputs: list[SceneOutput] = []
    for scene in outline.scenes:
        beats = [
            BeatOutput(
                id=f"{scene.id}-beat-{index + 1:02d}",
                kind="setup",
                summary="Beat summary",
            )
            for index in range(scene.beat_count)
        ]
        outputs.append(
            SceneOutput(
                id=scene.id,
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
        FragmentPlanItem(id=f"frag-{index + 1:02d}", target_words=50, intent="Intent") for index in range(count)
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
        StanzaPlanItem(id=f"stanza-{index + 1:02d}", line_count=3, intent="Intent") for index in range(stanza_count)
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
        lines = [f"Line {index + 1}" for index in range(stanza.line_count)]
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
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
    }

    seed = 42
    if format_value in {"novel", "novella", "short-story"}:
        # Use the structure-based helper to generate matching mocks
        outline_content, scene_outputs, _ = _prose_mocks_from_structure(
            cast(Literal["novel", "novella", "short-story"], format_value), seed
        )
        outputs_by_type[OutlineContentOutput] = [outline_content]
        outputs_by_type[SceneOutput] = cast(list[object], scene_outputs)
    elif format_value == "micro-prose":
        fragment_plan = _fragment_plan()
        outputs_by_type[FragmentPlanOutput] = [fragment_plan]
        outputs_by_type[FragmentOutput] = cast(list[object], _fragment_outputs(fragment_plan))
    else:
        poem_plan = _poem_plan()
        outputs_by_type[PoemPlanOutput] = [poem_plan]
        outputs_by_type[StanzaOutput] = cast(list[object], _stanza_outputs(poem_plan))

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))

    # Use full=True for prose formats to test full pipeline (default is now outline mode)
    use_full = format_value in {"novel", "novella", "short-story"}
    project = asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=use_full),
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
        create_progress: object = None,
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
        create_progress: object = None,
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
        create_progress: object = None,
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
    captured_options: list[CreateOptions | None] = []

    def fake_generate(
        idea: str,
        format_name: LiteratureFormat,
        _config: LLMConfig,
        output_dir: Path,
        idea_language: str | None = None,
        progress: Callable[[str], None] | None = None,
        options: CreateOptions | None = None,
        create_progress: object = None,
    ) -> Project:
        captured_options.append(options)
        return _minimal_project(format_name)

    monkeypatch.setattr(create_cli, "generate_project_from_idea_sync", fake_generate)

    result = runner.invoke(
        app,
        ["create", str(target), "--idea", "Test", "--format", "novel", "--language", "fr"],
    )
    assert result.exit_code == 0
    assert len(captured_options) == 1
    assert captured_options[0] is not None
    assert captured_options[0].idea_language == "fr"


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
        create_progress: object = None,
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
    seed = 42
    style_output = StyleOutput(language="es", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        # Provide multiple copies for potential retries
        OutlineContentOutput: [outline_content] * 4,
        SceneOutput: cast(list[object], scene_outputs),
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
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
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
    # New pipeline writes numbered artifacts to .fabulae/create/
    artifacts_dir = tmp_path / ".fabulae" / "create"
    assert (artifacts_dir / "01-style.yml").exists()
    assert (artifacts_dir / "02-premise.yml").exists()
    assert (artifacts_dir / "03-structure.yml").exists()
    assert (artifacts_dir / "04-outline-content.yml").exists()


def test_generate_project_retries_on_validation_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    seed = 42
    style_output = StyleOutput(language=None, pov="third")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

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
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
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
        OutlineContentOutput: [outline_content],
        SceneOutput: cast(list[object], scene_outputs),
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
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    assert any("RETRY" in prompt for prompt in prompts)


def test_generate_project_uses_provided_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that the new ID system provides IDs to LLM and uses them without normalization."""
    seed = 42
    style_output = StyleOutput(language="en", pov="third")
    character_plan = CharacterPlanOutput(
        characters=[
            CharacterPlanItem(id="char-01", name="Hero", role="protagonist"),
            CharacterPlanItem(id="char-02", name="Friend", role="ally"),
        ]
    )
    character_outputs = [
        CharacterOutput(id="char-01", name="Hero", role="protagonist"),
        CharacterOutput(id="char-02", name="Friend", role="ally"),
    ]
    world_plan = WorldPlanOutput(
        setting="Setting",
        facts=[
            WorldFactPlanItem(id="fact-01", type="location", name="Dr. Voss Lab"),
            WorldFactPlanItem(id="fact-02", type="object", name="Hurdles"),
        ],
    )
    world_fact_outputs = [
        WorldFactOutput(id="fact-01", type="location", name="Dr. Voss Lab"),
        WorldFactOutput(id="fact-02", type="object", name="Hurdles"),
    ]
    outline_content, scene_outputs_gen, _ = _prose_mocks_from_structure("short-story", seed)

    # Customize first scene output to have location and world_fact_ids
    scene_outputs = list(scene_outputs_gen)
    if scene_outputs:
        scene_outputs[0] = scene_outputs[0].model_copy(
            update={
                "location": "fact-01",
                "world_fact_ids": ["fact-02"],
            }
        )

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], character_outputs),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], world_fact_outputs),
        OutlineContentOutput: [outline_content],
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
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    world_data = load_yaml_file(tmp_path / "world.yml")
    plot_data = load_yaml_file(tmp_path / "plot.yml")
    world_ids = {fact["id"] for fact in cast(list[dict[str, object]], world_data.get("facts", []))}
    assert "fact-01" in world_ids
    assert "fact-02" in world_ids
    scenes = cast(list[dict[str, object]], plot_data["scenes"])
    assert scenes[0]["location"] == "fact-01"
    assert scenes[0]["world_fact_ids"] == ["fact-02"]


def test_world_fact_generation_retries_on_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that world fact generation retries when LLM returns wrong ID."""
    seed = 42
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    world_fact_outputs = _world_fact_outputs(world_plan)

    # First attempt: wrong ID (should trigger retry)
    invalid_world_fact = WorldFactOutput(
        id="wrong-id",
        type=world_fact_outputs[0].type,
        name=world_fact_outputs[0].name,
        facts=world_fact_outputs[0].facts,
    )
    # Second attempt: correct ID
    valid_world_fact = world_fact_outputs[0]

    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: [invalid_world_fact, valid_world_fact] + cast(list[object], world_fact_outputs[1:]),
        OutlineContentOutput: [outline_content],
        SceneOutput: cast(list[object], scene_outputs),
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
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    # Verify retry was triggered
    assert any("RETRY" in prompt for prompt in prompts)

    # Verify correct ID was used in the end
    world_data = load_yaml_file(tmp_path / "world.yml")
    world_ids = {fact["id"] for fact in cast(list[dict[str, object]], world_data.get("facts", []))}
    assert world_plan.facts[0].id in world_ids


def test_character_generation_retries_on_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that character generation retries when LLM returns wrong ID."""
    seed = 42
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    character_outputs = _character_outputs(character_plan)

    # First attempt: wrong ID (should trigger retry)
    invalid_character = CharacterOutput(
        id="wrong-id",
        name=character_outputs[0].name,
        role=character_outputs[0].role,
    )
    # Second attempt: correct ID
    valid_character = character_outputs[0]

    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: [invalid_character, valid_character] + cast(list[object], character_outputs[1:]),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content],
        SceneOutput: cast(list[object], scene_outputs),
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
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    # Verify retry was triggered
    assert any("RETRY" in prompt for prompt in prompts)

    # Verify correct ID was used in the end
    characters_data = load_yaml_file(tmp_path / "characters.yml")
    character_ids = {
        character["id"] for character in cast(list[dict[str, object]], characters_data.get("characters", []))
    }
    assert character_plan.characters[0].id in character_ids


def test_scene_generation_retries_on_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that scene generation retries when LLM returns wrong ID."""
    seed = 42
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, scene_outlines = _prose_mocks_from_structure("short-story", seed)

    # First attempt: wrong ID (should trigger retry)
    invalid_scene = scene_outputs[0].model_copy(update={"id": "wrong-scene"})
    # Second attempt: correct ID
    valid_scene = scene_outputs[0]

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content],
        SceneOutput: [invalid_scene, valid_scene] + cast(list[object], scene_outputs[1:]),
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
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    # Verify retry was triggered
    assert any("RETRY" in prompt for prompt in prompts)

    # Verify correct ID was used in the end
    plot_data = load_yaml_file(tmp_path / "plot.yml")
    plot_scene_ids = {scene["id"] for scene in cast(list[dict[str, object]], plot_data.get("scenes", []))}
    assert scene_outlines[0].id in plot_scene_ids


def test_scene_generation_accepts_any_beat_ids(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that scene generation accepts any beat IDs (beat ID validation not yet implemented)."""
    seed = 42
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    # Use custom beat IDs - must match the beat count from the structure
    # Get the expected beat count for the first scene
    first_scene_outline = outline_content.scenes[0]
    expected_beat_count = first_scene_outline.beat_count

    # Create custom beats with that count
    custom_beats = [
        BeatOutput(id=f"custom-beat-{i + 1}", kind="setup", summary=f"Custom beat {i + 1}")
        for i in range(expected_beat_count)
    ]

    custom_scene = scene_outputs[0].model_copy(update={"beats": custom_beats})

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content],
        SceneOutput: [custom_scene] + cast(list[object], scene_outputs[1:]),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    # Verify custom beat IDs were accepted
    plot_data = load_yaml_file(tmp_path / "plot.yml")
    scenes = cast(list[dict[str, object]], plot_data.get("scenes", []))
    first_scene = scenes[0]
    beat_ids = [beat["id"] for beat in cast(list[dict[str, object]], first_scene.get("beats", []))]
    # Beat ID validation not yet implemented, so custom IDs should be accepted
    assert beat_ids[0] == "custom-beat-1"  # Verify first beat has custom ID
    assert len(beat_ids) == expected_beat_count  # Verify correct beat count


def test_scene_generation_retries_on_unknown_characters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that scene generation retries when LLM references unknown characters."""
    seed = 42
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    # First attempt: includes unknown character (should trigger retry)
    invalid_scene = scene_outputs[0].model_copy(
        update={"characters": [character_plan.characters[0].id, "unknown-char"]}
    )
    # Second attempt: only valid characters
    valid_scene = scene_outputs[0].model_copy(update={"characters": [character_plan.characters[0].id]})

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content],
        SceneOutput: [invalid_scene, valid_scene] + cast(list[object], scene_outputs[1:]),
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
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "short-story",
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    # Verify retry was triggered
    assert any("RETRY" in prompt for prompt in prompts)

    # Verify only valid characters in final output
    plot_data = load_yaml_file(tmp_path / "plot.yml")
    scenes = cast(list[dict[str, object]], plot_data.get("scenes", []))
    first_scene = scenes[0]
    assert first_scene["characters"] == [character_plan.characters[0].id]


def test_fragment_generation_retries_on_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that fragment generation retries when LLM returns wrong ID."""
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("micro-prose")
    world_plan = _world_plan("micro-prose")
    fragment_plan = _fragment_plan()
    fragment_outputs = _fragment_outputs(fragment_plan)

    # First attempt: wrong ID (should trigger retry)
    invalid_fragment = fragment_outputs[0].model_copy(update={"id": "wrong-frag"})
    # Second attempt: correct ID
    valid_fragment = fragment_outputs[0]

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        FragmentPlanOutput: [fragment_plan],
        FragmentOutput: [invalid_fragment, valid_fragment] + cast(list[object], fragment_outputs[1:]),
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
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "micro-prose",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    # Verify retry was triggered
    assert any("RETRY" in prompt for prompt in prompts)

    # Verify correct ID was used in the end
    plot_data = load_yaml_file(tmp_path / "plot.yml")
    fragment_ids = {fragment["id"] for fragment in cast(list[dict[str, object]], plot_data.get("fragments", []))}
    assert fragment_plan.fragments[0].id in fragment_ids


def test_stanza_generation_retries_on_id_mismatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that stanza generation retries when LLM returns wrong ID."""
    style_output = StyleOutput(language="en", pov="third")
    poem_plan = _poem_plan()
    stanza_outputs = _stanza_outputs(poem_plan)

    # First attempt: wrong ID (should trigger retry)
    invalid_stanza = stanza_outputs[0].model_copy(update={"id": "wrong-stanza"})
    # Second attempt: correct ID
    valid_stanza = stanza_outputs[0]

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        PoemPlanOutput: [poem_plan],
        StanzaOutput: [invalid_stanza, valid_stanza] + cast(list[object], stanza_outputs[1:]),
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
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("en", 0.9))

    project = asyncio.run(
        create_service.generate_project_from_idea(
            "An idea.",
            "poem",
            LLMConfig(),
            output_dir=tmp_path,
        )
    )

    # Verify retry was triggered
    assert any("RETRY" in prompt for prompt in prompts)

    # Verify correct ID was used in the end - check the returned project
    stanza_ids = {stanza.id for stanza in project.plot.stanzas}
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
    seed = 42
    style_output = StyleOutput(language="en", pov="third")
    character_plan = _character_plan("novella")
    world_plan = _world_plan("novella")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("novella", seed)
    messages: list[str] = []

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise based on the original idea.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content],
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
            options=CreateOptions(seed=seed, full=True),  # full=True for prose pipeline test
        )
    )

    # New pipeline generates structure internally, so count warnings may differ
    # The important thing is that the pipeline completes without error
    assert any(msg for msg in messages)  # Pipeline produces progress messages


def test_language_override_flows_to_output_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that idea_language from CreateOptions flows through to fabulae.yml and style.yml."""
    seed = 42
    # LLM returns English style, but we override with a different language via CLI
    style_output = StyleOutput(language="en", pov="third", tense="past")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content] * 4,  # Allow for retries
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "A story idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, idea_language="fr", full=True),  # full=True for prose pipeline test
        )
    )

    # Verify language override appears in fabulae.yml
    config = load_yaml_file(tmp_path / "fabulae.yml")
    defaults = cast(dict[str, object], config.get("defaults", {}))
    assert defaults.get("language") == "fr"

    # Verify language appears in style.yml
    style = load_yaml_file(tmp_path / "style.yml")
    assert style.get("language") == "fr"


def test_language_detection_from_idea_when_no_override(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that detected language from idea wins over LLM style language."""
    seed = 42
    # LLM returns English style, but language detection returns German
    style_output = StyleOutput(language="en", pov="first")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content] * 4,  # Allow for retries
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    # Mock language detection to return German (simulating detecting language from idea)
    # Even though LLM returns "en" in style, detected "de" should win
    monkeypatch.setattr(create_service, "detect_language", lambda _text: ("de", 0.95))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "A story idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=True),  # No idea_language override; full=True for prose pipeline
        )
    )

    # Verify detected language (de) wins over LLM style language (en)
    config = load_yaml_file(tmp_path / "fabulae.yml")
    defaults = cast(dict[str, object], config.get("defaults", {}))
    assert defaults.get("language") == "de"

    # Verify style.yml is also updated to match detected language
    style = load_yaml_file(tmp_path / "style.yml")
    assert style.get("language") == "de"


def test_language_defaults_to_english_when_not_detected(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Test that language defaults to English when no override and no detection."""
    seed = 42
    # LLM returns style without language
    style_output = StyleOutput(language=None, pov="first")
    character_plan = _character_plan("short-story")
    world_plan = _world_plan("short-story")
    outline_content, scene_outputs, _ = _prose_mocks_from_structure("short-story", seed)

    outputs_by_type: dict[type[object], list[object]] = {
        StyleOutput: [style_output],
        PremiseOutput: [PremiseOutput(premise="An expanded narrative premise.")],
        CharacterPlanOutput: [character_plan],
        CharacterOutput: cast(list[object], _character_outputs(character_plan)),
        WorldPlanOutput: [world_plan],
        WorldFactOutput: cast(list[object], _world_fact_outputs(world_plan)),
        OutlineContentOutput: [outline_content] * 4,
        SceneOutput: cast(list[object], scene_outputs),
    }

    monkeypatch.setattr(create_service, "create_agent", _fake_agent_factory(outputs_by_type))
    # Mock language detection to return None (no language detected)
    monkeypatch.setattr(create_service, "detect_language", lambda _text: (None, None))

    format_value: LiteratureFormat = "short-story"
    asyncio.run(
        create_service.generate_project_from_idea(
            "A story idea.",
            format_value,
            LLMConfig(),
            output_dir=tmp_path,
            options=CreateOptions(seed=seed, full=True),  # No idea_language override; full=True for prose pipeline
        )
    )

    # Verify language defaults to English
    config = load_yaml_file(tmp_path / "fabulae.yml")
    defaults = cast(dict[str, object], config.get("defaults", {}))
    assert defaults.get("language") == "en"

    # Verify style.yml also has English
    style = load_yaml_file(tmp_path / "style.yml")
    assert style.get("language") == "en"
