"""Poetry narrative pipeline for poem format.

This module implements the generation pipeline for poetry narratives,
featuring form-driven structure with stanzas and lines as primary units.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fabulae import __version__
from fabulae.features.create.ids import allocate_poem_ids
from fabulae.features.create.prompts import (
    build_poem_plan_prompt,
    build_stanza_prompt,
    build_style_prompt,
)
from fabulae.features.create.schemas import CreateOptions, PoemPlanOutput, StanzaOutput, StyleOutput
from fabulae.features.create.service import (
    FORMAT_COUNT_RANGES,
    CreateProjectError,
    ErrorMode,
    _build_user_prompt,
    run_stage,
)
from fabulae.features.create.validation import validate_id_unchanged
from fabulae.llm import LLMConfig
from fabulae.models import (
    GenerationMetadata,
    LiteratureFormat,
    Plot,
    Project,
    ProjectConfig,
    Stanza,
    Style,
)


async def generate_poem(
    idea: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    artifacts_dir: Path | None = None,
) -> Project:
    """Generate a complete poem project from an idea.

    This pipeline follows a form-focused approach:
    1. Generate Style (tone, voice, poetic form hints)
    2. Generate Poem Plan (structure, stanza count, form)
    3. Generate Stanzas (actual lines for each stanza)

    No story shapes or narrative structure - poems are form-driven
    (sonnet, haiku, free verse, etc.)

    Args:
        idea: The user's initial idea for the poem
        options: Creation options (variation, shape, etc.)
        llm_config: LLM configuration for generation
        artifacts_dir: Optional directory to save intermediate artifacts

    Returns:
        A complete Project with config, plot (with stanzas), and style populated.
        Characters, world, chapters, scenes, and fragments will be empty.

    Raises:
        CreateProjectError: If generation fails after retries
    """
    format_name: LiteratureFormat = "poem"
    count_ranges = FORMAT_COUNT_RANGES[format_name]
    stanza_range = count_ranges["stanzas"]
    line_range = count_ranges["lines"]

    # Step 1: Generate Style (tone, voice, poetic form hints)
    user_prompt_style = _build_user_prompt(idea, format_name)
    system_prompt_style = build_style_prompt(format_name)

    style_result = await run_stage(
        result_type=StyleOutput,
        system_prompt=system_prompt_style,
        user_prompt=user_prompt_style,
        config=llm_config,
        expected_language=None,
        extract_text=lambda s: s.language or "",
        error_mode=ErrorMode.STRICT,
    )
    style_output = style_result.output

    # Format style as hint string
    style_hint_parts = []
    if style_output.language:
        style_hint_parts.append(f"Language: {style_output.language}")
    if style_output.voice:
        style_hint_parts.append(f"Voice: {style_output.voice}")
    if style_output.register_:
        style_hint_parts.append(f"Register: {style_output.register_}")
    if style_output.constraints:
        style_hint_parts.append(f"Constraints: {', '.join(style_output.constraints)}")
    style_hint = "\n".join(style_hint_parts) if style_hint_parts else None

    # Step 2: Generate Poem Plan (structure, stanza count, form)
    system_prompt_plan = build_poem_plan_prompt(
        format_name=format_name,
        style_hint=style_hint,
        stanza_range=stanza_range,
        line_range=line_range,
    )
    user_prompt_plan = _build_user_prompt(idea, format_name)

    poem_plan_result = await run_stage(
        result_type=PoemPlanOutput,
        system_prompt=system_prompt_plan,
        user_prompt=user_prompt_plan,
        config=llm_config,
        expected_language=style_output.language,
        extract_text=lambda p: p.premise,
        error_mode=ErrorMode.STRICT,
    )
    poem_plan = poem_plan_result.output

    # Allocate sequential stanza IDs
    num_stanzas = len(poem_plan.stanzas)
    if num_stanzas == 0:
        raise CreateProjectError("Poem plan must contain at least one stanza")

    project_ids = allocate_poem_ids(num_stanzas)

    # Update stanza plan items with allocated IDs
    for idx, stanza_plan_item in enumerate(poem_plan.stanzas):
        stanza_plan_item.id = project_ids.stanzas[idx]

    # Step 3: Generate Stanzas (actual lines for each stanza)
    stanzas: list[Stanza] = []
    existing_stanzas_summary: list[str] = []

    for idx, stanza_plan_item in enumerate(poem_plan.stanzas):
        assigned_id = project_ids.stanzas[idx]

        # Build summary of existing stanzas
        existing_summary = "\n\n".join(existing_stanzas_summary) if existing_stanzas_summary else "None yet."

        # Build context for this stanza
        context: dict[str, object] = {
            "Stanza Plan": (
                f"ID: {stanza_plan_item.id}\n"
                f"Line Count: {stanza_plan_item.line_count}\n"
                f"Intent: {stanza_plan_item.intent or 'N/A'}"
            ),
            "Poem Form": poem_plan.poem_form or "free verse",
        }
        if poem_plan.poem_meter:
            context["Poem Meter"] = poem_plan.poem_meter
        if poem_plan.poem_rhyme_scheme:
            context["Poem Rhyme Scheme"] = poem_plan.poem_rhyme_scheme

        system_prompt_stanza = build_stanza_prompt(
            format_name=format_name,
            style_hint=style_hint,
            existing_summary=existing_summary,
            assigned_id=assigned_id,
        )
        user_prompt_stanza = _build_user_prompt(idea, format_name, context)

        def validate_stanza(
            stanza_output: StanzaOutput,
            expected_id: str = assigned_id,
            expected_line_count: int = stanza_plan_item.line_count,
        ) -> str | None:
            # Validate ID unchanged
            id_error = validate_id_unchanged(stanza_output.id, expected_id)
            if id_error:
                return id_error

            # Validate line count matches plan
            actual_line_count = len(stanza_output.lines)
            if actual_line_count != expected_line_count:
                return (
                    f"Stanza has {actual_line_count} lines but plan requested {expected_line_count} lines. "
                    f"Please generate exactly {expected_line_count} lines."
                )

            return None

        stanza_result = await run_stage(
            result_type=StanzaOutput,
            system_prompt=system_prompt_stanza,
            user_prompt=user_prompt_stanza,
            config=llm_config,
            expected_language=style_output.language,
            extract_text=lambda s: "\n".join(s.lines),
            validate=validate_stanza,
            error_mode=ErrorMode.STRICT,
        )
        stanza_output = stanza_result.output

        # Convert to model
        stanza = Stanza(
            id=stanza_output.id,
            lines=stanza_output.lines,
            meter=stanza_output.meter,
            rhyme_scheme=stanza_output.rhyme_scheme,
        )
        stanzas.append(stanza)

        # Add to existing summary for next iteration
        stanza_summary = f"Stanza {idx + 1} ({assigned_id}):\n" + "\n".join(stanza.lines)
        existing_stanzas_summary.append(stanza_summary)

    # Build final Project - use model_dump and validate to handle type conversion
    plot_dict = {
        "format": format_name,
        "title": poem_plan.title,
        "premise": poem_plan.premise,
        "themes": poem_plan.themes,
        "stanzas": [s.model_dump(exclude_none=True) for s in stanzas],
        "poem_form": poem_plan.poem_form,
        "poem_meter": poem_plan.poem_meter,
        "poem_rhyme_scheme": poem_plan.poem_rhyme_scheme,
    }
    plot = Plot.model_validate(plot_dict)

    style_dict = style_output.model_dump(exclude_none=True, by_alias=True)
    style = Style.model_validate(style_dict) if style_dict else None

    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea=idea,
        model=llm_config.model,
        temperature=llm_config.temperature,
        shape=options.shape_id,
        shape_file=str(options.shape_file) if options.shape_file else None,
        variation=options.variation,
        seed=llm_config.seed,
        enrichment_enabled=options.enrich,
        format=format_name,
        language=style_output.language,
    )

    config = ProjectConfig(
        version=__version__,
        title=poem_plan.title,
        metadata=metadata,
    )

    project = Project(
        config=config,
        plot=plot,
        characters=[],  # Poems don't have characters
        world=None,  # Poems don't have world building
        style=style,
    )

    return project
