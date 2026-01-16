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


def is_title_acceptable(
    new_title: str,
    previous_titles: list[str],
    similarity_threshold: float = 0.6,
) -> tuple[bool, str | None]:
    """Check if a new chapter title is acceptable given previous titles.

    Validates that the new title:
    1. Is not empty
    2. Is not an exact duplicate of any previous title
    3. Does not share the same opening words (first 3 words) as any previous title
    4. Does not have excessive word overlap with any previous title

    Args:
        new_title: The new title to validate
        previous_titles: List of previously generated titles
        similarity_threshold: Maximum allowed word overlap ratio (0.0-1.0)

    Returns:
        Tuple of (is_acceptable, rejection_reason).
        If acceptable, returns (True, None).
        If not acceptable, returns (False, "reason string").
    """
    if not new_title or not new_title.strip():
        return False, "Title is empty"

    new_title = new_title.strip()

    # Check for exact duplicates (case-insensitive)
    for prev in previous_titles:
        if new_title.lower() == prev.lower():
            return False, f"Exact duplicate of '{prev}'"

    # Check for repeated starting pattern (first 3+ words match)
    new_words = new_title.lower().split()[:3]
    if len(new_words) >= 2:
        new_start = " ".join(new_words)
        for prev in previous_titles:
            prev_words = prev.lower().split()[:3]
            if len(prev_words) >= 2:
                prev_start = " ".join(prev_words)
                if new_start == prev_start:
                    return False, f"Same opening pattern as '{prev}'"

    # Check for high word overlap
    new_significant = _get_significant_words(new_title)
    for prev in previous_titles:
        prev_significant = _get_significant_words(prev)
        if new_significant and prev_significant:
            overlap = len(new_significant & prev_significant)
            max_size = max(len(new_significant), len(prev_significant))
            if max_size > 0:
                overlap_ratio = overlap / max_size
                if overlap_ratio >= similarity_threshold:
                    return False, f"Too similar to '{prev}' ({overlap_ratio:.0%} word overlap)"

    return True, None


def _get_significant_words(title: str) -> set[str]:
    """Extract significant words from a title (excluding stop words).

    Args:
        title: The title to extract words from

    Returns:
        Set of significant lowercase words
    """
    stop_words = {
        "the",
        "a",
        "an",
        "of",
        "in",
        "on",
        "at",
        "to",
        "for",
        "and",
        "or",
        "but",
        "is",
        "are",
        "was",
        "were",
        "with",
    }
    words = title.lower().split()
    return {w for w in words if w not in stop_words and len(w) > 2}


def validate_title_diversity(project: Project, threshold: float = 0.5) -> list[str]:
    """Check for repetitive titles in a generated project.

    Analyzes chapter and scene titles for similarity and returns warnings
    for any titles that are too similar to each other.

    Args:
        project: The generated project to validate
        threshold: Similarity threshold (0.0-1.0). Titles with word overlap
                  >= threshold are flagged as similar. Default 0.5.

    Returns:
        List of warning messages for similar titles. Empty if no issues.
    """
    warnings: list[str] = []

    # Check chapter titles
    if project.plot.chapters:
        chapter_titles = [ch.title for ch in project.plot.chapters if ch.title]

        # Check for uniform starters (more than 50% same starting word)
        uniform_starter_warning = _check_uniform_starters(chapter_titles)
        if uniform_starter_warning:
            warnings.append(uniform_starter_warning)

        # Check for similar titles
        similar_chapters = _find_similar_titles(chapter_titles, threshold)
        if similar_chapters:
            warnings.append(f"Similar chapter titles detected: {', '.join(similar_chapters)}")

    return warnings


def _check_uniform_starters(titles: list[str], threshold: float = 0.5) -> str | None:
    """Check if more than threshold fraction of titles start with the same word.

    Args:
        titles: List of titles to check
        threshold: Fraction of titles that must share a starter to trigger warning (default 0.5)

    Returns:
        Warning message if uniform starters detected, None otherwise.
    """
    if len(titles) < 3:
        return None  # Too few titles to meaningfully check

    from collections import Counter

    starters = [title.split()[0] for title in titles if title.split()]
    if not starters:
        return None

    starter_counts = Counter(starters)
    most_common_starter, count = starter_counts.most_common(1)[0]

    if count / len(starters) > threshold:
        return f"Uniform chapter title starters: {count}/{len(starters)} titles start with '{most_common_starter}'"

    return None


def _find_similar_titles(titles: list[str], threshold: float = 0.5) -> list[str]:
    """Find titles that are too similar using word overlap.

    Uses a simple Jaccard-like similarity based on word overlap:
    similarity = |intersection| / max(|words1|, |words2|)

    Args:
        titles: List of titles to compare
        threshold: Minimum overlap ratio to flag as similar (0.0-1.0)

    Returns:
        List of similar title pairs as "title1 / title2" strings
    """
    similar: list[str] = []

    # Common words to exclude from comparison (articles, prepositions, etc.)
    stop_words = {"the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or", "but", "is", "are", "was", "were"}

    for i, title1 in enumerate(titles):
        # Extract meaningful words (lowercase, non-stopwords, length > 2)
        words1 = {w for w in title1.lower().split() if w not in stop_words and len(w) > 2}

        for title2 in titles[i + 1 :]:
            words2 = {w for w in title2.lower().split() if w not in stop_words and len(w) > 2}

            if not words1 or not words2:
                continue

            # Calculate overlap ratio
            overlap = len(words1 & words2)
            max_size = max(len(words1), len(words2))
            similarity = overlap / max_size

            if similarity >= threshold:
                similar.append(f'"{title1}" / "{title2}"')

    return similar
