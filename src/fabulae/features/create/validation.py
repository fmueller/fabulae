"""Validation functions for create command.

This module provides simple validation functions that replace complex normalization logic.
All functions return None if validation passes, or an error message string if validation fails.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fabulae.models import Project


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


# =============================================================================
# Title diversity validation
# =============================================================================

# Common words to ignore when comparing titles (articles, prepositions, etc.)
_STOP_WORDS = frozenset({
    "a", "an", "the", "of", "in", "to", "for", "on", "at", "by",
    "and", "or", "but", "is", "was", "are", "were", "be", "been",
    "with", "from", "as", "into", "through", "during", "before", "after",
})


def _tokenize_title(title: str) -> set[str]:
    """Tokenize a title into meaningful words.

    Removes stop words and normalizes to lowercase.

    Args:
        title: The title to tokenize

    Returns:
        Set of meaningful words from the title
    """
    words = title.lower().split()
    # Filter out stop words and very short words
    return {word for word in words if word not in _STOP_WORDS and len(word) > 2}


def _calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate similarity between two titles using word overlap.

    Uses Jaccard similarity of meaningful words (excluding stop words).

    Args:
        title1: First title
        title2: Second title

    Returns:
        Similarity score from 0.0 (no overlap) to 1.0 (identical)
    """
    words1 = _tokenize_title(title1)
    words2 = _tokenize_title(title2)

    if not words1 or not words2:
        return 0.0

    # Jaccard similarity: intersection / union
    intersection = len(words1 & words2)
    union = len(words1 | words2)

    return intersection / union if union > 0 else 0.0


def find_similar_titles(titles: list[str], threshold: float = 0.5) -> list[tuple[str, str, float]]:
    """Find pairs of titles that are too similar.

    Args:
        titles: List of titles to compare
        threshold: Similarity threshold (0.0-1.0). Pairs above this are flagged.
            Default 0.5 catches titles sharing half their meaningful words.

    Returns:
        List of (title1, title2, similarity) tuples for similar pairs
    """
    similar_pairs: list[tuple[str, str, float]] = []

    for i, title1 in enumerate(titles):
        for title2 in titles[i + 1:]:
            similarity = _calculate_title_similarity(title1, title2)
            if similarity >= threshold:
                similar_pairs.append((title1, title2, similarity))

    return similar_pairs


def validate_title_diversity(project: Project, threshold: float = 0.5) -> list[str]:
    """Check for repetitive titles in a project and return warnings.

    Validates both chapter titles (if chapters exist) and scene titles (if present).
    Uses word overlap to detect similar titles.

    Args:
        project: The Project to validate
        threshold: Similarity threshold (0.0-1.0). Default 0.5.

    Returns:
        List of warning messages for similar titles found
    """
    warnings: list[str] = []

    # Check chapter titles
    if project.plot.chapters:
        chapter_titles = [ch.title for ch in project.plot.chapters if ch.title]
        if len(chapter_titles) >= 2:
            similar_chapters = find_similar_titles(chapter_titles, threshold)
            for title1, title2, similarity in similar_chapters:
                warnings.append(
                    f"Similar chapter titles detected ({similarity:.0%} overlap): "
                    f'"{title1}" / "{title2}"'
                )

    # Check scene summaries (scenes don't have titles, but summaries can be repetitive)
    # We check the first few words of summaries as a proxy for "title-like" content
    if project.plot.scenes:
        scene_summaries = [
            scene.summary.split(".")[0]  # First sentence
            for scene in project.plot.scenes
            if scene.summary
        ]
        if len(scene_summaries) >= 2:
            similar_scenes = find_similar_titles(scene_summaries, threshold)
            # Only warn if many scenes are similar (some overlap is natural)
            if len(similar_scenes) > len(scene_summaries) // 4:
                warnings.append(
                    f"Many scene summaries share similar patterns ({len(similar_scenes)} pairs). "
                    "Consider varying scene descriptions more."
                )

    return warnings
