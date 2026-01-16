"""Sequential generation pipeline for poetry.

This pipeline generates poetry content one stanza at a time with minimal context,
reducing LLM divergence and errors compared to batch generation.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from fabulae import __version__
from fabulae.features.create.context import (
    PoemState,
    build_stanza_context,
)
from fabulae.features.create.graph import PoemGraph
from fabulae.features.create.progress import CreateProgress
from fabulae.features.create.prompts_v2 import (
    build_premise_prompt_v2,
    build_stanza_prompt_v2,
    build_style_prompt_v2,
)
from fabulae.features.create.schemas import (
    CreateOptions,
    PremiseOutput,
    StanzaOutput,
    StyleOutput,
)
from fabulae.features.create.service import (
    ErrorMode,
    _coerce_style,
    _extract_text_from_style,
    _resolve_language,
    _write_artifact,
    _write_config,
    _write_plot,
    _write_style,
    run_stage,
)
from fabulae.features.create.shutdown import graceful_shutdown
from fabulae.features.create.state import GenerationState
from fabulae.features.create.structure import generate_poem_graph
from fabulae.llm import LLMConfig
from fabulae.llm.language_guard import LanguageGuardConfig
from fabulae.models import (
    GenerationMetadata,
    LiteratureFormat,
    Plot,
    Project,
    ProjectConfig,
    ProjectDefaults,
    Stanza,
)


class PoemPlanOutput(BaseModel):
    """Minimal poem planning output."""

    title: str | None = Field(default=None, description="Poem title")
    poem_form: str | None = Field(default=None, description="Poem form (sonnet, haiku, free verse, etc.)")
    themes: list[str] = Field(default_factory=list, description="Key themes")


async def generate_poem_sequential(
    idea: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress,
    artifacts_dir: Path | None = None,
) -> Project:
    """Generate a poem using sequential per-unit approach.

    This pipeline generates content one stanza at a time with minimal context:
    1. Structure generation (deterministic, no LLM)
    2. Style generation (single call)
    3. Premise expansion (single call)
    4. Stanzas (one call per stanza, with sliding window context)

    Args:
        idea: The core idea or premise for the poem
        options: Configuration options including variation, seed, etc.
        llm_config: Configuration for LLM interactions
        progress: Progress reporter for user feedback
        artifacts_dir: Optional directory for saving intermediate artifacts

    Returns:
        A complete Project object with all stanzas
    """
    format_name: LiteratureFormat = "poem"

    # =========================================================================
    # Phase 1: Structure Generation (No LLM)
    # =========================================================================

    with progress.stage("Planning poem structure..."):
        graph: PoemGraph = generate_poem_graph(options.variation, options.seed)

    progress.success(f"Structure planned: {graph.total_stanzas()} stanzas, ~{graph.total_lines()} lines")

    # Write structure artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "01-structure.yml",
            {
                "format": format_name,
                "stanzas": graph.total_stanzas(),
                "total_lines": graph.total_lines(),
                "seed": graph.seed,
                "summary": graph.to_summary(),
            },
        )

    # Initialize generation state for graceful shutdown
    gen_state = GenerationState(idea=idea, format_name=format_name)
    output_dir = artifacts_dir or Path.cwd()

    with graceful_shutdown(gen_state, output_dir, progress):
        return await _generate_poem_sequential_inner(
            idea=idea,
            format_name=format_name,
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=artifacts_dir,
            graph=graph,
            gen_state=gen_state,
        )


async def _generate_poem_sequential_inner(
    idea: str,
    format_name: LiteratureFormat,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress,
    artifacts_dir: Path | None,
    graph: PoemGraph,
    gen_state: GenerationState,
) -> Project:
    """Inner generation logic wrapped by graceful shutdown handler."""
    # =========================================================================
    # Phase 2: Style Generation
    # =========================================================================

    # Resolve language from CLI override or detect from idea
    language_config = LanguageGuardConfig()
    expected_language = _resolve_language(idea, options.idea_language, language_config)

    with progress.stage("Determining poetic style..."):
        style_result = await run_stage(
            result_type=StyleOutput,
            system_prompt=build_style_prompt_v2(format_name, idea),
            user_prompt=f"Generate style for: {idea.strip()}",
            config=llm_config,
            expected_language=expected_language,
            extract_text=_extract_text_from_style,
            error_mode=ErrorMode.WARN,
        )
        style_output = style_result.output

    # Default to English if no language was detected or overridden
    if expected_language is None:
        expected_language = "en"

    # Ensure style reflects the enforced language (CLI override takes precedence)
    if expected_language and style_output.language != expected_language:
        style_output = style_output.model_copy(update={"language": expected_language})

    progress.success("Style determined")

    # Update generation state
    gen_state.style = style_output
    gen_state.current_stage = "style_complete"

    # Write style artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "02-style.yml", style_output.model_dump(exclude_none=True, by_alias=True))

    # =========================================================================
    # Phase 3: Premise Expansion (used as poem theme/direction)
    # =========================================================================

    with progress.stage("Expanding premise..."):
        premise_result = await run_stage(
            result_type=PremiseOutput,
            system_prompt=build_premise_prompt_v2(format_name, idea, style_output),
            user_prompt=f"Expand this idea for a poem: {idea.strip()}",
            config=llm_config,
            expected_language=expected_language,
            extract_text=lambda p: p.premise,
            error_mode=ErrorMode.STRICT,
        )
        premise = premise_result.output.premise

    progress.success("Premise expanded")

    # Update generation state
    gen_state.premise = premise
    gen_state.current_stage = "premise_complete"

    # Write premise artifact
    if artifacts_dir:
        _write_artifact(artifacts_dir, "03-premise.yml", {"premise": premise})

    # =========================================================================
    # Phase 4: Stanza Generation (One at a time)
    # =========================================================================

    state = PoemState()

    with progress.phase("Writing stanzas...") as phase:
        for i, stanza_slot in enumerate(graph.stanza_slots):
            phase.update(f"Writing stanza {i + 1}/{graph.total_stanzas()}...")
            context = build_stanza_context(
                stanza_slot=stanza_slot,
                graph=graph,
                state=state,
                premise=premise,
                style=style_output,
                options=options,
            )

            def validate_stanza(
                output: StanzaOutput,
                slot_id: str = stanza_slot.id,
                expected_lines: int = stanza_slot.line_count,
            ) -> str | None:
                if output.id != slot_id:
                    return f"Stanza ID {output.id!r} does not match expected {slot_id!r}."
                if len(output.lines) != expected_lines:
                    return f"Stanza has {len(output.lines)} lines but expected {expected_lines}."
                return None

            stanza_result = await run_stage(
                result_type=StanzaOutput,
                system_prompt=build_stanza_prompt_v2(context),
                user_prompt=f"Generate stanza {stanza_slot.id}",
                config=llm_config,
                expected_language=expected_language,
                extract_text=lambda s: "\n".join(s.lines),
                validate=validate_stanza,
                error_mode=ErrorMode.WARN,
            )

            # Convert to domain model and add to state
            stanza_data = stanza_result.output.model_dump(exclude_none=True)
            stanza = Stanza.model_validate(stanza_data)
            state.stanzas.append(stanza)

            # Update generation state
            gen_state.stanzas.append(stanza)
            gen_state.current_stage = f"generating_stanzas ({i + 1}/{graph.total_stanzas()})"

    progress.success(f"Written {len(state.stanzas)} stanzas")
    gen_state.current_stage = "stanzas_complete"

    # Write stanzas artifact
    if artifacts_dir and state.stanzas:
        _write_artifact(
            artifacts_dir,
            "04-stanzas.yml",
            {"stanzas": [s.model_dump(exclude_none=True) for s in state.stanzas]},
        )

    # =========================================================================
    # Phase 5: Project Assembly
    # =========================================================================

    with progress.stage("Assembling project..."):
        project = _assemble_poem_project(
            idea=idea,
            format_name=format_name,
            style_output=style_output,
            premise=premise,
            state=state,
            graph=graph,
            llm_config=llm_config,
            variation=options.variation,
            enrich=options.enrich,
        )

    progress.success("Project assembled")

    # Write final project files
    if artifacts_dir:
        _write_config(project.config, artifacts_dir)
        _write_style(project.style, project.config, artifacts_dir)
        _write_plot(project.plot, project.config, artifacts_dir)

    return project


def _assemble_poem_project(
    idea: str,
    format_name: LiteratureFormat,
    style_output: StyleOutput,
    premise: str,
    state: PoemState,
    graph: PoemGraph,
    llm_config: LLMConfig,
    variation: float,
    enrich: bool,
) -> Project:
    """Assemble the final Project from generated components."""
    # Build style
    style = _coerce_style(style_output)

    # Build plot
    plot = Plot(
        format=format_name,
        title=None,
        premise=premise,
        themes=[],
        stanzas=state.stanzas,
        poem_form=graph.poem_form,
    )

    # Build config with metadata
    metadata = GenerationMetadata(
        generated_at=datetime.now(),
        generator_version=__version__,
        original_idea=idea,
        model=llm_config.model,
        temperature=llm_config.temperature,
        variation=variation,
        seed=graph.seed,
        enrichment_enabled=enrich,
        format=format_name,
    )

    config = ProjectConfig(
        defaults=ProjectDefaults(),
        metadata=metadata,
    )

    return Project(
        config=config,
        plot=plot,
        characters=[],
        world=None,
        style=style,
    )


__all__ = ["generate_poem_sequential"]
