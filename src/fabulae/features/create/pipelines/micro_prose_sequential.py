"""Sequential generation pipeline for micro-prose narratives.

This pipeline generates micro-prose content one fragment at a time with minimal context,
reducing LLM divergence and errors compared to batch generation.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fabulae import __version__
from fabulae.features.create.context import (
    MicroProseState,
    build_fragment_context,
)
from fabulae.features.create.graph import MicroProseGraph
from fabulae.features.create.progress import CreateProgress
from fabulae.features.create.prompts_v2 import (
    build_fragment_prompt_v2,
    build_premise_prompt_v2,
    build_style_prompt_v2,
)
from fabulae.features.create.schemas import (
    CreateOptions,
    FragmentOutput,
    PremiseOutput,
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
from fabulae.features.create.structure import generate_micro_prose_graph
from fabulae.llm import LLMConfig
from fabulae.llm.language_guard import LanguageGuardConfig
from fabulae.models import (
    Fragment,
    GenerationMetadata,
    LiteratureFormat,
    Plot,
    Project,
    ProjectConfig,
    ProjectDefaults,
)


async def generate_micro_prose_sequential(
    idea: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress,
    artifacts_dir: Path | None = None,
) -> Project:
    """Generate a micro-prose narrative using sequential per-unit approach.

    This pipeline generates content one fragment at a time with minimal context:
    1. Structure generation (deterministic, no LLM)
    2. Style generation (single call)
    3. Premise expansion (single call)
    4. Fragments (one call per fragment, with sliding window context)

    Args:
        idea: The core idea or premise for the narrative
        options: Configuration options including variation, seed, etc.
        llm_config: Configuration for LLM interactions
        progress: Progress reporter for user feedback
        artifacts_dir: Optional directory for saving intermediate artifacts

    Returns:
        A complete Project object with all fragments
    """
    format_name: LiteratureFormat = "micro-prose"

    # =========================================================================
    # Phase 1: Structure Generation (No LLM)
    # =========================================================================

    with progress.stage("Planning fragment structure..."):
        graph: MicroProseGraph = generate_micro_prose_graph(options.variation, options.seed)

    progress.success(f"Structure planned: {graph.total_fragments()} fragments")

    # Write structure artifact
    if artifacts_dir:
        _write_artifact(
            artifacts_dir,
            "01-structure.yml",
            {
                "format": format_name,
                "fragments": graph.total_fragments(),
                "seed": graph.seed,
                "summary": graph.to_summary(),
            },
        )

    # Initialize generation state for graceful shutdown
    gen_state = GenerationState(idea=idea, format_name=format_name)
    output_dir = artifacts_dir or Path.cwd()

    with graceful_shutdown(gen_state, output_dir, progress):
        return await _generate_micro_prose_sequential_inner(
            idea=idea,
            format_name=format_name,
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=artifacts_dir,
            graph=graph,
            gen_state=gen_state,
        )


async def _generate_micro_prose_sequential_inner(
    idea: str,
    format_name: LiteratureFormat,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress,
    artifacts_dir: Path | None,
    graph: MicroProseGraph,
    gen_state: GenerationState,
) -> Project:
    """Inner generation logic wrapped by graceful shutdown handler."""
    # =========================================================================
    # Phase 2: Style Generation
    # =========================================================================

    # Resolve language from CLI override or detect from idea
    language_config = LanguageGuardConfig()
    expected_language = _resolve_language(idea, options.idea_language, language_config)

    with progress.stage("Determining narrative style..."):
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
    # Phase 3: Premise Expansion
    # =========================================================================

    with progress.stage("Expanding premise..."):
        premise_result = await run_stage(
            result_type=PremiseOutput,
            system_prompt=build_premise_prompt_v2(format_name, idea, style_output),
            user_prompt=f"Expand this idea: {idea.strip()}",
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
    # Phase 4: Fragment Generation (One at a time)
    # =========================================================================

    state = MicroProseState()

    with progress.phase("Writing fragments...") as phase:
        for i, fragment_slot in enumerate(graph.fragment_slots):
            phase.update(f"Writing fragment {i + 1}/{graph.total_fragments()}...")
            context = build_fragment_context(
                fragment_slot=fragment_slot,
                graph=graph,
                state=state,
                premise=premise,
                style=style_output,
                options=options,
            )

            def validate_fragment(output: FragmentOutput, slot_id: str = fragment_slot.id) -> str | None:
                if output.id != slot_id:
                    return f"Fragment ID {output.id!r} does not match expected {slot_id!r}."
                return None

            fragment_result = await run_stage(
                result_type=FragmentOutput,
                system_prompt=build_fragment_prompt_v2(context),
                user_prompt=f"Generate fragment {fragment_slot.id}",
                config=llm_config,
                expected_language=expected_language,
                extract_text=lambda f: f.content,
                validate=validate_fragment,
                error_mode=ErrorMode.WARN,
            )

            # Convert to domain model and add to state
            fragment_data = fragment_result.output.model_dump(exclude_none=True)
            # Map 'content' to 'text' for the Fragment model if needed
            fragment = Fragment.model_validate(fragment_data)
            state.fragments.append(fragment)

            # Update generation state
            gen_state.fragments.append(fragment)
            gen_state.current_stage = f"generating_fragments ({i + 1}/{graph.total_fragments()})"

    progress.success(f"Written {len(state.fragments)} fragments")
    gen_state.current_stage = "fragments_complete"

    # Write fragments artifact
    if artifacts_dir and state.fragments:
        _write_artifact(
            artifacts_dir,
            "04-fragments.yml",
            {"fragments": [f.model_dump(exclude_none=True) for f in state.fragments]},
        )

    # =========================================================================
    # Phase 5: Project Assembly
    # =========================================================================

    with progress.stage("Assembling project..."):
        project = _assemble_micro_prose_project(
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


def _assemble_micro_prose_project(
    idea: str,
    format_name: LiteratureFormat,
    style_output: StyleOutput,
    premise: str,
    state: MicroProseState,
    graph: MicroProseGraph,
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
        fragments=state.fragments,
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


__all__ = ["generate_micro_prose_sequential"]
