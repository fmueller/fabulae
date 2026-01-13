# Task: Sequential Pipeline Improvements

**Priority:** Medium - improves generation quality for small models.
**Depends on:** None

## Overview

Address two quality issues observed in the sequential pipeline:
1. **Title repetition**: Chapter and scene titles tend to repeat similar patterns across generated content
2. **Character count uniformity**: Every scene tends to have the same number of characters, lacking natural variety

These issues are especially noticeable with small models (<13B) using the sequential pipeline.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Issue 1: Title Repetition

### Current Behavior
Generated chapters often have similar title patterns:
- "Chapter 1: The Beginning of the Journey"
- "Chapter 2: The Journey Continues"
- "Chapter 3: The Journey Deepens"

Scenes within chapters also repeat patterns:
- "The Discovery"
- "The Revelation"
- "The Confrontation"

### Root Cause Analysis

1. Small models have limited creativity in title generation
2. Sequential pipeline generates titles one at a time with limited prior context
3. No explicit constraint to avoid repetition
4. Prompts don't emphasize title diversity

### Proposed Solutions

1. **Pre-generate title word banks** using RNG for variety
2. **Include previously used titles** in prompts to encourage avoidance
3. **Add title patterns to story shapes** for structural variety
4. **Post-process validation** to flag/reject repetitive titles

## Issue 2: Character Count Uniformity

### Current Behavior
Every scene has the same number of characters (e.g., always 2-3):
- Scene 1: [protagonist, antagonist]
- Scene 2: [protagonist, antagonist]
- Scene 3: [protagonist, antagonist]

### Root Cause Analysis

1. Sequential pipeline uses heuristics in `structure.py` that may be too uniform
2. Character assignment doesn't vary based on scene type
3. No guidance on scene-appropriate character counts
4. RNG variation not applied to character counts

### Proposed Solutions

1. **Use scene type to determine character count range**
   - Action scenes: 1-2 characters
   - Dialogue scenes: 2-3 characters
   - Ensemble scenes: 3-5 characters

2. **Apply RNG variation to character counts** within ranges

3. **Add character count hints to story shapes** for beat types

## Implementation Steps

### Step 1: Analyze Current Title Generation
**Model: Sonnet**

Review and document the current title generation approach:

1. Read `src/fabulae/features/create/prompts_v2.py` for title prompts
2. Read `src/fabulae/features/create/structure.py` for structure generation
3. Identify where titles are generated and what context is provided
4. Document findings for improvement

**Files to review:**
- `src/fabulae/features/create/prompts_v2.py`
- `src/fabulae/features/create/structure.py`
- `src/fabulae/features/create/pipelines/sequential.py`

**Acceptance criteria:**
- Clear understanding of current title generation
- Identified points for improvement

### Step 2: Add Title Diversity to Prompts
**Model: Opus**

Update prompts to include:
1. List of previously used titles to avoid
2. Explicit instruction for title variety
3. Style-appropriate title guidance

Example prompt addition:
```python
# In prompts_v2.py chapter generation
previously_used = [ch.title for ch in state.chapters if ch.title]
if previously_used:
    prompt += f"\n\nPreviously used chapter titles (DO NOT repeat these patterns):\n"
    prompt += "\n".join(f"- {title}" for title in previously_used)
    prompt += "\n\nCreate a UNIQUE title that differs from the above."
```

**Files to modify:**
- `src/fabulae/features/create/prompts_v2.py`

**Acceptance criteria:**
- Prompts include previously used titles
- Explicit diversity instruction added
- Works for both chapter and scene titles

### Step 3: Implement RNG-Based Character Count Variation
**Model: Sonnet**

Update `src/fabulae/features/create/structure.py` to vary character counts:

```python
from fabulae.features.create.variation import ProjectVariation

def _assign_scene_characters(
    scene_index: int,
    available_characters: list[str],
    variation: ProjectVariation,
    scene_type: str | None = None,
) -> list[str]:
    """Assign characters to a scene with variety based on scene type."""
    rng = variation.rng

    # Define ranges based on scene type/beat kind
    if scene_type in ("action", "chase", "solo"):
        min_chars, max_chars = 1, 2
    elif scene_type in ("dialogue", "confrontation", "revelation"):
        min_chars, max_chars = 2, 3
    elif scene_type in ("ensemble", "gathering", "finale"):
        min_chars, max_chars = 3, min(5, len(available_characters))
    else:
        # Default varies based on scene index for natural pacing
        # Early scenes: fewer chars, mid scenes: more, late: climactic
        act_position = scene_index / max(1, total_scenes)
        if act_position < 0.25:  # Act 1
            min_chars, max_chars = 1, 3
        elif act_position < 0.75:  # Act 2
            min_chars, max_chars = 2, 4
        else:  # Act 3
            min_chars, max_chars = 2, 5

    # Apply variation
    target_count = rng.randint(min_chars, max_chars)
    target_count = min(target_count, len(available_characters))

    # Select characters with weighted probability
    # Protagonist more likely, minor characters less likely
    selected = _weighted_character_selection(
        available_characters, target_count, rng
    )

    return selected
```

**Files to modify:**
- `src/fabulae/features/create/structure.py`
- `src/fabulae/features/create/graph.py` (if character assignment is here)

**Acceptance criteria:**
- Character counts vary by scene
- Scene type influences character count
- RNG ensures reproducibility with seed

### Step 4: Add Post-Generation Validation for Title Repetition
**Model: Sonnet**

Add validation in `src/fabulae/features/create/validation.py`:

```python
def validate_title_diversity(project: Project) -> list[str]:
    """Check for repetitive titles and return warnings."""
    warnings = []

    # Check chapter titles
    if project.plot.chapters:
        chapter_titles = [ch.title for ch in project.plot.chapters if ch.title]
        duplicates = _find_similar_titles(chapter_titles, threshold=0.7)
        if duplicates:
            warnings.append(
                f"Similar chapter titles detected: {', '.join(duplicates)}"
            )

    # Check scene titles
    if project.plot.scenes:
        scene_titles = [s.title for s in project.plot.scenes if s.title]
        duplicates = _find_similar_titles(scene_titles, threshold=0.7)
        if duplicates:
            warnings.append(
                f"Similar scene titles detected: {', '.join(duplicates)}"
            )

    return warnings


def _find_similar_titles(titles: list[str], threshold: float = 0.7) -> list[str]:
    """Find titles that are too similar using simple word overlap."""
    similar = []
    for i, title1 in enumerate(titles):
        words1 = set(title1.lower().split())
        for title2 in titles[i + 1:]:
            words2 = set(title2.lower().split())
            if not words1 or not words2:
                continue
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            if overlap >= threshold:
                similar.append(f"{title1} / {title2}")
    return similar
```

**Files to modify:**
- `src/fabulae/features/create/validation.py`

**Acceptance criteria:**
- Title similarity detection works
- Warnings generated for repetitive titles
- Threshold is configurable

### Step 5: Integrate Validation into Pipeline
**Model: Haiku**

Call title validation after generation and display warnings:

```python
# In service.py or cli.py after generation
from fabulae.features.create.validation import validate_title_diversity

warnings = validate_title_diversity(project)
for warning in warnings:
    progress.warn(warning)
```

**Files to modify:**
- `src/fabulae/features/create/cli.py` or `service.py`

**Acceptance criteria:**
- Warnings displayed for repetitive titles
- User can identify quality issues

### Step 6: Write Tests
**Model: Sonnet**

Create tests for new functionality:

**`tests/unit/features/create/title_diversity_test.py`:**
```python
from fabulae.features.create.validation import _find_similar_titles, validate_title_diversity


def test_find_similar_titles() -> None:
    titles = [
        "The Beginning of the Journey",
        "The Journey Continues",
        "A New Discovery",
    ]
    similar = _find_similar_titles(titles, threshold=0.5)
    assert len(similar) == 1  # First two are similar


def test_find_similar_titles_no_duplicates() -> None:
    titles = ["The Storm", "A Quiet Night", "Final Confrontation"]
    similar = _find_similar_titles(titles, threshold=0.7)
    assert len(similar) == 0
```

**`tests/unit/features/create/character_assignment_test.py`:**
```python
from fabulae.features.create.structure import _assign_scene_characters
from fabulae.features.create.variation import ProjectVariation


def test_character_count_varies_with_seed() -> None:
    chars = ["protagonist", "antagonist", "mentor", "ally", "rival"]

    # Run multiple times with different seeds
    counts = []
    for seed in range(10):
        variation = ProjectVariation(seed=seed)
        assigned = _assign_scene_characters(0, chars, variation)
        counts.append(len(assigned))

    # Should have some variety (not all the same)
    assert len(set(counts)) > 1, "Character counts should vary"
```

**Files to create:**
- `tests/unit/features/create/title_diversity_test.py`
- `tests/unit/features/create/character_assignment_test.py`

**Acceptance criteria:**
- Title similarity detection tested
- Character count variation tested
- Edge cases covered

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - RNG usage maintains reproducibility
   - Type hints are complete

2. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass

3. **Manual Testing:**
   - Generate a novel with sequential pipeline
   - Verify chapter titles are diverse
   - Verify scene character counts vary
   - Test with different seeds for consistency

4. **Documentation Review:**
   - Update CLAUDE.md if variation patterns changed
   - No README changes needed

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/create/prompts_v2.py` | Modify | Add title diversity to prompts |
| `src/fabulae/features/create/structure.py` | Modify | Vary character counts |
| `src/fabulae/features/create/validation.py` | Modify | Add title diversity validation |
| `src/fabulae/features/create/cli.py` | Modify | Display diversity warnings |
| `tests/unit/features/create/title_diversity_test.py` | Create | Title diversity tests |
| `tests/unit/features/create/character_assignment_test.py` | Create | Character assignment tests |

## Acceptance Criteria

- [ ] Title prompts include previously used titles to avoid
- [ ] Character counts vary by scene type and position
- [ ] RNG-based variation maintains seed reproducibility
- [ ] Post-generation validation flags repetitive titles
- [ ] Warnings displayed for quality issues
- [ ] All tests pass
- [ ] All checks pass (`ruff`, `mypy`, `pytest`)

## Example Improvement

### Before (Uniform)
```yaml
chapters:
  - title: "The Journey Begins"
  - title: "The Journey Continues"
  - title: "The Journey's End"

scenes:
  - characters: [protagonist, antagonist]  # Always 2
  - characters: [protagonist, antagonist]  # Always 2
  - characters: [protagonist, antagonist]  # Always 2
```

### After (Varied)
```yaml
chapters:
  - title: "A Fateful Meeting"
  - title: "Shadows in the Palace"
  - title: "The Final Reckoning"

scenes:
  - characters: [protagonist]              # Solo scene
  - characters: [protagonist, mentor]      # Dialogue
  - characters: [protagonist, antagonist, ally, rival]  # Ensemble
```
