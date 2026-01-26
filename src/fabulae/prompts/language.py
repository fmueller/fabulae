"""Shared prompt helpers for enforcing language output."""

from __future__ import annotations

from lingua import IsoCode639_1, Language

LANGUAGE_GUARD_TEMPLATE = (
    "You MUST output all narrative text in {language_name} ({iso_code}). "
    "Do not mix languages.\n"
    "Rewrite any text in other languages into {language_name}."
)

LANGUAGE_CORRECTION_TEMPLATE = (
    "The following output was generated in the wrong language. "
    "Translate ALL narrative text into {language_name} ({iso_code}). "
    "Keep the exact same JSON structure and field names. "
    "Only change the text content — preserve all IDs, numbers, and structural fields unchanged.\n\n"
    "Original output:\n{original_output}\n\n"
    "Return the corrected output in the same JSON format."
)


def _format_language_name(language: Language) -> str:
    return language.name.replace("_", " ").title()


def _resolve_language_name(iso_code: str) -> tuple[str, str]:
    """Resolve ISO code to (code, language_name) pair."""
    code = iso_code.strip().lower()
    language_name = code
    try:
        language = Language.from_iso_code_639_1(IsoCode639_1.from_str(code))
    except ValueError:
        language = None
    if language is not None:
        language_name = _format_language_name(language)
    return code, language_name


def build_language_guard_prompt(iso_code: str) -> str:
    code, language_name = _resolve_language_name(iso_code)
    return LANGUAGE_GUARD_TEMPLATE.format(language_name=language_name, iso_code=code)


def build_language_correction_prompt(iso_code: str, original_output: str) -> str:
    """Build a correction prompt that asks the LLM to translate wrong-language output.

    Args:
        iso_code: Target language ISO 639-1 code (e.g. 'de', 'fr').
        original_output: The wrong-language output serialized as JSON.

    Returns:
        A prompt instructing the LLM to translate text fields while preserving structure.
    """
    code, language_name = _resolve_language_name(iso_code)
    return LANGUAGE_CORRECTION_TEMPLATE.format(
        language_name=language_name,
        iso_code=code,
        original_output=original_output,
    )


__all__ = [
    "LANGUAGE_CORRECTION_TEMPLATE",
    "LANGUAGE_GUARD_TEMPLATE",
    "build_language_correction_prompt",
    "build_language_guard_prompt",
]
