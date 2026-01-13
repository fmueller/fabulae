"""Micro-prose narrative pipeline for flash fiction format.

This module implements the generation pipeline for micro-prose narratives,
featuring minimal structure with fragments as the primary unit of content.

The micro-prose pipeline is simpler than prose formats:
- No story shapes
- No complex plot structure
- Just: Style -> Fragment Plan -> Fragments
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fabulae import __version__
from fabulae.features.create.progress import CreateProgress
from fabulae.features.create.prompts import (
    build_fragment_plan_prompt,
    build_fragment_prompt,
    build_style_prompt,
)
from fabulae.features.create.schemas import (
    CreateOptions,
    FragmentOutput,
    FragmentPlanOutput,
    StyleOutput,
)
from fabulae.features.create.service import (
    ErrorMode,
    _build_user_prompt,
    _coerce_style,
    _count_range,
    _extract_text_from_fragment,
    _extract_text_from_fragment_plan,
    _extract_text_from_style,
    _resolve_language,
    _rng,
    _style_hint,
    _summarize_fragments,
    _validate_fragment_output,
    _validate_fragment_plan_output,
    _validate_style_output,
    _write_artifact,
    _write_config,
    _write_plot,
    _write_style,
    run_stage,
)
from fabulae.features.create.shutdown import graceful_shutdown
from fabulae.features.create.state import GenerationState
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


async def generate_micro_prose(
    idea: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress | None = None,
    artifacts_dir: Path | None = None,
) -> Project:
    """Generate a micro-prose project from an idea.

    Args:
        idea: The story idea to generate from
        options: Create options (language, variation, etc.)
        llm_config: LLM configuration
        artifacts_dir: Optional directory for intermediate artifacts

    Returns:
        A complete Project object with fragments populated
    """
    format_name: LiteratureFormat = "micro-prose"

    # Initialize generation state for graceful shutdown
    gen_state = GenerationState(idea=idea, format_name=format_name)
    output_dir = artifacts_dir or Path.cwd()

    with graceful_shutdown(gen_state, output_dir, progress):
        return await _generate_micro_prose_impl(
            idea=idea,
            options=options,
            llm_config=llm_config,
            progress=progress,
            artifacts_dir=artifacts_dir,
            gen_state=gen_state,
        )


async def _generate_micro_prose_impl(
    idea: str,
    options: CreateOptions,
    llm_config: LLMConfig,
    progress: CreateProgress | None,
    artifacts_dir: Path | None,
    gen_state: GenerationState,
) -> Project:
    """Internal implementation of micro-prose generation with state tracking."""
    format_name: LiteratureFormat = "micro-prose"

    # Resolve language from CLI override or detect from idea
    language_config = LanguageGuardConfig()
    expected_language = _resolve_language(idea, options.idea_language, language_config)

    # Initialize config
    gen_state.current_stage = "setup"
    config = ProjectConfig(
        version=__version__,
        title=None,
        paths=None,
        defaults=ProjectDefaults(language=expected_language) if expected_language else None,
    )

    # Initialize RNG if seeded
    rng = _rng(llm_config.seed)

    # Step 1: Generate Style
    gen_state.current_stage = "generating_style"
    style_prompt = build_style_prompt(format_name)
    style_user_prompt = _build_user_prompt(idea, format_name, {"Language": expected_language or "auto-detect"})
    style_result = await run_stage(
        result_type=StyleOutput,
        system_prompt=style_prompt,
        user_prompt=style_user_prompt,
        config=llm_config,
        expected_language=expected_language,
        extract_text=_extract_text_from_style,
        normalize=None,
        validate=_validate_style_output(expected_language),
        error_mode=ErrorMode.STRICT,
    )
    style_output = style_result.output

    # Default to English if no language was detected or overridden
    if expected_language is None:
        expected_language = "en"

    # Ensure language matches expected
    if style_output.language != expected_language:
        style_output = style_output.model_copy(update={"language": expected_language})

    style = _coerce_style(style_output)
    style_hint_str = _style_hint(style_output) if style_output else ""
    gen_state.style = style_output

    if progress:
        progress.success("Style determined")

    # Write artifacts if directory provided
    if artifacts_dir:
        _write_config(config, artifacts_dir)
        _write_style(style, config, artifacts_dir)
        _write_artifact(artifacts_dir, "style.yml", style_output.model_dump(exclude_none=True, by_alias=True))

    # Step 2: Generate Fragment Plan
    gen_state.current_stage = "generating_fragment_plan"
    fragment_count_range = _count_range(format_name, "fragments")
    fragment_plan_prompt = build_fragment_plan_prompt(format_name, style_hint_str or None, fragment_count_range)
    fragment_plan_user_prompt = _build_user_prompt(
        idea,
        format_name,
        {
            "Style": style_hint_str,
            "Count Targets": f"Fragments: {fragment_count_range[0]}-{fragment_count_range[1]}",
        },
    )

    fragment_plan_result = await run_stage(
        result_type=FragmentPlanOutput,
        system_prompt=fragment_plan_prompt,
        user_prompt=fragment_plan_user_prompt,
        config=llm_config,
        expected_language=expected_language,
        extract_text=_extract_text_from_fragment_plan,
        normalize=None,
        validate=_validate_fragment_plan_output,
        error_mode=ErrorMode.STRICT,
    )
    fragment_plan_output = fragment_plan_result.output

    if progress:
        progress.success(f"Fragments planned: {len(fragment_plan_output.fragments)}")

    # Store premise from fragment plan if available
    if fragment_plan_output.premise:
        gen_state.premise = fragment_plan_output.premise

    if artifacts_dir:
        _write_artifact(artifacts_dir, "fragments_plan.yml", fragment_plan_output.model_dump(exclude_none=True))

    # Step 3: Generate Fragments
    gen_state.current_stage = "generating_fragments"

    fragment_outputs: dict[str, Fragment] = {}
    fragment_order = list(fragment_plan_output.fragments)

    # Optionally shuffle for variety
    if llm_config.seed is not None:
        rng.shuffle(fragment_order)

    for fragment_seed in fragment_order:
        # Apply sliding window for fragment context if configured
        all_fragments = list(fragment_outputs.values())
        if options.sliding_window_scenes is not None and len(all_fragments) > options.sliding_window_scenes:
            windowed_fragments = all_fragments[-options.sliding_window_scenes :]
        else:
            windowed_fragments = all_fragments
        existing_summary = _summarize_fragments(windowed_fragments)
        fragment_prompt = build_fragment_prompt(
            format_name,
            style_hint_str or None,
            existing_summary,
            fragment_seed.id,
        )
        fragment_user_prompt = _build_user_prompt(
            idea,
            format_name,
            {
                "Fragment Seed": fragment_seed.model_dump(exclude_none=True),
                "Style": style_hint_str,
            },
        )

        def validate_fragment(output: FragmentOutput, expected_id: str = fragment_seed.id) -> str | None:
            return _validate_fragment_output(output, expected_id, set(fragment_outputs))

        fragment_result = await run_stage(
            result_type=FragmentOutput,
            system_prompt=fragment_prompt,
            user_prompt=fragment_user_prompt,
            config=llm_config,
            expected_language=expected_language,
            extract_text=_extract_text_from_fragment,
            normalize=None,
            validate=validate_fragment,
            error_mode=ErrorMode.STRICT,
        )
        fragment_output = fragment_result.output
        fragment = Fragment.model_validate(fragment_output.model_dump(exclude_none=True))
        fragment_outputs[fragment.id] = fragment
        gen_state.fragments.append(fragment)

        if artifacts_dir:
            _write_artifact(
                artifacts_dir,
                f"fragments/{fragment.id}.yml",
                fragment_output.model_dump(exclude_none=True),
            )

    # Reconstruct fragments in original plan order
    fragments = [fragment_outputs[seed.id] for seed in fragment_plan_output.fragments if seed.id in fragment_outputs]

    if progress:
        progress.success(f"Written {len(fragments)} fragments")

    # Build plot
    gen_state.current_stage = "assembling_project"
    plot_payload = {
        "format": format_name,
        "title": fragment_plan_output.title,
        "premise": fragment_plan_output.premise,
        "themes": fragment_plan_output.themes,
        "fragments": [fragment.model_dump(exclude_none=True) for fragment in fragments],
    }
    plot = Plot.model_validate(plot_payload)

    # Update config with title and metadata
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
        language=expected_language,
    )

    config.title = plot.title
    config.metadata = metadata

    if artifacts_dir:
        _write_plot(plot, config, artifacts_dir)
        _write_config(config, artifacts_dir)

    # Build and return project
    project = Project(
        config=config,
        plot=plot,
        characters=[],  # Micro-prose doesn't use characters
        world=None,
        style=style,
    )

    if progress:
        progress.success("Project assembled")

    return project


__all__ = ["generate_micro_prose"]
