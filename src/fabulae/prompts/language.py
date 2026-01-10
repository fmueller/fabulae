"""Shared prompt helpers for enforcing language output."""

from __future__ import annotations

from lingua import IsoCode639_1, Language

LANGUAGE_GUARD_TEMPLATE = (
    "You MUST output all narrative text in {language_name} ({iso_code}). "
    "Do not mix languages.\n"
    "Rewrite any text in other languages into {language_name}."
)


def _format_language_name(language: Language) -> str:
    return language.name.replace("_", " ").title()


def build_language_guard_prompt(iso_code: str) -> str:
    code = iso_code.strip().lower()
    language_name = code
    try:
        language = Language.from_iso_code_639_1(IsoCode639_1.from_str(code))
    except ValueError:
        language = None
    if language is not None:
        language_name = _format_language_name(language)
    return LANGUAGE_GUARD_TEMPLATE.format(language_name=language_name, iso_code=code)


__all__ = ["build_language_guard_prompt", "LANGUAGE_GUARD_TEMPLATE"]
