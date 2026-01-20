"""CLI commands for story shapes."""

from __future__ import annotations

from typing import Annotated

import typer

from fabulae.features.create.shapes.loader import (
    ShapeNotFoundError,
    get_shape_ids,
    load_shape,
)


def _list_shapes() -> None:
    """List all available built-in story shapes."""
    shape_ids = get_shape_ids()

    if not shape_ids:
        typer.echo("No story shapes found.")
        return

    typer.echo(f"Available story shapes ({len(shape_ids)}):")
    typer.echo()

    for shape_id in shape_ids:
        try:
            shape = load_shape(shape_id)
            typer.echo(f"  {shape_id}")
            typer.echo(f"    Name: {shape.name}")
            typer.echo(f"    {shape.description}")
            typer.echo()
        except Exception as exc:
            typer.echo(f"  {shape_id} (error loading: {exc})")
            typer.echo()


def _show_shape_details(shape_id: str) -> None:
    """Display detailed information about a specific story shape."""
    try:
        shape = load_shape(shape_id)
    except ShapeNotFoundError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1) from exc
    except Exception as exc:
        typer.echo(f"Error loading shape '{shape_id}': {exc}")
        raise typer.Exit(code=1) from exc

    # Display shape header
    typer.echo(f"Shape: {shape.name}")
    typer.echo(f"ID: {shape.id}")
    typer.echo()
    typer.echo(f"Description: {shape.description}")
    typer.echo()

    # Display character slots
    if shape.character_slots:
        typer.echo(f"Character Slots ({len(shape.character_slots)}):")
        for slot in shape.character_slots:
            optional_marker = " (optional)" if slot.optional else ""
            typer.echo(f"  - {slot.slot}{optional_marker}")
            # Format needs text with proper wrapping
            needs_lines = slot.needs.strip().replace("\n", " ").split(". ")
            for line in needs_lines:
                if line.strip():
                    typer.echo(f"    {line.strip()}.")
            if slot.can_merge_with:
                merge_list = ", ".join(slot.can_merge_with)
                typer.echo(f"    Can merge with: {merge_list}")
            typer.echo()

    # Display setting slots
    if shape.setting_slots:
        typer.echo(f"Setting Slots ({len(shape.setting_slots)}):")
        for setting_slot in shape.setting_slots:
            optional_marker = " (optional)" if setting_slot.optional else ""
            typer.echo(f"  - {setting_slot.slot}{optional_marker}")
            # Format needs text with proper wrapping
            needs_lines = setting_slot.needs.strip().replace("\n", " ").split(". ")
            for line in needs_lines:
                if line.strip():
                    typer.echo(f"    {line.strip()}.")
            if setting_slot.used_in:
                used_list = ", ".join(setting_slot.used_in)
                typer.echo(f"    Used in: {used_list}")
            typer.echo()

    # Display required beats
    if shape.required_beats:
        typer.echo(f"Required Beats ({len(shape.required_beats)}):")
        for beat in shape.required_beats:
            typer.echo(f"  - {beat.type} ({beat.position}, {beat.flexibility})")
            # Format description text with proper wrapping
            desc_lines = beat.description.strip().replace("\n", " ").split(". ")
            for line in desc_lines:
                if line.strip():
                    typer.echo(f"    {line.strip()}.")
            typer.echo()

    # Display variation points
    if shape.variation_points:
        typer.echo(f"Variation Points ({len(shape.variation_points)}):")
        for var in shape.variation_points:
            prob_pct = int(var.probability * 100)
            typer.echo(f"  - {var.type} ({prob_pct}% probability, {var.position})")
            # Format description text with proper wrapping
            desc_lines = var.description.strip().replace("\n", " ").split(". ")
            for line in desc_lines:
                if line.strip():
                    typer.echo(f"    {line.strip()}.")
            typer.echo()

    # Display themes
    if shape.themes:
        themes_list = ", ".join(shape.themes)
        typer.echo(f"Themes: {themes_list}")
        typer.echo()

    # Display motifs
    if shape.motifs:
        motifs_list = ", ".join(shape.motifs)
        typer.echo(f"Motifs: {motifs_list}")
        typer.echo()

    # Display tone
    if shape.tone:
        typer.echo("Tone:")
        # Format tone text with proper wrapping
        tone_lines = shape.tone.strip().replace("\n", " ").split(". ")
        for line in tone_lines:
            if line.strip():
                typer.echo(f"  {line.strip()}.")
        typer.echo()


def register_shapes_commands(app: typer.Typer) -> None:
    """Register shape-related commands."""

    @app.command(name="shapes", help="List all story shapes, or show details of a specific shape.")
    def shapes_command(
        shape_id: Annotated[
            str | None, typer.Argument(help="Shape ID to display details for. If omitted, lists all shapes.")
        ] = None,
    ) -> None:
        """List all story shapes or show details of a specific one."""
        if shape_id is None:
            _list_shapes()
        else:
            _show_shape_details(shape_id)


__all__ = ["register_shapes_commands"]
