"""Tests for story shape selector."""

import asyncio
from collections.abc import Coroutine
from typing import TypeVar
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from fabulae.features.create.shapes.selector import (
    DEFAULT_SHAPE,
    ShapeSelectionOutput,
    select_shape_for_idea,
)
from fabulae.llm import LLMConfig
from fabulae.models import StoryShape

T = TypeVar("T")


def run_async(coro: Coroutine[object, object, T]) -> T:
    """Helper to run async functions in sync tests."""
    return asyncio.run(coro)


@pytest.fixture
def mock_agent() -> MagicMock:
    """Create a mock agent for testing."""
    agent = MagicMock()
    agent.run = AsyncMock()
    return agent


@pytest.fixture
def llm_config() -> LLMConfig:
    """Create a test LLM config."""
    return LLMConfig(model="test-model", temperature=0.7)


class TestSelectShapeForIdea:
    """Tests for select_shape_for_idea()."""

    def test_selection_with_betrayal_themed_idea(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test selection with betrayal-themed idea returns betrayal-arc."""
        # Setup mock to return betrayal-arc
        mock_result = MagicMock()
        mock_result.output = ShapeSelectionOutput(
            shape_id="betrayal-arc", reasoning="The story centers on broken trust"
        )
        mock_agent.run.return_value = mock_result

        # Patch create_agent to return our mock
        def mock_create_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        idea = "A trusted friend betrays the protagonist, revealing they were working for the enemy all along"
        shape = run_async(select_shape_for_idea(idea, llm_config))

        # Verify result
        assert isinstance(shape, StoryShape)
        assert shape.id == "betrayal-arc"
        assert shape.name == "Betrayal Arc"

        # Verify agent was called
        mock_agent.run.assert_called_once_with(idea)

    def test_selection_with_mystery_idea(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test selection with mystery idea returns mystery-reveal."""
        # Setup mock to return mystery-reveal
        mock_result = MagicMock()
        mock_result.output = ShapeSelectionOutput(
            shape_id="mystery-reveal", reasoning="The story is about uncovering hidden truth"
        )
        mock_agent.run.return_value = mock_result

        # Patch create_agent to return our mock
        def mock_create_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        idea = "A detective investigates a murder where everyone has secrets to hide"
        shape = run_async(select_shape_for_idea(idea, llm_config))

        # Verify result
        assert isinstance(shape, StoryShape)
        assert shape.id == "mystery-reveal"
        assert shape.name == "Mystery Reveal"

        # Verify agent was called
        mock_agent.run.assert_called_once_with(idea)

    def test_fallback_when_llm_returns_invalid_shape(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to default shape when LLM returns invalid shape ID."""
        # Setup mock to return non-existent shape
        mock_result = MagicMock()
        mock_result.output = ShapeSelectionOutput(shape_id="nonexistent-shape", reasoning="This shape doesn't exist")
        mock_agent.run.return_value = mock_result

        # Patch create_agent to return our mock
        def mock_create_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        idea = "Some story idea"
        shape = run_async(select_shape_for_idea(idea, llm_config))

        # Verify fallback to default shape
        assert isinstance(shape, StoryShape)
        assert shape.id == DEFAULT_SHAPE
        assert shape.id == "heros-journey"

    def test_fallback_when_llm_call_fails(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test fallback to default shape when LLM call raises exception."""
        # Setup mock to raise exception
        mock_agent.run.side_effect = RuntimeError("LLM service unavailable")

        # Patch create_agent to return our mock
        def mock_create_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        idea = "Some story idea"
        shape = run_async(select_shape_for_idea(idea, llm_config))

        # Verify fallback to default shape
        assert isinstance(shape, StoryShape)
        assert shape.id == DEFAULT_SHAPE
        assert shape.id == "heros-journey"

    def test_selection_with_coming_of_age_idea(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test selection with coming-of-age themed idea."""
        # Setup mock to return coming-of-age
        mock_result = MagicMock()
        mock_result.output = ShapeSelectionOutput(
            shape_id="coming-of-age", reasoning="The story focuses on maturation and growth"
        )
        mock_agent.run.return_value = mock_result

        # Patch create_agent to return our mock
        def mock_create_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        idea = "A teenager leaves home for the first time and learns hard truths about the world"
        shape = run_async(select_shape_for_idea(idea, llm_config))

        # Verify result
        assert isinstance(shape, StoryShape)
        assert shape.id == "coming-of-age"

    def test_selection_with_revenge_idea(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test selection with revenge-themed idea."""
        # Setup mock to return revenge-quest
        mock_result = MagicMock()
        mock_result.output = ShapeSelectionOutput(
            shape_id="revenge-quest", reasoning="The protagonist seeks vengeance for past wrongs"
        )
        mock_agent.run.return_value = mock_result

        # Patch create_agent to return our mock
        def mock_create_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        idea = "After their family is killed, the protagonist vows to hunt down those responsible"
        shape = run_async(select_shape_for_idea(idea, llm_config))

        # Verify result
        assert isinstance(shape, StoryShape)
        assert shape.id == "revenge-quest"

    def test_prompt_includes_all_available_shapes(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that the generated prompt includes all available shapes."""
        # Setup mock
        mock_result = MagicMock()
        mock_result.output = ShapeSelectionOutput(shape_id="heros-journey", reasoning="Default choice")
        mock_agent.run.return_value = mock_result

        # Capture the system prompt that was used to create the agent
        captured_prompt = None

        def mock_create_agent(result_type, system_prompt, config):  # type: ignore[no-untyped-def]
            nonlocal captured_prompt
            captured_prompt = system_prompt
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        run_async(select_shape_for_idea("Some idea", llm_config))

        # Verify prompt includes shape IDs
        assert captured_prompt is not None
        assert "betrayal-arc" in captured_prompt
        assert "mystery-reveal" in captured_prompt
        assert "heros-journey" in captured_prompt
        assert "coming-of-age" in captured_prompt
        assert "Available Story Shapes" in captured_prompt

    def test_selection_with_transformation_idea(
        self, mock_agent: MagicMock, llm_config: LLMConfig, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test selection with transformation-themed idea."""
        # Setup mock to return transformation
        mock_result = MagicMock()
        mock_result.output = ShapeSelectionOutput(
            shape_id="transformation", reasoning="The protagonist undergoes fundamental change"
        )
        mock_agent.run.return_value = mock_result

        # Patch create_agent to return our mock
        def mock_create_agent(*args, **kwargs):  # type: ignore[no-untyped-def]
            return mock_agent

        monkeypatch.setattr("fabulae.features.create.shapes.selector.create_agent", mock_create_agent)

        # Run selection
        idea = "A workaholic executive is forced to slow down after an accident and discovers what truly matters"
        shape = run_async(select_shape_for_idea(idea, llm_config))

        # Verify result
        assert isinstance(shape, StoryShape)
        assert shape.id == "transformation"


class TestShapeSelectionOutput:
    """Tests for ShapeSelectionOutput model."""

    def test_can_instantiate_with_valid_data(self) -> None:
        """Test that ShapeSelectionOutput can be instantiated with valid data."""
        output = ShapeSelectionOutput(shape_id="betrayal-arc", reasoning="Test reasoning")
        assert output.shape_id == "betrayal-arc"
        assert output.reasoning == "Test reasoning"

    def test_fields_are_required(self) -> None:
        """Test that both fields are required."""
        with pytest.raises(ValidationError):
            ShapeSelectionOutput()  # type: ignore[call-arg]
