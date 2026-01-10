"""Reusable CLI options for LLM configuration."""

from typing import cast

import typer

from fabulae.llm import DEFAULT_BASE_URL, DEFAULT_MODEL, DEFAULT_TEMPERATURE


def model_option() -> str:
    return cast(
        str,
        typer.Option(
            DEFAULT_MODEL,
            "--model",
            "-m",
            help="LLM model to use.",
        ),
    )


def temperature_option() -> float:
    return cast(
        float,
        typer.Option(
            DEFAULT_TEMPERATURE,
            "--temperature",
            "-t",
            help="LLM temperature (0.0-2.0).",
            min=0.0,
            max=2.0,
        ),
    )


def base_url_option() -> str | None:
    return cast(
        str | None,
        typer.Option(
            None,
            "--base-url",
            help="Base URL for the OpenAI-compatible endpoint.",
            show_default=f"{DEFAULT_BASE_URL} (default)",
        ),
    )


def api_key_option() -> str | None:
    return cast(
        str | None,
        typer.Option(
            None,
            "--api-key",
            help="API key for the OpenAI-compatible provider.",
        ),
    )


__all__ = ["api_key_option", "base_url_option", "model_option", "temperature_option"]
