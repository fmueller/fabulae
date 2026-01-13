"""CLI entrypoint for create-from-idea command."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated, cast

import typer
from pydantic import ValidationError

from fabulae.cli_options import model_option, seed_option, temperature_option
from fabulae.features.create.schemas import CreateOptions, NarrativePatternsMode
from fabulae.features.create.service import (
    CreateProjectError,
    generate_project_from_idea_sync,
)
from fabulae.llm import resolve_config
from fabulae.models import AVAILABLE_FORMATS, LiteratureFormat, save_project


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
            bool,
            typer.Option(
                "--enrich/--no-enrich",
                help="Enable/disable narrative enrichment (new characters, subplots, foreshadowing). Default: enabled.",
            ),
        ] = True,
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
        create_options = CreateOptions(
            narrative_patterns_mode=narrative_patterns,
            use_narrative_patterns_in_prompts=use_narrative_patterns_in_prompts,
            shape_id=shape,
            shape_file=shape_file,
            variation=variation,
            enrich=enrich,
        )
        try:
            project = generate_project_from_idea_sync(
                idea_text,
                format_value,
                config,
                output_dir=directory,
                idea_language=language_code,
                progress=typer.echo,
                options=create_options,
            )
        except (CreateProjectError, ValidationError, ValueError) as exc:
            typer.echo(f"Create failed: {exc}")
            raise typer.Exit(code=1) from exc

        typer.echo("Writing project files...")
        save_project(project, directory)

        character_count = len(project.characters)
        scene_count = len(project.plot.scenes)
        fragment_count = len(project.plot.fragments)
        stanza_count = len(project.plot.stanzas)
        typer.echo(f"Created Fabulae project in {directory}")
        typer.echo(
            "Summary: "
            f"{character_count} characters, {scene_count} scenes, "
            f"{fragment_count} fragments, {stanza_count} stanzas."
        )


__all__ = ["register_create_command"]
