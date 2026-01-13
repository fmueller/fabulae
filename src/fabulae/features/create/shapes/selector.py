"""Automatic story shape selection based on story ideas."""

from __future__ import annotations

from pydantic import BaseModel

from fabulae.llm import LLMConfig, create_agent
from fabulae.models import StoryShape
from fabulae.prompts import build_system_prompt, format_sections

from .loader import get_shape_ids, load_shape

DEFAULT_SHAPE = "heros-journey"


class ShapeSelectionOutput(BaseModel):
    """LLM output for shape selection."""

    shape_id: str
    reasoning: str


def _build_shape_selection_prompt(idea: str) -> str:
    """
    Build the prompt for shape selection.

    Args:
        idea: The user's story idea

    Returns:
        System prompt for the LLM
    """
    purpose = (
        "Analyze a story idea and select the most appropriate narrative structure (story shape). "
        "Choose the shape that best fits the core conflict, character dynamics, and thematic elements."
    )

    guidelines = [
        "Return valid JSON only (no markdown, no extra text).",
        "Choose from the available shape IDs listed below.",
        "Base your choice on the central dramatic question and character relationships.",
        "Provide brief reasoning for your selection.",
    ]

    # Get all available shape IDs
    available_shapes = get_shape_ids()

    # Build brief descriptions of each shape for the LLM
    shape_descriptions = []
    for shape_id in available_shapes:
        shape = load_shape(shape_id)
        # Create a one-line summary for the prompt
        shape_descriptions.append(f"- {shape_id}: {shape.description[:150]}...")

    schema = '{\n  "shape_id": "betrayal-arc",\n  "reasoning": "The idea centers on broken trust between characters"\n}'

    sections: dict[str, str] = {
        "Available Story Shapes": "\n".join(shape_descriptions),
        "Story Idea": idea,
        "Output Schema (JSON)": schema,
        "Notes": (
            "If the idea could fit multiple shapes, choose the one that matches the "
            "primary dramatic conflict. If uncertain, default to 'heros-journey'."
        ),
    }

    return build_system_prompt(purpose, guidelines) + "\n\n" + format_sections(sections)


async def select_shape_for_idea(idea: str, config: LLMConfig) -> StoryShape:
    """
    Auto-select an appropriate story shape based on the user's idea.

    This function uses an LLM to analyze the story idea and select the most
    appropriate narrative structure from the available story shapes.

    Args:
        idea: The user's story idea (free-form text)
        config: LLM configuration

    Returns:
        The selected StoryShape instance

    Raises:
        Exception: If LLM call fails or returns invalid data
    """
    # Build the selection prompt
    system_prompt = _build_shape_selection_prompt(idea)

    # Create agent for structured output
    agent = create_agent(ShapeSelectionOutput, system_prompt, config)

    # Run the LLM to get shape selection
    try:
        result = await agent.run(idea)
        selection: ShapeSelectionOutput = result.output

        # Validate that the selected shape exists
        available_shapes = get_shape_ids()
        if selection.shape_id not in available_shapes:
            # Fall back to default shape if invalid selection
            return load_shape(DEFAULT_SHAPE)

        # Load and return the selected shape
        return load_shape(selection.shape_id)

    except Exception:
        # If anything goes wrong, fall back to default shape
        return load_shape(DEFAULT_SHAPE)
