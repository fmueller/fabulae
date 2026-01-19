"""Title structure utilities for chapter generation.

This module provides title diversity logic extracted from create/prompts_v2.py.
It is used to ensure chapter titles are varied and don't follow repetitive patterns.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

# Title structures with concrete examples for structure rotation
TITLE_STRUCTURES = [
    {
        "name": "possessive",
        "instruction": "Use possessive format: [Name]'s [Noun]",
        "examples": ["Elena's Gambit", "The Captain's Doubt", "Marcus's Betrayal"],
    },
    {
        "name": "question",
        "instruction": "Start with What/When/Where/Why/How",
        "examples": ["What the River Knows", "When Shadows Fall", "Where Trust Dies"],
    },
    {
        "name": "verb_phrase",
        "instruction": "Start with a verb (-ing or imperative)",
        "examples": ["Burning Bridges", "Breaking Silence", "Chasing Ghosts"],
    },
    {
        "name": "single_word",
        "instruction": "Use exactly ONE evocative word",
        "examples": ["Reckoning", "Descent", "Shattered", "Awakening"],
    },
    {
        "name": "preposition",
        "instruction": "Start with a preposition (Beyond, Into, Through, etc.)",
        "examples": ["Beyond the Wall", "Into Darkness", "Through Fire"],
    },
    {
        "name": "the_last_first",
        "instruction": "Use 'The Last/First/Final [Noun]' format",
        "examples": ["The Last Stand", "The First Lie", "The Final Hour"],
    },
    {
        "name": "number",
        "instruction": "Include a number in the title",
        "examples": ["Seven Days", "The Third Door", "One Last Chance"],
    },
    {
        "name": "contrast",
        "instruction": "Use contrast/opposition with 'and' or 'of'",
        "examples": ["Blood and Stone", "Ashes of Hope", "Truth in Lies"],
    },
]


@dataclass
class TitleRequirement:
    """Requirements for chapter title generation.

    This dataclass provides structured title requirements to the LLM
    to ensure diverse chapter titles.
    """

    structure_name: str
    instruction: str
    examples: list[str]
    banned_starters: list[str]
    banned_keywords: list[str]
    recent_titles: list[str]

    def format_for_prompt(self, language: str | None = None) -> str:
        """Format the title requirement as a prompt section.

        Args:
            language: Optional language code for the title

        Returns:
            Formatted title requirement string
        """
        lines = ["TITLE REQUIREMENT (MANDATORY):"]

        # Language hint
        if language:
            lines.append(f"  Language: Generate title in {language.upper()}")

        # Required structure
        lines.append(f"  Required Structure: {self.instruction}")
        examples = ", ".join(f'"{ex}"' for ex in self.examples[:2])
        lines.append(f"  Examples: {examples}")

        # Add bans
        if self.banned_starters:
            banned = ", ".join(f'"{s}"' for s in self.banned_starters[:3])
            lines.append(f"  DO NOT start with: {banned}")

        if self.banned_keywords:
            banned = ", ".join(f'"{k}"' for k in self.banned_keywords[:4])
            lines.append(f"  DO NOT use words: {banned}")

        if self.recent_titles:
            lines.append(f"  Recent titles (avoid similarity): {', '.join(self.recent_titles[-3:])}")

        return "\n".join(lines)


def _extract_title_patterns(titles: list[str]) -> dict[str, list[str]]:
    """Extract overused patterns from previous titles (language-agnostic).

    Args:
        titles: List of previous chapter titles

    Returns:
        Dictionary with 'starters', 'keywords', and 'phrases' lists
    """
    starters: list[str] = []
    all_words: list[str] = []

    for title in titles:
        words = title.split()
        if words:
            starters.append(words[0])
            all_words.extend(w for w in words if len(w) > 2)

    starter_counts = Counter(starters)
    overused_starters = [word for word, count in starter_counts.items() if count >= 2]

    word_counts = Counter(w.lower() for w in all_words)
    overused_keywords = [word for word, count in word_counts.items() if count >= 2]

    phrase_counts: Counter[str] = Counter()
    for title in titles:
        words = title.lower().split()
        for i in range(len(words) - 1):
            phrase = f"{words[i]} {words[i + 1]}"
            phrase_counts[phrase] += 1
    phrases = [phrase for phrase, count in phrase_counts.items() if count >= 2]

    return {"starters": overused_starters, "phrases": phrases, "keywords": overused_keywords}


def get_title_structure(chapter_index: int, total_chapters: int) -> dict[str, str | list[str]]:
    """Get the assigned title structure for a chapter position.

    Rotates through structures to ensure variety. The rotation is deterministic
    based on chapter index.

    Args:
        chapter_index: 0-based index of the chapter
        total_chapters: Total number of chapters (for potential future use)

    Returns:
        Structure dict with name, instruction, and examples
    """
    _ = total_chapters  # Reserved for future use
    structure_index = chapter_index % len(TITLE_STRUCTURES)
    structure = TITLE_STRUCTURES[structure_index]
    # Cast to satisfy mypy - the structure dict has known string keys
    name: str = str(structure["name"])
    instruction: str = str(structure["instruction"])
    examples: list[str] = list(structure["examples"])
    return {
        "name": name,
        "instruction": instruction,
        "examples": examples,
    }


def get_title_requirement(
    chapter_index: int,
    total_chapters: int,
    previous_titles: list[str],
) -> TitleRequirement:
    """Get title requirements for a chapter.

    This determines the title structure and extracts patterns to avoid
    from previous titles.

    Args:
        chapter_index: 0-based index of the chapter
        total_chapters: Total number of chapters
        previous_titles: List of titles already generated

    Returns:
        TitleRequirement with structure and bans
    """
    structure = get_title_structure(chapter_index, total_chapters)

    # Extract patterns to avoid from previous titles
    patterns = _extract_title_patterns(previous_titles) if previous_titles else {}

    examples_raw = structure["examples"]
    examples_list: list[str] = list(examples_raw) if isinstance(examples_raw, list) else []

    return TitleRequirement(
        structure_name=str(structure["name"]),
        instruction=str(structure["instruction"]),
        examples=examples_list,
        banned_starters=patterns.get("starters", []),
        banned_keywords=patterns.get("keywords", []),
        recent_titles=previous_titles[-3:] if previous_titles else [],
    )


def is_title_acceptable(title: str, previous_titles: list[str]) -> tuple[bool, str]:
    """Check if a title is sufficiently different from previous titles.

    Args:
        title: The title to check
        previous_titles: List of previous titles

    Returns:
        Tuple of (is_acceptable, reason_if_not)
    """
    if not previous_titles:
        return (True, "")

    title_lower = title.lower()
    title_words = set(title_lower.split())

    for prev in previous_titles:
        prev_lower = prev.lower()
        prev_words = set(prev_lower.split())

        # Check for exact match
        if title_lower == prev_lower:
            return (False, f"Identical to existing title: {prev}")

        # Check for high word overlap (more than 50% words in common)
        common_words = title_words & prev_words
        # Exclude short words
        common_words = {w for w in common_words if len(w) > 2}
        if len(common_words) >= 2 and len(common_words) / max(len(title_words), 1) > 0.5:
            return (False, f"Too similar to: {prev} (common words: {', '.join(common_words)})")

    return (True, "")


__all__ = [
    "TITLE_STRUCTURES",
    "TitleRequirement",
    "get_title_structure",
    "get_title_requirement",
    "is_title_acceptable",
]
