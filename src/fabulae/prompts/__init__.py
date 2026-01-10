"""Shared prompt helpers for Fabulae feature slices."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

import yaml

BASE_SYSTEM_PROMPT = (
    "You are Fabulae, a narrative design assistant. "
    "Return structured data only and follow the provided schema."
)


def build_system_prompt(purpose: str, guidelines: Iterable[str] | None = None) -> str:
    """Create a system prompt with optional guideline bullet points."""
    lines = [BASE_SYSTEM_PROMPT, "", purpose.strip()]
    if guidelines:
        lines.append("")
        lines.append("Guidelines:")
        lines.extend(f"- {rule.strip()}" for rule in guidelines if rule.strip())
    return "\n".join(lines).strip()


def serialize_for_prompt(value: Any) -> str:
    """Serialize values for prompt inclusion using compact YAML."""
    if hasattr(value, "model_dump"):
        value = value.model_dump()
    return yaml.safe_dump(
        value,
        sort_keys=False,
        width=1000,
        default_flow_style=False,
        allow_unicode=False,
    ).strip()


def format_sections(sections: Mapping[str, str]) -> str:
    """Format prompt sections with headings."""
    parts: list[str] = []
    for title, body in sections.items():
        cleaned = body.strip()
        if not cleaned:
            continue
        parts.append(f"## {title}\n{cleaned}")
    return "\n\n".join(parts)


def format_project_context(sections: Mapping[str, Any]) -> str:
    """Serialize and format project context sections for prompts."""
    rendered = {title: serialize_for_prompt(value) for title, value in sections.items()}
    return format_sections(rendered)


__all__ = [
    "BASE_SYSTEM_PROMPT",
    "build_system_prompt",
    "format_project_context",
    "format_sections",
    "serialize_for_prompt",
]
