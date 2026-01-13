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
from fabulae.features.create.schemas import CreateOptions, NarrativePatternsMode, PipelineMode
from fabulae.features.create.service import (
    CreateProjectError,
    generate_project_from_idea_sync,
)
from fabulae.llm import resolve_config
from fabulae.models import AVAILABLE_FORMATS, LiteratureFormat, save_project

# Patterns that indicate a small model that may struggle with structured output
_SMALL_MODEL_PATTERNS = [
    r"[:\-](\d+(?:\.\d+)?)b\b",  # Matches :1.7b, :3b, :10b, -7b, etc.
    r"mini",
    r"tiny",
    r"small",
]

# Threshold for "small" model in billions of parameters
_SMALL_MODEL_THRESHOLD_B = 13


def _is_small_model(model_name: str) -> bool:
    """Check if a model name suggests it's a small model (<13B parameters)."""
    model_lower = model_name.lower()
    for pattern in _SMALL_MODEL_PATTERNS:
        match = re.search(pattern, model_lower)
        if match:
            # For numeric patterns, check if < threshold
            if match.lastindex and match.lastindex >= 1:
                try:
                    size = float(match.group(1))
                    if size < _SMALL_MODEL_THRESHOLD_B:
                        return True
                except ValueError:
                    pass
            else:
                # Non-numeric patterns like "mini", "tiny", "small"
                return True
    return False


def _format_generation_error(exc: CreateProjectError, model_name: str) -> str:
    """Format a CreateProjectError with helpful context."""
    error_str = str(exc)

    # Try to classify the error for better messaging
    error_type = classify_error(exc)
    guidance = get_error_guidance(error_type)

    lines = [f"Generation failed: {guidance}"]

    # Add model-specific hints
    if error_type in {ErrorType.JSON_TRUNCATED, ErrorType.JSON_PARSE_ERROR} and _is_small_model(model_name):
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


def register_create_command(app: typer.Typer) -> None:
    @app.command(name="create", help="Create a Fabulae project from an idea.")
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
        narrative_patterns: Annotated[
            NarrativePatternsMode,
            typer.Option(
                "--narrative-patterns",
                help=(
                    "Control narrative pattern generation: "
                    "'off' = do not generate (default), "
                    "'artifact' = generate and save to .fabulae-create/ only, "
                    "'project' = generate and save to both .fabulae-create/ and project root."
                ),
            ),
        ] = "off",
        use_narrative_patterns_in_prompts: Annotated[
            bool,
            typer.Option(
                "--use-narrative-patterns-in-prompts",
                help=(
                    "Include narrative patterns in prompt context for plot outline and scene expansion. "
                    "Only meaningful if --narrative-patterns is not 'off'. Default: off."
                ),
            ),
        ] = False,
        shape: Annotated[
            str | None,
            typer.Option(
                "--shape",
                help=(
                    "Story shape to use (e.g., 'betrayal-arc', 'heros-journey'). "
                    "Use 'fabulae shapes' to list available shapes."
                ),
            ),
        ] = None,
        shape_file: Annotated[
            Path | None,
            typer.Option(
                "--shape-file",
                help="Path to a custom story shape YAML file.",
            ),
        ] = None,
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
    ) -> None:
        format_value = _validate_format(format_name)
        if directory.exists() and directory.is_file():
            raise typer.BadParameter(f"Target path is a file: {directory}")
        if directory.exists() and not force:
            raise typer.BadParameter(f"Target directory already exists: {directory}")

        # Validate shape flags
        if shape and shape_file:
            raise typer.BadParameter(
                "Cannot specify both --shape and --shape-file. "
                "Use --shape for built-in shapes or --shape-file for custom shapes."
            )

        if shape_file and not shape_file.exists():
            raise typer.BadParameter(f"Shape file not found: {shape_file}")

        # Validate shape ID exists before starting generation
        if shape:
            from fabulae.features.create.shapes.loader import get_shape_ids

            available_ids = get_shape_ids()
            if shape not in available_ids:
                available = ", ".join(sorted(available_ids))
                raise typer.BadParameter(
                    f"Unknown shape: {shape}. Available shapes: {available}. "
                    "Use 'fabulae shapes' to list all available shapes."
                )

        idea_text = _resolve_idea(idea)
        language_code = _validate_language(language)
        if not idea_text:
            raise typer.BadParameter("Idea text cannot be empty.")

        directory.mkdir(parents=True, exist_ok=True)
        config = resolve_config(model, None, None, temperature, seed)

        progress = CreateProgress()
        is_small = _is_small_model(config.model)

        # Determine effective settings based on model size
        # Auto: disable enrichment for small models to reduce context pressure
        effective_enrich: bool = not is_small if enrich is None else enrich
        # Auto: use sequential for small models (better for limited context)
        effective_pipeline: PipelineMode = ("sequential" if is_small else "batch") if pipeline is None else pipeline

        create_options = CreateOptions(
            narrative_patterns_mode=narrative_patterns,
            use_narrative_patterns_in_prompts=use_narrative_patterns_in_prompts,
            shape_id=shape,
            shape_file=shape_file,
            variation=variation,
            seed=seed,
            enrich=effective_enrich,
            idea_language=language_code,
            is_small_model=is_small,
            sliding_window_scenes=5 if is_small else None,  # Limit context for small models
            pipeline=effective_pipeline,
        )

        # Show small model optimizations info
        if is_small:
            optimizations = []
            overrides = []
            if enrich is None:
                optimizations.append("enrichment disabled")
                overrides.append("--enrich")
            if pipeline is None:
                optimizations.append("sequential pipeline")
                overrides.append("--pipeline batch")
            if optimizations:
                msg = f"Small model detected (<{_SMALL_MODEL_THRESHOLD_B}B): using {', '.join(optimizations)}."
                if overrides:
                    msg += f" Override with {'/'.join(overrides)}."
                progress.info(msg)
            # Only warn about JSON issues if user explicitly chose batch pipeline or enrichment
            if pipeline == "batch" or enrich is True:
                progress.warn(
                    f"Model '{config.model}' may struggle with JSON output. "
                    "Consider a larger model if generation fails."
                )

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
