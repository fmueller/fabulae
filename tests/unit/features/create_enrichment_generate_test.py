"""Tests for generate_enrichment function."""

from __future__ import annotations

import pytest

from fabulae.features.create.enrichment import generate_enrichment
from fabulae.features.create.schemas import (
    ChapterContentOutput,
    CharacterOutput,
    EnrichmentOutput,
    OutlineContentOutput,
    SceneContentOutput,
    StyleOutput,
    SubplotAddition,
    WorldFactOutput,
)
from fabulae.features.create.variation import ProjectVariation, VariationConfig
from fabulae.llm import LLMConfig
from fabulae.models import Character, StoryShape, World, WorldFact


@pytest.fixture
def basic_style() -> StyleOutput:
    """Basic style output for testing."""
    return StyleOutput(
        language="en",
        pov="third",
        tense="past",
    )


@pytest.fixture
def basic_characters() -> list[Character]:
    """Basic character list for testing."""
    return [
        Character(id="character-01", name="Alice", role="protagonist"),
        Character(id="character-02", name="Bob", role="antagonist"),
    ]


@pytest.fixture
def basic_world() -> World:
    """Basic world for testing."""
    return World(
        setting="Medieval fantasy",
        time_period="Dark Ages",
        facts=[
            WorldFact(id="location-01", type="location", name="Castle"),
        ],
    )


@pytest.fixture
def basic_outline() -> OutlineContentOutput:
    """Basic outline for testing."""
    return OutlineContentOutput(
        chapters=[
            ChapterContentOutput(id="chapter-01", title="Chapter 1"),
        ],
        scenes=[
            SceneContentOutput(id="scene-01", chapter_id="chapter-01", summary="Opening scene", beat_count=3),
            SceneContentOutput(id="scene-02", chapter_id="chapter-01", summary="Middle scene", beat_count=2),
            SceneContentOutput(id="scene-03", chapter_id="chapter-01", summary="Closing scene", beat_count=2),
        ],
    )


@pytest.mark.anyio
async def test_generate_enrichment_returns_enrichment_output(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that generate_enrichment returns EnrichmentOutput."""

    # Mock the create_agent function to return a fake agent
    class FakeResult:
        def __init__(self, output: EnrichmentOutput) -> None:
            self.output = output

    class FakeAgent:
        async def run(self, prompt: str) -> FakeResult:
            return FakeResult(
                EnrichmentOutput(
                    new_characters=[
                        CharacterOutput(id="temp-char-1", name="Charlie", role="sidekick"),
                    ],
                    new_locations=[
                        WorldFactOutput(id="temp-loc-1", type="location", name="Forest", facts=["Dark"]),
                    ],
                )
            )

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    config = LLMConfig()
    result = await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
    )

    assert isinstance(result, EnrichmentOutput)
    assert len(result.new_characters) == 1
    assert result.new_characters[0].name == "Charlie"
    assert len(result.new_locations) == 1
    assert result.new_locations[0].name == "Forest"


@pytest.mark.anyio
async def test_generate_enrichment_handles_validation_errors_gracefully(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that generate_enrichment returns empty EnrichmentOutput on validation error."""

    class FakeAgent:
        async def run(self, prompt: str) -> None:
            from pydantic import ValidationError

            # Simulate a validation error
            raise ValidationError.from_exception_data(
                "EnrichmentOutput",
                [{"type": "value_error", "loc": ("new_characters",), "input": None}],
            )

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    config = LLMConfig()
    result = await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
    )

    # Should return empty EnrichmentOutput on validation error
    assert isinstance(result, EnrichmentOutput)
    assert len(result.new_characters) == 0
    assert len(result.new_locations) == 0
    assert len(result.new_world_facts) == 0
    assert len(result.subplot_additions) == 0
    assert len(result.foreshadowing_elements) == 0


@pytest.mark.anyio
async def test_generate_enrichment_handles_general_exceptions_gracefully(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that generate_enrichment returns empty EnrichmentOutput on general exception."""

    class FakeAgent:
        async def run(self, prompt: str) -> None:
            raise RuntimeError("LLM connection failed")

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    config = LLMConfig()
    result = await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
    )

    # Should return empty EnrichmentOutput on exception
    assert isinstance(result, EnrichmentOutput)
    assert len(result.new_characters) == 0
    assert len(result.new_locations) == 0


@pytest.mark.anyio
async def test_generate_enrichment_calls_progress_callback(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that generate_enrichment calls progress callback."""
    progress_messages: list[str] = []

    def progress_callback(msg: str) -> None:
        progress_messages.append(msg)

    class FakeResult:
        def __init__(self, output: EnrichmentOutput) -> None:
            self.output = output

    class FakeAgent:
        async def run(self, prompt: str) -> FakeResult:
            return FakeResult(
                EnrichmentOutput(
                    new_characters=[CharacterOutput(id="temp-1", name="Test")],
                    subplot_additions=[
                        SubplotAddition(
                            description="Test subplot",
                            involved_characters=["character-01"],
                            scenes_to_modify=["scene-01"],
                        )
                    ],
                )
            )

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    config = LLMConfig()
    await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
        progress=progress_callback,
    )

    assert len(progress_messages) >= 2
    assert progress_messages[0] == "Generating narrative enrichment suggestions..."
    assert "new characters" in progress_messages[1]
    assert "subplots" in progress_messages[1]


@pytest.mark.anyio
async def test_generate_enrichment_with_empty_response_returns_empty_enrichment(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that generate_enrichment handles empty response correctly."""

    class FakeResult:
        def __init__(self, output: EnrichmentOutput) -> None:
            self.output = output

    class FakeAgent:
        async def run(self, prompt: str) -> FakeResult:
            return FakeResult(EnrichmentOutput())

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    config = LLMConfig()
    result = await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
    )

    assert isinstance(result, EnrichmentOutput)
    assert len(result.new_characters) == 0
    assert len(result.new_locations) == 0
    assert len(result.new_world_facts) == 0
    assert len(result.subplot_additions) == 0
    assert len(result.foreshadowing_elements) == 0


@pytest.mark.anyio
async def test_generate_enrichment_with_variation_and_shape(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that generate_enrichment accepts variation and shape parameters."""

    class FakeResult:
        def __init__(self, output: EnrichmentOutput) -> None:
            self.output = output

    class FakeAgent:
        async def run(self, prompt: str) -> FakeResult:
            return FakeResult(EnrichmentOutput())

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    variation = ProjectVariation(
        scene_variations=[],
        subplot_seeds=["A romance subplot"],
        config=VariationConfig(),
    )
    shape = StoryShape(
        id="three-act",
        name="Three Act",
        description="Classic three-act structure",
    )

    config = LLMConfig()
    result = await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
        variation=variation,
        shape=shape,
    )

    assert isinstance(result, EnrichmentOutput)


@pytest.mark.anyio
async def test_generate_enrichment_reports_no_suggestions_when_empty(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that progress callback reports when no suggestions are generated."""
    progress_messages: list[str] = []

    def progress_callback(msg: str) -> None:
        progress_messages.append(msg)

    class FakeResult:
        def __init__(self, output: EnrichmentOutput) -> None:
            self.output = output

    class FakeAgent:
        async def run(self, prompt: str) -> FakeResult:
            return FakeResult(EnrichmentOutput())

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    config = LLMConfig()
    await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
        progress=progress_callback,
    )

    assert len(progress_messages) == 2
    assert progress_messages[0] == "Generating narrative enrichment suggestions..."
    assert progress_messages[1] == "No enrichment suggestions generated"


@pytest.mark.anyio
async def test_generate_enrichment_reports_warning_on_failure(
    basic_style: StyleOutput,
    basic_characters: list[Character],
    basic_world: World,
    basic_outline: OutlineContentOutput,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that progress callback reports warning on failure."""
    progress_messages: list[str] = []

    def progress_callback(msg: str) -> None:
        progress_messages.append(msg)

    class FakeAgent:
        async def run(self, prompt: str) -> None:
            raise RuntimeError("Test failure")

    def mock_create_agent(result_type: type, system_prompt: str, config: LLMConfig) -> FakeAgent:
        return FakeAgent()

    monkeypatch.setattr("fabulae.features.create.enrichment.create_agent", mock_create_agent)

    config = LLMConfig()
    await generate_enrichment(
        idea="A fantasy adventure",
        format_name="novel",
        style=basic_style,
        characters=basic_characters,
        world=basic_world,
        outline=basic_outline,
        config=config,
        progress=progress_callback,
    )

    assert len(progress_messages) == 2
    assert progress_messages[0] == "Generating narrative enrichment suggestions..."
    assert "Warning" in progress_messages[1]
    assert "failed" in progress_messages[1]
