# Task: Remove Narrative Patterns (Dead Code Cleanup)

**Priority:** Low - code hygiene and simplification.
**Depends on:** None

## Overview

Remove the narrative patterns and plot patterns feature from the codebase. This feature was planned but never implemented - the schemas and CLI flags exist, but no generation logic was ever written. This is dead code that adds complexity without providing value.

**Important:** This is different from **Story Shapes**, which ARE implemented and actively used. Story shapes should NOT be removed.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Current State Analysis

### What Exists (But Doesn't Work)

1. **Type Alias** in `src/fabulae/features/create/schemas.py`:
   - `NarrativePatternsMode = Literal["off", "artifact", "project"]`
   - Note: The PlotPattern* and NarrativePattern* Output classes have already been removed from schemas

2. **CLI Flags** in `src/fabulae/features/create/cli.py`:
   - `--narrative-patterns` with modes: `off` (default), `artifact`, `project`
   - `--use-narrative-patterns-in-prompts` boolean flag

3. **CreateOptions** dataclass fields:
   - `narrative_patterns_mode: NarrativePatternsMode`
   - `use_narrative_patterns_in_prompts: bool`

4. **Template Files** (unused):
   - `templates/novel/plot_patterns.yml`
   - `templates/novel/narrative_patterns.yml`

5. **Prompt Comments** mentioning patterns as future features (if any remain)

### What's Missing (Never Implemented)

- No `generate_plot_patterns()` function
- No `generate_narrative_patterns()` function
- No pipeline integration
- Template files are never loaded or used
- CLI flags are accepted but ignored

### Story Shapes vs Narrative Patterns

| Feature | Story Shapes | Narrative Patterns |
|---------|--------------|-------------------|
| **Status** | IMPLEMENTED | NOT IMPLEMENTED |
| **Location** | `src/fabulae/data/story_shapes/` | `templates/*/narrative_patterns.yml` |
| **CLI Flag** | `--shape`, `--shape-file` | `--narrative-patterns` |
| **Usage** | Integrated into prose pipeline | Flags accepted but ignored |
| **Action** | KEEP | REMOVE |

## Implementation Steps

### Step 1: Remove CLI Flags
**Model: Haiku**

Remove narrative pattern flags from `src/fabulae/features/create/cli.py`:

```python
# REMOVE these parameters from create_command():
# narrative_patterns: Annotated[NarrativePatternsMode, typer.Option(...)]
# use_narrative_patterns_in_prompts: Annotated[bool, typer.Option(...)]
```

**Files to modify:**
- `src/fabulae/features/create/cli.py`

**Acceptance criteria:**
- `--narrative-patterns` flag no longer exists
- `--use-narrative-patterns-in-prompts` flag no longer exists
- `fabulae create --help` doesn't show pattern flags

### Step 2: Remove Type Alias from Schemas
**Model: Haiku**

Remove the remaining pattern-related type alias from `src/fabulae/features/create/schemas.py`:

```python
# REMOVE this:
# NarrativePatternsMode = Literal["off", "artifact", "project"]
```

Note: The PlotPattern* and NarrativePattern* Output classes have already been removed from schemas.py.

**Files to modify:**
- `src/fabulae/features/create/schemas.py`

**Acceptance criteria:**
- NarrativePatternsMode type alias removed
- No remaining pattern-related definitions
- File still contains Story Shape schemas (if any)

### Step 3: Update CreateOptions Dataclass
**Model: Haiku**

Remove pattern fields from CreateOptions:

```python
# In src/fabulae/features/create/schemas.py

@dataclass
class CreateOptions:
    format: str
    shape: StoryShape | None = None
    variation: float = 0.5
    seed: int | None = None
    enrichment: bool = True
    # REMOVE: narrative_patterns_mode: NarrativePatternsMode = "off"
    # REMOVE: use_narrative_patterns_in_prompts: bool = False
```

**Files to modify:**
- `src/fabulae/features/create/schemas.py`

**Acceptance criteria:**
- CreateOptions has no pattern-related fields
- All code creating CreateOptions updated

### Step 4: Remove Template Files
**Model: Haiku**

Delete unused template files:

```bash
rm templates/novel/plot_patterns.yml
rm templates/novel/narrative_patterns.yml
# Check other format templates for similar files
```

**Files to delete:**
- `templates/novel/plot_patterns.yml`
- `templates/novel/narrative_patterns.yml`
- Any similar files in other template directories

**Acceptance criteria:**
- No pattern template files remain
- Template directories still contain other valid files

### Step 5: Clean Up Prompt Comments
**Model: Haiku**

Remove or update comments in `src/fabulae/features/create/prompts.py` that reference patterns:

```python
# REMOVE or UPDATE comments like:
# "Plot patterns (if provided) are structural constraints..."
# "Narrative patterns (if provided) are optional guidance..."
# "Use narrative pattern tone/motifs/roles to shape..."
```

**Files to modify:**
- `src/fabulae/features/create/prompts.py`

**Acceptance criteria:**
- No misleading comments about patterns
- Comments accurately reflect current functionality

### Step 6: Update Service Layer
**Model: Haiku**

Remove pattern-related code from service layer:

```python
# In src/fabulae/features/create/service.py

# REMOVE from FORMAT_COUNT_RANGES:
# "plot_patterns": (1, 2),
# "narrative_patterns": (0, 1),
```

**Files to modify:**
- `src/fabulae/features/create/service.py`

**Acceptance criteria:**
- No pattern references in service code
- Count ranges don't include patterns

### Step 7: Update Tests
**Model: Sonnet**

Fix any tests that reference pattern fields:

```python
# In tests/unit/features/create_enrichment_schema_test.py or similar

# UPDATE any tests that create CreateOptions with pattern fields
# REMOVE any tests specifically for pattern functionality
```

**Files to modify:**
- `tests/unit/features/create_enrichment_schema_test.py`
- Any other tests referencing patterns

**Acceptance criteria:**
- All tests pass after removal
- No test references to removed functionality

### Step 8: Verify No Remaining References
**Model: Haiku**

Search for any remaining references:

```bash
# Run these searches to ensure complete removal:
grep -r "narrative_pattern" src/
grep -r "plot_pattern" src/
grep -r "NarrativePattern" src/
grep -r "PlotPattern" src/
```

**Acceptance criteria:**
- No grep results for pattern-related terms
- All references cleaned up

### Step 9: Run Full Test Suite
**Model: Haiku**

Verify everything still works:

```bash
uv run ruff check --fix
uv run mypy
uv run pytest
```

**Acceptance criteria:**
- All linting passes
- All type checking passes
- All tests pass

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - No orphaned imports or references
   - No broken code paths

2. **Completeness Check:**
   - Run grep searches to verify no remaining references to removed code
   - Verify story shapes still work correctly

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Acceptance Criteria Validation:**
   - Verify each acceptance criterion is met
   - Test the create command manually with story shapes

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Review and update `AGENTS.md` if project structure, testing guidelines, or commit conventions changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Delete

| File | Reason |
|------|--------|
| `templates/novel/plot_patterns.yml` | Never used |
| `templates/novel/narrative_patterns.yml` | Never used |

## Files to Modify

| File | Changes |
|------|---------|
| `src/fabulae/features/create/cli.py` | Remove CLI flags |
| `src/fabulae/features/create/schemas.py` | Remove schemas and CreateOptions fields |
| `src/fabulae/features/create/prompts.py` | Remove/update comments |
| `src/fabulae/features/create/service.py` | Remove count ranges |
| `tests/unit/features/create_enrichment_schema_test.py` | Update tests |

## Acceptance Criteria

- [ ] `--narrative-patterns` CLI flag removed
- [ ] `--use-narrative-patterns-in-prompts` CLI flag removed
- [ ] All pattern schemas removed from schemas.py
- [ ] CreateOptions has no pattern fields
- [ ] Template files deleted
- [ ] No grep results for pattern terms in src/
- [ ] Story shapes still work correctly
- [ ] All tests pass
- [ ] `uv run ruff check`, `uv run mypy`, and `uv run pytest` pass

## What NOT to Remove

**KEEP these - they are implemented and working:**

- Story Shapes (`src/fabulae/data/story_shapes/`)
- Story Shape CLI flags (`--shape`, `--shape-file`)
- Story Shape loader (`src/fabulae/features/create/shapes/`)
- `fabulae shapes` and `fabulae shape <id>` commands
- Any references to "shape" (not "pattern")

## Risk Assessment

**Low Risk:** This is pure dead code removal. The feature was never implemented, so removing it cannot break any working functionality.

**Verification:** After removal, run the full create command test suite to ensure story shapes still work:

```bash
# Test create with story shape
fabulae create ./test-project --idea "test" --format novel --shape heros-journey

# Verify output uses shape
cat ./test-project/plot.yml  # Should show beats from hero's journey shape
```
