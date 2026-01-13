"""Merge functions for enrichment output into existing project data."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import cast

from pydantic import ValidationError

from fabulae.features.create.ids import (
    generate_character_id,
    generate_location_id,
    generate_world_fact_id,
)
from fabulae.features.create.prompts import build_enrichment_prompt
from fabulae.features.create.schemas import (
    EnrichmentOutput,
    OutlineContentOutput,
    SceneContentOutput,
    StyleOutput,
)
from fabulae.features.create.variation import ProjectVariation
from fabulae.llm import LLMConfig, create_agent
from fabulae.models import Character, StoryShape, World, WorldFact

logger = logging.getLogger(__name__)


def merge_enrichment_characters(
    existing: list[Character],
    enrichment: EnrichmentOutput,
    next_character_index: int,
) -> tuple[list[Character], dict[str, str]]:
    """
    Merge new characters from enrichment into existing list.

    Args:
        existing: Existing characters in the project
        enrichment: Enrichment output with new characters
        next_character_index: Index to use for next character ID

    Returns:
        Tuple of (merged character list, mapping of temp_id -> assigned_id)
    """
    merged = list(existing)
    id_mapping: dict[str, str] = {}

    for char_output in enrichment.new_characters:
        assigned_id = generate_character_id(next_character_index)
        id_mapping[char_output.id] = assigned_id
        next_character_index += 1

        merged.append(
            Character(
                id=assigned_id,
                name=char_output.name,
                role=char_output.role,
                desire=char_output.desire,
                need=char_output.need,
                flaw=char_output.flaw,
                secret=char_output.secret,
                traits=char_output.traits,
            )
        )

    return merged, id_mapping


def merge_enrichment_world(
    existing: World,
    enrichment: EnrichmentOutput,
    next_location_index: int,
    next_world_fact_index: int,
) -> tuple[World, dict[str, str]]:
    """
    Merge new locations and world facts from enrichment.

    Args:
        existing: Existing World data
        enrichment: Enrichment output with new locations and world facts
        next_location_index: Index to use for next location ID
        next_world_fact_index: Index to use for next world fact ID

    Returns:
        Tuple of (merged World, mapping of temp_id -> assigned_id)
    """
    merged_facts = list(existing.facts)
    id_mapping: dict[str, str] = {}

    # Merge new locations
    for location_output in enrichment.new_locations:
        assigned_id = generate_location_id(next_location_index)
        id_mapping[location_output.id] = assigned_id
        next_location_index += 1

        merged_facts.append(
            WorldFact(
                id=assigned_id,
                type=location_output.type,
                name=location_output.name,
                facts=location_output.facts,
            )
        )

    # Merge new world facts
    for world_fact_output in enrichment.new_world_facts:
        assigned_id = generate_world_fact_id(next_world_fact_index)
        id_mapping[world_fact_output.id] = assigned_id
        next_world_fact_index += 1

        merged_facts.append(
            WorldFact(
                id=assigned_id,
                type=world_fact_output.type,
                name=world_fact_output.name,
                facts=world_fact_output.facts,
            )
        )

    return (
        World(
            setting=existing.setting,
            time_period=existing.time_period,
            tone=existing.tone,
            motifs=list(existing.motifs),
            facts=merged_facts,
        ),
        id_mapping,
    )


def merge_enrichment_plot(
    outline: OutlineContentOutput,
    enrichment: EnrichmentOutput,
    id_mapping: dict[str, str],
) -> OutlineContentOutput:
    """
    Apply subplot additions and foreshadowing to the outline.
    Updates scene summaries/goals to incorporate enrichment.

    Note: This doesn't change structure, just adds notes/context
    for scene expansion.

    Args:
        outline: The existing outline content
        enrichment: Enrichment output with subplots and foreshadowing
        id_mapping: Mapping of temporary IDs to assigned IDs

    Returns:
        Updated outline with enrichment notes incorporated
    """
    # Create updated scenes list
    updated_scenes: list[SceneContentOutput] = []

    for scene in outline.scenes:
        updated_summary = scene.summary or ""

        # Apply subplot additions
        for subplot in enrichment.subplot_additions:
            if scene.id in subplot.scenes_to_modify:
                if updated_summary and not updated_summary.endswith("\n"):
                    updated_summary += "\n"
                # Map involved character IDs to assigned IDs
                involved_chars = [id_mapping.get(char_id, char_id) for char_id in subplot.involved_characters]
                updated_summary += f"\n[Subplot] {subplot.description} (involves: {', '.join(involved_chars)})"

        # Apply foreshadowing elements
        for foreshadow in enrichment.foreshadowing_elements:
            # Map setup and payoff scene IDs if they are in the mapping
            setup_scene = id_mapping.get(foreshadow.setup_scene or "", foreshadow.setup_scene)
            payoff_scene = id_mapping.get(foreshadow.payoff_scene or "", foreshadow.payoff_scene)

            if setup_scene == scene.id:
                if updated_summary and not updated_summary.endswith("\n"):
                    updated_summary += "\n"
                payoff_note = f" (payoff in {payoff_scene})" if payoff_scene else ""
                updated_summary += f"\n[Foreshadowing setup] {foreshadow.description}{payoff_note}"
            elif payoff_scene == scene.id:
                if updated_summary and not updated_summary.endswith("\n"):
                    updated_summary += "\n"
                setup_note = f" (setup in {setup_scene})" if setup_scene else ""
                updated_summary += f"\n[Foreshadowing payoff] {foreshadow.description}{setup_note}"

        updated_scenes.append(
            SceneContentOutput(
                id=scene.id,
                chapter_id=scene.chapter_id,
                title=scene.title,
                summary=updated_summary if updated_summary != (scene.summary or "") else scene.summary,
                beat_count=scene.beat_count,
            )
        )

    return OutlineContentOutput(
        chapters=list(outline.chapters),
        scenes=updated_scenes,
    )


async def generate_enrichment(
    idea: str,
    format_name: str,
    style: StyleOutput,
    characters: list[Character],
    world: World,
    outline: OutlineContentOutput,
    config: LLMConfig,
    variation: ProjectVariation | None = None,
    shape: StoryShape | None = None,
    progress: Callable[[str], None] | None = None,
) -> EnrichmentOutput:
    """
    Generate enrichment suggestions for adding depth to the narrative.

    Calls the LLM to analyze the outline and suggest:
    - Secondary characters
    - Additional world-building
    - Subplot additions
    - Foreshadowing elements

    Args:
        idea: The original story idea.
        format_name: The narrative format (novel, novella, short-story, etc.).
        style: The style output from pass 1.
        characters: The existing characters from pass 1.
        world: The world data from pass 1.
        outline: The plot outline with chapters and scenes.
        config: LLM configuration.
        variation: Optional variation decisions that may contain subplot seeds.
        shape: Optional story shape for additional guidance.
        progress: Optional progress callback function.

    Returns:
        EnrichmentOutput with suggested additions.
        Returns empty EnrichmentOutput if LLM fails or validation errors occur.
    """
    if progress:
        progress("Generating narrative enrichment suggestions...")

    # Build the enrichment prompt
    prompt = build_enrichment_prompt(
        idea=idea,
        format_name=format_name,
        style=style,
        characters=characters,
        world=world,
        outline=outline,
        variation=variation,
        shape=shape,
    )

    try:
        # Create agent and run
        agent = create_agent(EnrichmentOutput, prompt, config)
        result = await agent.run(idea)
        enrichment = cast(EnrichmentOutput, result.output)

        if progress:
            enrichment_summary = []
            if enrichment.new_characters:
                enrichment_summary.append(f"{len(enrichment.new_characters)} new characters")
            if enrichment.new_locations:
                enrichment_summary.append(f"{len(enrichment.new_locations)} new locations")
            if enrichment.new_world_facts:
                enrichment_summary.append(f"{len(enrichment.new_world_facts)} new world facts")
            if enrichment.subplot_additions:
                enrichment_summary.append(f"{len(enrichment.subplot_additions)} subplots")
            if enrichment.foreshadowing_elements:
                enrichment_summary.append(f"{len(enrichment.foreshadowing_elements)} foreshadowing elements")

            if enrichment_summary:
                progress(f"Enrichment suggestions: {', '.join(enrichment_summary)}")
            else:
                progress("No enrichment suggestions generated")

        return enrichment

    except ValidationError as exc:
        logger.warning(f"Enrichment validation failed: {exc}")
        if progress:
            progress("Warning: Enrichment generation failed, continuing without enrichment")
        return EnrichmentOutput()

    except Exception as exc:
        logger.warning(f"Enrichment generation failed: {exc}")
        if progress:
            progress("Warning: Enrichment generation failed, continuing without enrichment")
        return EnrichmentOutput()
