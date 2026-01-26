"""CLI command for building narrative output from Fabulae projects."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import typer
import yaml

from fabulae.cli_options import api_key_option, base_url_option, model_option, seed_option, temperature_option
from fabulae.features.build.service import build_project
from fabulae.features.build.writer import write_build_output
from fabulae.features.create.progress import CreateProgress
from fabulae.history.manager import HistoryManager
from fabulae.history.models import ActionType
from fabulae.history.state import get_history_enabled
from fabulae.llm import resolve_config
from fabulae.models import load_project


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
    ) -> None:
        """Build a complete narrative from a Fabulae project.

        Generates prose/poetry from the project's structural elements using an LLM.
        Each build with a different seed produces a unique variation.

        Examples:
            fabulae build ./my-novel
            fabulae build ./my-novel --seed 42 --output ./drafts
            fabulae build ./my-poem --format html
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

        progress.info(f"Building {format_type}: {project_title}")
        progress.info(f"Model: {config.model}, Temperature: {config.temperature}")
        if seed is not None:
            progress.info(f"Seed: {seed}")

        # Set up history tracking
        history_manager = HistoryManager(project_dir, enabled=get_history_enabled())
        history_params = {
            "format": format_type,
            "model": config.model,
            "temperature": config.temperature,
            "seed": seed,
            "output_format": output_format,
            "output_dir": str(build_dir),
        }

        # Run build
        try:
            with history_manager.track_action(
                action=ActionType.BUILD,
                command=f"fabulae build {project_dir}",
                parameters=history_params,
            ):
                with progress.stage("Generating narrative..."):
                    result = asyncio.run(build_project(project, config, seed, progress))

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
