"""CLI command for building narrative output from Fabulae projects."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import typer
import yaml

from fabulae.cli_options import api_key_option, base_url_option, model_option, seed_option, temperature_option
from fabulae.features.build.schemas import BuildOptions, BuildPipelineMode
from fabulae.features.build.service import build_project
from fabulae.features.build.writer import write_build_output
from fabulae.features.create.progress import CreateProgress
from fabulae.history.manager import HistoryManager
from fabulae.history.models import ActionType
from fabulae.history.state import get_history_enabled
from fabulae.llm import resolve_config
from fabulae.models import load_project

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


def register_build_command(app: typer.Typer) -> None:
    """Register the build command with the Typer app."""

    @app.command(name="build", help="Build a complete narrative from a Fabulae project.")
    def build_command(
        project_dir: Annotated[
            Path,
            typer.Argument(help="Path to Fabulae project directory."),
        ] = Path("."),
        output: Annotated[
            Path | None,
            typer.Option("--output", "-o", help="Output directory for generated files."),
        ] = None,
        seed: int | None = seed_option(),
        model: str = model_option(),
        temperature: float = temperature_option(),
        base_url: str | None = base_url_option(),
        api_key: str | None = api_key_option(),
        output_format: Annotated[
            Literal["md", "txt", "html"],
            typer.Option("--format", "-f", help="Output file format."),
        ] = "md",
        language: Annotated[
            str | None,
            typer.Option(
                "--language",
                "-l",
                help="Target language (ISO 639-1 code, e.g. 'de', 'fr'). Overrides style.yml.",
            ),
        ] = None,
        pipeline: Annotated[
            BuildPipelineMode | None,
            typer.Option(
                "--pipeline",
                "-p",
                help=(
                    "Generation pipeline: 'sequential' (sliding window context, better for small models) "
                    "or 'batch' (full context, better coherence). Default: sequential."
                ),
            ),
        ] = None,
        enhanced: Annotated[
            bool,
            typer.Option(
                "--enhanced/--no-enhanced",
                help="Enable enhanced narrative elements (hooks, beat tracking). Default: enabled.",
            ),
        ] = True,
    ) -> None:
        """Build a complete narrative from a Fabulae project.

        Generates prose/poetry from the project's structural elements using an LLM.
        Each build with a different seed produces a unique variation.

        Examples:
            fabulae build ./my-novel
            fabulae build ./my-novel --seed 42 --output ./drafts
            fabulae build ./my-poem --format html
            fabulae build ./my-novel --pipeline batch --enhanced
        """
        progress = CreateProgress()
        progress.start()

        # Load and validate project
        with progress.stage("Loading project..."):
            try:
                project = load_project(project_dir)
            except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
                progress.error(f"Failed to load project: {exc}")
                raise typer.Exit(code=1) from exc

        # Resolve LLM config
        config = resolve_config(
            cli_model=model,
            cli_base_url=base_url,
            cli_api_key=api_key,
            cli_temperature=temperature,
            cli_seed=seed,
        )

        # Determine output directory
        if output is None:
            output = project_dir / "output"

        # Create timestamped build directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        seed_suffix = f"_seed{seed}" if seed is not None else ""
        build_dir = output / f"{timestamp}{seed_suffix}"

        project_title = project.plot.title or project.config.title or "project"
        format_type = project.plot.format or "novel"

        # Determine pipeline mode (auto-detect for small models)
        is_small = _is_small_model(config.model)
        actual_pipeline: BuildPipelineMode = pipeline or ("sequential" if is_small else "sequential")
        actual_enhanced = enhanced

        # Build options
        build_options = BuildOptions(
            pipeline=actual_pipeline,
            enhanced=actual_enhanced,
        )

        progress.info(f"Building {format_type}: {project_title}")
        progress.info(f"Model: {config.model}, Temperature: {config.temperature}")
        progress.info(f"Pipeline: {actual_pipeline}, Enhanced: {actual_enhanced}")
        if seed is not None:
            progress.info(f"Seed: {seed}")

        if is_small and pipeline is None:
            progress.warn(
                f"Small model detected ({config.model}). "
                "Using sequential pipeline. Override with --pipeline batch if desired."
            )

        # Set up history tracking
        history_manager = HistoryManager(project_dir, enabled=get_history_enabled())
        history_params = {
            "format": format_type,
            "model": config.model,
            "temperature": config.temperature,
            "seed": seed,
            "output_format": output_format,
            "output_dir": str(build_dir),
            "pipeline": actual_pipeline,
            "enhanced": actual_enhanced,
        }

        # Resolve target language: CLI flag > style.yml > None
        expected_language = language
        if expected_language is None and project.style and project.style.language:
            expected_language = project.style.language

        # Run build
        try:
            with history_manager.track_action(
                action=ActionType.BUILD,
                command=f"fabulae build {project_dir}",
                parameters=history_params,
            ):
                with progress.stage("Generating narrative..."):
                    result = asyncio.run(
                        build_project(project, config, seed, progress, expected_language, build_options)
                    )

                with progress.stage("Writing output files..."):
                    write_build_output(result, build_dir, output_format)

        except Exception as exc:
            progress.error(f"Build failed: {exc}")
            raise typer.Exit(code=1) from exc

        # Print summary
        progress.success(f"Build complete: {build_dir}")
        progress.info(f"Total words: {result.total_word_count:,}")

        if result.chapters:
            progress.info(f"Chapters: {len(result.chapters)}")
            for chapter in result.chapters:
                scene_count = len(chapter.scenes)
                title = chapter.title or chapter.chapter_id
                progress.console.print(f"  [dim]{title}: {scene_count} scenes, {chapter.word_count:,} words[/dim]")

        elif result.scenes:
            progress.info(f"Scenes: {len(result.scenes)}")

        elif result.fragments:
            progress.info(f"Fragments: {len(result.fragments)}")

        elif result.stanzas:
            progress.info(f"Stanzas: {len(result.stanzas)}")


__all__ = ["register_build_command"]
