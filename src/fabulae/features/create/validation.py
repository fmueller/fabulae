"""Validation functions for create command.

This module provides simple validation functions that replace complex normalization logic.
All functions return None if validation passes, or an error message string if validation fails.
"""


def validate_id_unchanged(output_id: str, expected_id: str) -> str | None:
    """Validate that the output ID matches the expected ID exactly.

    Args:
        output_id: The ID returned by the LLM
        expected_id: The ID that was provided in the prompt

    Returns:
        None if IDs match, error message if they don't match
    """
    if output_id != expected_id:
        return f"ID mismatch: expected '{expected_id}', got '{output_id}'"
    return None


def validate_character_references(refs: list[str], available: list[str]) -> str | None:
    """Validate that all character references exist in the available list.

    Args:
        refs: List of character IDs to validate
        available: List of available character IDs

    Returns:
        None if all references are valid, error message if any are invalid
    """
    if not refs:
        return None

    invalid_refs = [ref for ref in refs if ref not in available]
    if invalid_refs:
        return (
            f"Invalid character reference(s): {', '.join(invalid_refs)}. "
            f"Available characters: {', '.join(available) if available else 'none'}"
        )
    return None


def validate_location_reference(ref: str | None, available: list[str]) -> str | None:
    """Validate that a location reference exists in the available list.

    Args:
        ref: Location ID to validate (can be None)
        available: List of available location IDs

    Returns:
        None if reference is valid or None, error message if invalid
    """
    if ref is None:
        return None

    if ref not in available:
        return (
            f"Invalid location reference: '{ref}'. Available locations: {', '.join(available) if available else 'none'}"
        )
    return None


def validate_world_fact_references(refs: list[str], available: list[str]) -> str | None:
    """Validate that all world fact references exist in the available list.

    Args:
        refs: List of world fact IDs to validate
        available: List of available world fact IDs

    Returns:
        None if all references are valid, error message if any are invalid
    """
    if not refs:
        return None

    invalid_refs = [ref for ref in refs if ref not in available]
    if invalid_refs:
        return (
            f"Invalid world fact reference(s): {', '.join(invalid_refs)}. "
            f"Available world facts: {', '.join(available) if available else 'none'}"
        )
    return None
