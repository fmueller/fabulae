"""CLI entrypoint for create-from-idea command."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, cast

import typer
from pydantic import ValidationError

from fabulae.cli_options import model_option, seed_option, temperature_option
from fabulae.features.create.errors import ErrorType, classify_error, get_error_guidance
from fabulae.features.create.progress import CreateProgress
from fabulae.features.create.schemas import CreateOptions, PipelineMode
from fabulae.features.create.service import (
    CreateProjectError,
    generate_project_from_idea_sync,
)
from fabulae.features.create.validation import validate_title_diversity
from fabulae.history.manager import HistoryManager
from fabulae.history.models import ActionType
from fabulae.history.state import get_history_enabled
from fabulae.llm import resolve_config
from fabulae.llm.models import is_small_model, small_model_message
from fabulae.models import AVAILABLE_FORMATS, LiteratureFormat, sanitize_project, save_project


def _format_generation_error(exc: CreateProjectError, model_name: str) -> str:
    """Format a CreateProjectError with helpful context."""
    error_str = str(exc)

    # Try to classify the error for better messaging
    error_type = classify_error(exc)
    guidance = get_error_guidance(error_type)

    lines = [f"Generation failed: {guidance}"]

    # Add model-specific hints
    if error_type in {ErrorType.JSON_TRUNCATED, ErrorType.JSON_PARSE_ERROR} and is_small_model(model_name):
        lines.append(f"Note: The model '{model_name}' may be too small for complex structured output.")
        lines.append("Consider using a larger model (e.g., 13B+ parameters).")

    lines.append("")
    lines.append(f"Technical details: {error_str}")

    return "\n".join(lines)


def _resolve_idea(idea: str | None) -> str:
    if idea is None or not idea.strip():
        return cast(str, typer.prompt("Enter your story idea")).strip()
    candidate = Path(idea)
    if candidate.exists():
        if candidate.is_dir():
            raise typer.BadParameter(f"Idea path is a directory: {candidate}")
        return candidate.read_text(encoding="utf-8").strip()
    return idea.strip()


def _validate_format(format_name: str) -> LiteratureFormat:
    if format_name not in AVAILABLE_FORMATS:
        available = ", ".join(AVAILABLE_FORMATS)
        raise typer.BadParameter(f"Unknown format: {format_name}. Available: {available}")
    return format_name  # type: ignore[return-value]


def _validate_language(language: str | None) -> str | None:
    if language is None:
        return None
    normalized = language.strip().lower()
    if not re.match(r"^[a-z]{2}$", normalized):
        raise typer.BadParameter("Language must be an ISO 639-1 code (e.g., en, fr).")
    return normalized


def _resolve_shape(shape: str | None) -> tuple[str | None, Path | None]:
    """Resolve shape argument to either a shape ID or a file path.

    Args:
        shape: The shape argument from CLI - can be a shape ID or a file path

    Returns:
        Tuple of (shape_id, shape_file) - one will be set, the other None

    Raises:
        typer.BadParameter: If shape ID is invalid or file not found
    """
    if shape is None:
        return None, None

    # Check if it's a file path (exists as a file)
    candidate = Path(shape)
    if candidate.exists():
        if candidate.is_dir():
            raise typer.BadParameter(f"Shape path is a directory, not a file: {candidate}")
        return None, candidate

    # Otherwise, treat as a shape ID and validate it
    from fabulae.features.create.shapes.loader import get_shape_ids

    available_ids = get_shape_ids()
    if shape not in available_ids:
        available = ", ".join(sorted(available_ids))
        raise typer.BadParameter(
            f"Unknown shape: '{shape}'. If this is a file path, ensure it exists. "
            f"Available built-in shapes: {available}. "
            "Use 'fabulae shapes' to list all available shapes."
        )

    return shape, None


def register_create_command(app: typer.Typer) -> None:
    @app.command(
        name="create",
        help=(
            "Create a Fabulae project from an idea.\n\n"
            "For prose formats (novel, novella, short-story), generates a rough outline by default "
            "(chapters, scene summaries, character sketches). Use --full to generate complete "
            "project with all beats and details. Other formats (micro-prose, poem) always "
            "generate full content.\n\n"
            "Examples:\n\n"
            "  fabulae create ./my-novel --idea '...' --format novel          # Outline only\n\n"
            "  fabulae create ./my-novel --idea '...' --format novel --full   # Full details"
        ),
    )
    def create_command(
        directory: Annotated[Path, typer.Argument(help="Target project directory.")],
        idea: Annotated[
            str | None,
            typer.Option("--idea", "-i", help="Idea text or path to file containing the idea."),
        ] = None,
        format_name: Annotated[
            str,
            typer.Option("--format", "-f", help="Literature format to generate."),
        ] = "novel",
        language: Annotated[
            str | None,
            typer.Option("--language", "-l", help="ISO 639-1 language code to enforce."),
        ] = None,
        model: str = model_option(),
        temperature: float = temperature_option(),
        seed: int | None = seed_option(),
        force: Annotated[
            bool,
            typer.Option("--force", help="Overwrite existing directory."),
        ] = False,
        shape: Annotated[
            str | None,
            typer.Option(
                "--shape",
                "-s",
                help=(
                    "Story shape to use: either a built-in shape ID (e.g., 'betrayal-arc', "
                    "'heros-journey') or a path to a custom shape YAML file. "
                    "Use 'fabulae shapes' to list available built-in shapes."
                ),
            ),
        ] = None,
        no_shape: Annotated[
            bool,
            typer.Option(
                "--no-shape",
                help="Skip story shape selection for free-form generation without structural scaffolding.",
            ),
        ] = False,
        variation: Annotated[
            float,
            typer.Option(
                "--variation",
                min=0.0,
                max=1.0,
                help="Variation level for narrative elements (0.0 = minimal, 1.0 = maximum)",
            ),
        ] = 0.5,
        enrich: Annotated[
            bool | None,
            typer.Option(
                "--enrich/--no-enrich",
                help=(
                    "Enable/disable narrative enrichment (new characters, subplots, foreshadowing). "
                    "Default: enabled for large models, disabled for small models (<13B)."
                ),
            ),
        ] = None,
        pipeline: Annotated[
            PipelineMode | None,
            typer.Option(
                "--pipeline",
                "-p",
                help=(
                    "Generation pipeline: 'batch' (generates multiple items per LLM call) "
                    "or 'sequential' (generates one unit at a time with minimal context). "
                    "Default: 'sequential' for small models (<13B), 'batch' otherwise."
                ),
            ),
        ] = None,
        full: Annotated[
            bool,
            typer.Option(
                "--full",
                "-F",
                help=(
                    "Generate full project with all details including beats and scene content. "
                    "Default generates outline only for prose formats (novel, novella, short-story). "
                    "Has no effect on micro-prose or poem formats."
                ),
            ),
        ] = False,
    ) -> None:
        format_value = _validate_format(format_name)
        if directory.exists() and directory.is_file():
            raise typer.BadParameter(f"Target path is a file: {directory}")
        if directory.exists() and not force:
            raise typer.BadParameter(f"Target directory already exists: {directory}")

        # Resolve shape argument (can be shape ID or file path)
        shape_id, shape_file = _resolve_shape(shape)

        # Validate shape flags
        if no_shape and shape:
            raise typer.BadParameter("Cannot specify --no-shape with --shape.")

        idea_text = _resolve_idea(idea)
        language_code = _validate_language(language)
        if not idea_text:
            raise typer.BadParameter("Idea text cannot be empty.")

        directory.mkdir(parents=True, exist_ok=True)
        config = resolve_config(model, None, None, temperature, seed)

        progress = CreateProgress()
        is_small = is_small_model(config.model)

        # Determine effective settings based on model size
        # Auto: disable enrichment for small models to reduce context pressure
        effective_enrich: bool = not is_small if enrich is None else enrich
        # Auto: use sequential for small models (better for limited context)
        effective_pipeline: PipelineMode = ("sequential" if is_small else "batch") if pipeline is None else pipeline

        # Auto: disable enrichment for outline mode (no detailed content to enrich)
        effective_enrich_for_full = effective_enrich if full else False

        create_options = CreateOptions(
            shape_id=shape_id,
            shape_file=shape_file,
            no_shape=no_shape,
            variation=variation,
            seed=seed,
            enrich=effective_enrich_for_full,
            idea_language=language_code,
            is_small_model=is_small,
            sliding_window_scenes=5 if is_small else None,  # Limit context for small models
            pipeline=effective_pipeline,
            full=full,
        )

        # Show small model optimizations info
        if is_small:
            optimizations: list[tuple[str, str]] = []
            if pipeline is None:
                optimizations.append(("sequential pipeline", "--pipeline batch"))
            if enrich is None:
                optimizations.append(("enrichment disabled", "--enrich"))
            if optimizations:
                progress.info(small_model_message(optimizations))
            # Only warn about JSON issues if user explicitly chose batch pipeline or enrichment
            if pipeline == "batch" or enrich is True:
                progress.warn(
                    f"Model '{config.model}' may struggle with JSON output. "
                    "Consider a larger model if generation fails."
                )

        # Set up history tracking
        history_manager = HistoryManager(directory, enabled=get_history_enabled())
        history_params = {
            "format": format_name,
            "model": config.model,
            "temperature": temperature,
            "seed": seed,
            "shape": shape_id,
            "shape_file": str(shape_file) if shape_file else None,
            "variation": variation,
            "enrich": effective_enrich,
            "pipeline": effective_pipeline,
            "language": language_code,
        }

        with history_manager.track_action(
            action=ActionType.CREATE,
            command=f"fabulae create {directory} --format {format_name}",
            parameters=history_params,
        ):
            try:
                # Pipeline reports progress directly via CreateProgress
                project = generate_project_from_idea_sync(
                    idea_text,
                    format_value,
                    config,
                    output_dir=directory,
                    idea_language=language_code,
                    progress=None,
                    options=create_options,
                    create_progress=progress,
                )
            except CreateProjectError as exc:
                error_message = _format_generation_error(exc, config.model)
                progress.error(error_message)
                raise typer.Exit(code=1) from exc
            except (ValidationError, ValueError) as exc:
                progress.error(f"Create failed: {exc}")
                raise typer.Exit(code=1) from exc

            # Validate generated content for quality issues
            quality_warnings = validate_title_diversity(project)
            for warning in quality_warnings:
                progress.warn(warning)

            # Sanitize project to remove orphaned entities
            sanitize_warnings = sanitize_project(project)
            for warning in sanitize_warnings:
                progress.warn(warning)

            with progress.stage("Writing project files..."):
                save_project(project, directory)

        character_count = len(project.characters)
        scene_count = len(project.plot.scenes)
        fragment_count = len(project.plot.fragments)
        stanza_count = len(project.plot.stanzas)

        progress.success(f"Created Fabulae project in {directory}")
        progress.info(
            f"Summary: {character_count} characters, {scene_count} scenes, "
            f"{fragment_count} fragments, {stanza_count} stanzas"
        )


__all__ = ["register_create_command"]
