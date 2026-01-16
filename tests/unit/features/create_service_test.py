from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import pytest

from fabulae.features.create.service import CreateProjectError, ErrorMode, StageResult, run_stage
from fabulae.llm import LLMConfig
from fabulae.llm.language_guard import LanguageGuardResult


def test_error_mode_values() -> None:
    assert [mode.value for mode in ErrorMode] == ["strict", "warn", "strict_then_warn"]


def test_stage_result_accepts_generic_types() -> None:
    int_result = StageResult(output=42, warnings=["note"], attempts=2)
    str_result = StageResult(output="ok")

    assert int_result.output == 42
    assert int_result.warnings == ["note"]
    assert int_result.attempts == 2
    assert str_result.output == "ok"
    assert str_result.warnings == []
    assert str_result.attempts == 1


class DummyResult:
    def __init__(self, output: object) -> None:
        self.output = output


class DummyAgent:
    def __init__(self, output: object, prompts: list[str] | None = None) -> None:
        self._output = output
        self._prompts = prompts

    async def run(self, prompt: str) -> DummyResult:
        if self._prompts is not None:
            self._prompts.append(prompt)
        return DummyResult(self._output)


def _fake_agent_factory(
    outputs_by_type: dict[type[object], list[object]],
    system_prompts: list[str] | None = None,
    user_prompts: list[str] | None = None,
) -> Callable[..., DummyAgent]:
    def factory(result_type: type[object], system_prompt: str, _config: LLMConfig) -> DummyAgent:
        queue = outputs_by_type.get(result_type)
        if not queue:
            raise AssertionError(f"Unexpected output type or empty queue: {result_type}")
        if system_prompts is not None:
            system_prompts.append(system_prompt)
        return DummyAgent(queue.pop(0), user_prompts)

    return factory


def test_run_stage_strict_mode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs_by_type: dict[type[object], list[object]] = {str: ["first", "second", "third"]}
    monkeypatch.setattr(
        "fabulae.features.create.service.create_agent",
        _fake_agent_factory(outputs_by_type),
    )

    with pytest.raises(CreateProjectError):
        asyncio.run(
            run_stage(
                result_type=str,
                system_prompt="sys",
                user_prompt="user",
                config=LLMConfig(),
                expected_language=None,
                extract_text=str,
                validate=lambda _output: "bad",
                error_mode=ErrorMode.STRICT,
            )
        )


def test_run_stage_warn_mode_returns_last_output(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs_by_type: dict[type[object], list[object]] = {str: ["first", "second", "third"]}
    monkeypatch.setattr(
        "fabulae.features.create.service.create_agent",
        _fake_agent_factory(outputs_by_type),
    )

    result = asyncio.run(
        run_stage(
            result_type=str,
            system_prompt="sys",
            user_prompt="user",
            config=LLMConfig(),
            expected_language=None,
            extract_text=str,
            validate=lambda _output: "still bad",
            warning_label="Stage",
            error_mode=ErrorMode.WARN,
        )
    )

    assert result.output == "third"
    assert any("Stage" in warning for warning in result.warnings)
    assert result.attempts == 3


def test_run_stage_strict_then_warn_with_warn_validate(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs_by_type: dict[type[object], list[object]] = {str: ["ok", "ok", "ok"]}
    monkeypatch.setattr(
        "fabulae.features.create.service.create_agent",
        _fake_agent_factory(outputs_by_type),
    )

    result = asyncio.run(
        run_stage(
            result_type=str,
            system_prompt="sys",
            user_prompt="user",
            config=LLMConfig(),
            expected_language=None,
            extract_text=str,
            validate=lambda _output: None,
            warn_validate=lambda _output: "soft",
            warning_label="Soft check",
            error_mode=ErrorMode.STRICT_THEN_WARN,
        )
    )

    assert result.output == "ok"
    assert result.warnings
    assert any("Soft check" in warning for warning in result.warnings)


def test_run_stage_retries_append_error(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs_by_type: dict[type[object], list[object]] = {str: ["bad", "good"]}
    prompts: list[str] = []
    monkeypatch.setattr(
        "fabulae.features.create.service.create_agent",
        _fake_agent_factory(outputs_by_type, user_prompts=prompts),
    )

    result = asyncio.run(
        run_stage(
            result_type=str,
            system_prompt="sys",
            user_prompt="user",
            config=LLMConfig(),
            expected_language=None,
            extract_text=str,
            validate=lambda output: None if output == "good" else "error",
            error_mode=ErrorMode.STRICT,
        )
    )

    assert result.output == "good"
    assert any("RETRY" in prompt for prompt in prompts)


def test_run_stage_reprompts_language_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    outputs_by_type: dict[type[object], list[object]] = {str: ["first", "second"]}
    system_prompts: list[str] = []
    monkeypatch.setattr(
        "fabulae.features.create.service.create_agent",
        _fake_agent_factory(outputs_by_type, system_prompts=system_prompts),
    )

    async def fake_run_with_language_guard(
        runner: Callable[[], Any],
        extract_text: Callable[[Any], str],
        expected_language: str | None,
        config: object | None = None,
        reprompt: Callable[[int], None] | None = None,
    ) -> tuple[Any, LanguageGuardResult]:
        await runner()
        if reprompt:
            reprompt(1)
        second = await runner()
        extract_text(second)
        return second, LanguageGuardResult(
            expected=expected_language or "",
            detected="",
            confidence=1.0,
            passed=True,
            skipped=False,
            reason="fake",
        )

    monkeypatch.setattr(
        "fabulae.features.create.service.run_with_language_guard",
        fake_run_with_language_guard,
    )

    result = asyncio.run(
        run_stage(
            result_type=str,
            system_prompt="sys",
            user_prompt="user",
            config=LLMConfig(),
            expected_language="en",
            extract_text=str,
            validate=lambda _output: None,
            error_mode=ErrorMode.STRICT,
        )
    )

    assert result.output == "second"
    assert any("Retry attempt: 1" in prompt for prompt in system_prompts)


def test_shared_utilities_can_be_imported_from_service() -> None:
    """Test that all shared utilities can be imported from service module."""
    from fabulae.features.create import service

    # Check that all expected exports are available
    assert hasattr(service, "CreateProjectError")
    assert hasattr(service, "ErrorMode")
    assert hasattr(service, "StageResult")
    assert hasattr(service, "SceneContext")
    assert hasattr(service, "run_stage")
    assert hasattr(service, "generate_project_from_idea")
    assert hasattr(service, "generate_project_from_idea_sync")


def test_no_circular_imports_from_pipelines() -> None:
    """Test that pipelines can be imported without circular import errors."""
    # This test ensures that when pipelines import from service,
    # there are no circular dependency issues
    try:
        from fabulae.features.create.pipelines import (
            micro_prose,  # noqa: F401
            poem,  # noqa: F401
            prose,  # noqa: F401
        )
    except ImportError as e:
        pytest.fail(f"Circular import or import error detected: {e}")


def test_create_project_error_can_be_imported_and_raised() -> None:
    """Test that CreateProjectError can be imported, raised and caught."""
    from fabulae.features.create.service import CreateProjectError

    with pytest.raises(CreateProjectError, match="Pipeline error"):
        raise CreateProjectError("Pipeline error")

    # Verify it's a RuntimeError subclass
    assert issubclass(CreateProjectError, RuntimeError)


def test_scene_context_can_be_instantiated() -> None:
    """Test SceneContext can be instantiated with all required fields."""
    from fabulae.features.create.schemas import OutlineSceneOutput, StyleOutput
    from fabulae.features.create.service import SceneContext

    # Create minimal required objects
    style = StyleOutput(pov="first", tense="past", voice="active", register="formal", language="english")

    scene_outline = OutlineSceneOutput(
        id="scene-01", summary="Test scene", beat_count=3, goal=None, conflict=None, outcome=None
    )

    context = SceneContext(
        idea="Test idea",
        format_name="novel",
        style=style,
        style_hint="POV: first; Tense: past",
        scene_outline=scene_outline,
        characters=[],
        world_facts=[],
        beat_template=None,
        available_characters=set(),
        available_world_facts=set(),
        available_location_ids=set(),
        available_character_summary="",
        available_location_summary="",
        world_summary="",
        prior_scene_summaries=[],
        beats_per_scene=(2, 5),
    )

    assert context.idea == "Test idea"
    assert context.format_name == "novel"
    assert context.style == style
    assert context.scene_outline == scene_outline


@pytest.mark.anyio
async def test_dispatcher_routes_novel_to_prose_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Test that format='novel' with full=True dispatches to generate_prose."""
    from pathlib import Path

    from fabulae.features.create.schemas import CreateOptions
    from fabulae.features.create.service import generate_project_from_idea
    from fabulae.models import Plot, Project, ProjectConfig

    called = {"prose": False, "micro_prose": False, "poem": False}

    async def fake_generate_prose(
        idea: str,
        format: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["prose"] = True
        assert format == "novel"
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="novel", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    monkeypatch.setattr("fabulae.features.create.pipelines.prose.generate_prose", fake_generate_prose)

    # Note: full=True is required to test prose pipeline routing (default is outline mode)
    result = await generate_project_from_idea(
        idea="A test novel",
        format_name="novel",
        config=LLMConfig(model="claude-3-haiku-20240307"),
        output_dir=tmp_path,
        options=CreateOptions(full=True),
    )

    assert called["prose"] is True
    assert called["micro_prose"] is False
    assert called["poem"] is False
    assert result.plot.format == "novel"


@pytest.mark.anyio
async def test_dispatcher_routes_novella_to_prose_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Test that format='novella' with full=True dispatches to generate_prose."""
    from pathlib import Path

    from fabulae.features.create.schemas import CreateOptions
    from fabulae.features.create.service import generate_project_from_idea
    from fabulae.models import Plot, Project, ProjectConfig

    called: dict[str, str | None] = {"format": None}

    async def fake_generate_prose(
        idea: str,
        format: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["format"] = format
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="novella", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    monkeypatch.setattr("fabulae.features.create.pipelines.prose.generate_prose", fake_generate_prose)

    # Note: full=True is required to test prose pipeline routing (default is outline mode)
    await generate_project_from_idea(
        idea="A test novella",
        format_name="novella",
        config=LLMConfig(model="claude-3-haiku-20240307"),
        output_dir=tmp_path,
        options=CreateOptions(full=True),
    )

    assert called["format"] == "novella"


@pytest.mark.anyio
async def test_dispatcher_routes_short_story_to_prose_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Test that format='short-story' with full=True dispatches to generate_prose."""
    from pathlib import Path

    from fabulae.features.create.schemas import CreateOptions
    from fabulae.features.create.service import generate_project_from_idea
    from fabulae.models import Plot, Project, ProjectConfig

    called: dict[str, str | None] = {"format": None}

    async def fake_generate_prose(
        idea: str,
        format: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["format"] = format
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="short-story", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    monkeypatch.setattr("fabulae.features.create.pipelines.prose.generate_prose", fake_generate_prose)

    # Note: full=True is required to test prose pipeline routing (default is outline mode)
    await generate_project_from_idea(
        idea="A test short story",
        format_name="short-story",
        config=LLMConfig(model="claude-3-haiku-20240307"),
        output_dir=tmp_path,
        options=CreateOptions(full=True),
    )

    assert called["format"] == "short-story"


@pytest.mark.anyio
async def test_dispatcher_routes_micro_prose_to_micro_prose_pipeline(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """Test that format='micro-prose' dispatches to generate_micro_prose."""
    from pathlib import Path

    from fabulae.features.create.schemas import CreateOptions
    from fabulae.features.create.service import generate_project_from_idea
    from fabulae.models import Plot, Project, ProjectConfig

    called = {"micro_prose": False}

    async def fake_generate_micro_prose(
        idea: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["micro_prose"] = True
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="micro-prose", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    monkeypatch.setattr("fabulae.features.create.pipelines.micro_prose.generate_micro_prose", fake_generate_micro_prose)

    result = await generate_project_from_idea(
        idea="A test micro-prose",
        format_name="micro-prose",
        config=LLMConfig(model="claude-3-haiku-20240307"),
        output_dir=tmp_path,
        options=CreateOptions(),
    )

    assert called["micro_prose"] is True
    assert result.plot.format == "micro-prose"


@pytest.mark.anyio
async def test_dispatcher_routes_poem_to_poem_pipeline(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    """Test that format='poem' dispatches to generate_poem."""
    from pathlib import Path

    from fabulae.features.create.schemas import CreateOptions
    from fabulae.features.create.service import generate_project_from_idea
    from fabulae.models import Plot, Project, ProjectConfig

    called = {"poem": False}

    async def fake_generate_poem(
        idea: str,
        options: CreateOptions,
        llm_config: Any,
        progress: Any = None,
        artifacts_dir: Path | None = None,
    ) -> Project:
        called["poem"] = True
        return Project(
            config=ProjectConfig(version="1.0.0", title="Test"),
            plot=Plot(format="poem", premise="Test premise"),
            characters=[],
            world=None,
            style=None,
        )

    monkeypatch.setattr("fabulae.features.create.pipelines.poem.generate_poem", fake_generate_poem)

    result = await generate_project_from_idea(
        idea="A test poem",
        format_name="poem",
        config=LLMConfig(model="claude-3-haiku-20240307"),
        output_dir=tmp_path,
        options=CreateOptions(),
    )

    assert called["poem"] is True
    assert result.plot.format == "poem"


@pytest.mark.anyio
async def test_dispatcher_validates_format_before_routing(tmp_path: Any) -> None:
    """Test that invalid formats are rejected before routing."""
    from fabulae.features.create.service import generate_project_from_idea

    with pytest.raises(ValueError, match="Unknown format"):
        await generate_project_from_idea(
            idea="A test story",
            format_name="invalid-format",  # type: ignore
            config=LLMConfig(model="claude-3-haiku-20240307"),
            output_dir=tmp_path,
        )
