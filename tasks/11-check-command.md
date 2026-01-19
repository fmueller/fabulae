# Task: Check Command (Semantic & Quality Checks)

**Priority:** Medium - enhances project quality assurance.
**Depends on:** `10-tui-simple.md` (v0.1.0 release)

## Overview

Add a `check` command that performs semantic and quality checks on a Fabulae project using LLM analysis. Unlike `validate` which checks structural correctness (valid IDs, references, required fields), `check` analyzes the narrative content for coherence, consistency, and quality issues.

All LLM interactions must use structured output (Pydantic models) via `create_agent()` from `src/fabulae/llm/`.
Check output must follow the project language via the shared language guard.
Language mismatches in project content should be reported as warnings (not errors).

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Command Signature

```bash
fabulae check <project-dir> [--model MODEL] [--temperature TEMP] [--checks all|consistency|pacing|characters|world] [--format text|json]
```

## Comparison: validate vs check

| Aspect | `validate` | `check` |
|--------|-----------|---------|
| Speed | Fast (local) | Slow (LLM calls) |
| Type | Structural | Semantic |
| Examples | Missing references, invalid IDs | Character motivation gaps, pacing issues |
| LLM | No | Yes |
| Deterministic | Yes | No |

## Check Categories

### 1. Consistency Checks
- Character behavior consistency across scenes
- World fact contradictions
- Timeline/chronology issues
- Location continuity errors

### 2. Pacing Checks
- Scene length distribution
- Beat density analysis
- Tension arc evaluation
- Chapter balance

### 3. Character Checks
- Character arc completeness
- Motivation clarity
- Relationship dynamics
- Character voice distinctiveness

### 4. World Checks
- World-building completeness
- Setting utilization
- Rule consistency
- Atmosphere coherence

### 5. Craft Checks
- Show vs. tell balance
- Dialogue authenticity
- Description density
- POV consistency

## Implementation Steps

### Step 1: Design Check Result Models
**Model: Sonnet**

Create structured output types in `src/fabulae/features/check/models.py`:

```python
from enum import Enum
from pydantic import BaseModel

class CheckSeverity(str, Enum):
    ERROR = "error"       # Significant issue that should be fixed
    WARNING = "warning"   # Potential issue worth reviewing
    INFO = "info"         # Suggestion for improvement

class CheckCategory(str, Enum):
    CONSISTENCY = "consistency"
    PACING = "pacing"
    CHARACTERS = "characters"
    WORLD = "world"
    CRAFT = "craft"

class CheckIssue(BaseModel):
    category: CheckCategory
    severity: CheckSeverity
    message: str
    location: str | None = None  # e.g., "scene:scene-01", "character:vera"
    suggestion: str | None = None

class CheckResult(BaseModel):
    issues: list[CheckIssue]
    summary: str
    overall_score: int | None = None  # 1-10 optional quality score
```

### Step 2: Design Check Prompts
**Model: Opus**

Create specialized prompts for each check category in `src/fabulae/features/check/prompts.py`.
Follow the patterns established in `src/fabulae/features/entities/prompts.py` and `src/fabulae/features/create/prompts.py`.

1. **Consistency check prompt**:
   - Input: Full project context
   - Focus: Find contradictions, continuity errors, timeline issues
   - Output: List of CheckIssue models

2. **Pacing check prompt**:
   - Input: Plot structure, scenes, beats
   - Focus: Analyze rhythm, tension, balance
   - Output: Pacing issues and suggestions

3. **Character check prompt**:
   - Input: Characters, their appearances in scenes
   - Focus: Arc completeness, motivation clarity, distinctiveness
   - Output: Character-related issues

4. **World check prompt**:
   - Input: World facts, their usage in scenes
   - Focus: Completeness, consistency, atmosphere
   - Output: World-building issues

5. **Master check prompt** (for `--checks all`):
   - Combines all categories
   - May need to be run in stages to avoid token limits

Each prompt must instruct the model to emit only the `CheckIssue` list (or `CheckResult`) as structured output.

### Step 3: Implement Check Runner
**Model: Sonnet**

Create `src/fabulae/features/check/service.py`:

```python
from fabulae.llm import LLMConfig, create_agent
from fabulae.features.check.models import CheckCategory, CheckIssue, CheckResult

async def run_checks(
    project: Project,
    categories: list[CheckCategory],
    config: LLMConfig,
) -> CheckResult:
    """Run specified checks on the project."""
    all_issues: list[CheckIssue] = []

    for category in categories:
        checker = get_checker(category)
        issues = await checker.check(project, config)
        all_issues.extend(issues)

    return CheckResult(
        issues=all_issues,
        summary=generate_summary(all_issues),
    )
```

### Step 4: Implement Category Checkers
**Model: Sonnet**

Create individual checker modules under the feature slice:

**`src/fabulae/features/check/__init__.py`**
**`src/fabulae/features/check/consistency.py`**
**`src/fabulae/features/check/pacing.py`**
**`src/fabulae/features/check/characters.py`**
**`src/fabulae/features/check/world.py`**

Each checker:
1. Formats relevant project data for prompt
2. Calls LLM with category-specific prompt using `create_agent()`
3. Parses structured output into CheckIssue list
4. Validates issue text language with the shared language guard and retries on mismatch
5. Adds warning issues for content language mismatches in the project
6. Returns issues

Structured output usage example (follow pattern from entity suggest):
```python
from fabulae.llm import create_agent

agent = create_agent(CheckResult, system_prompt, config)
result = await agent.run()
issues = result.data.issues
```

### Step 5: Implement CLI Command
**Model: Sonnet**

Create `src/fabulae/features/check/cli.py` following the pattern in `src/fabulae/features/entities/`:

```python
from fabulae.features.check.service import run_checks

def register_check_command(app: typer.Typer) -> None:
    @app.command()
    def check(
        project_dir: Annotated[Path, typer.Argument(help="Path to Fabulae project")],
        model: str = model_option(),
        temperature: float = temperature_option(),
        checks: Annotated[str, typer.Option("--checks", "-c")] = "all",
        format: Annotated[str, typer.Option("--format", "-f")] = "text",
    ) -> None:
        """
        Run semantic and quality checks on a Fabulae project.

        Unlike 'validate' which checks structure, 'check' uses an LLM to analyze
        narrative coherence, character consistency, pacing, and more.
        """
        # Load and validate project first
        project = load_project(project_dir)

        # Parse check categories
        categories = parse_check_categories(checks)

        # Run checks
        config = LLMConfig(model=model, temperature=temperature)
        result = asyncio.run(run_checks(project, categories, config))

        # Output results
        if format == "text":
            print_check_results(result)
        elif format == "json":
            print(result.model_dump_json(indent=2))
```

Wire it in `src/fabulae/main.py`:

```python
from fabulae.features.check.cli import register_check_command

register_check_command(app)
```

### Step 6: Implement Result Formatting
**Model: Haiku**

Create formatted output for terminal using Rich (already a dependency):

```python
from rich.console import Console

def print_check_results(result: CheckResult) -> None:
    """Print check results in a readable format."""
    console = Console()

    # Group by severity
    errors = [i for i in result.issues if i.severity == CheckSeverity.ERROR]
    warnings = [i for i in result.issues if i.severity == CheckSeverity.WARNING]
    infos = [i for i in result.issues if i.severity == CheckSeverity.INFO]

    if errors:
        console.print("\n[red]Errors:[/red]")
        for issue in errors:
            console.print(f"  ✗ [{issue.category}] {issue.message}")
            if issue.location:
                console.print(f"    Location: {issue.location}")
            if issue.suggestion:
                console.print(f"    Suggestion: {issue.suggestion}")

    # Similar for warnings and infos...

    # Summary
    console.print(f"\n{result.summary}")
```

### Step 7: Add Progress Feedback
**Model: Haiku**

Since checks take time, provide feedback using Rich progress:

```python
with console.status("[bold green]Running consistency checks...") as status:
    consistency_issues = await consistency_checker.check(project, config)
    status.update("[bold green]Running pacing checks...")
    pacing_issues = await pacing_checker.check(project, config)
    # etc.
```

### Step 8: Handle Check Failures Gracefully
**Model: Sonnet**

1. If one check category fails, continue with others
2. Report partial results with indication of failed checks
3. Handle LLM parsing errors (retry or report)

### Step 9: Write Tests
**Model: Sonnet**

Create `tests/unit/features/check_test.py`:

1. Test check result models
2. Mock LLM responses for each checker (use `FABULAE_FAKE_LLM=1` or mock `create_agent`)
3. Test CLI with various --checks options
4. Test output formats (text, json)
5. Test handling of check failures

### Step 10: TUI Integration (Optional)
**Model: Sonnet**

Add check functionality to the TUI if implementing the advanced TUI (task 13):
- Add `[c]heck` keyboard shortcut
- Show check results in a dedicated panel
- Allow filtering by category/severity

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete, switch to Opus model and verify:

1. **Code Quality Review:**
   - All changes follow codebase conventions
   - No duplicate code introduced
   - Error handling is appropriate
   - Type hints are complete

2. **Integration Check:**
   - All new code integrates properly with existing code
   - Imports are correct
   - No circular dependencies

3. **Test Verification:**
   - Run `uv run ruff check --fix && uv run mypy && uv run pytest`
   - All tests pass
   - No regressions introduced

4. **Acceptance Criteria Validation:**
   - Verify each acceptance criterion is met
   - Test the check command manually with a sample project

5. **Documentation Review:**
   - Review and update `README.md` if the feature adds/changes CLI commands or user-facing behavior
   - Review and update `CLAUDE.md` if architectural patterns, conventions, or key implementation details changed
   - Keep all documentation concise but detailed enough for coding agents and human users

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/fabulae/features/check/__init__.py` | Create | Package init |
| `src/fabulae/features/check/models.py` | Create | Check result models |
| `src/fabulae/features/check/service.py` | Create | Check orchestration |
| `src/fabulae/features/check/prompts.py` | Create | Check prompts |
| `src/fabulae/features/check/consistency.py` | Create | Consistency checker |
| `src/fabulae/features/check/pacing.py` | Create | Pacing checker |
| `src/fabulae/features/check/characters.py` | Create | Character checker |
| `src/fabulae/features/check/world.py` | Create | World checker |
| `src/fabulae/features/check/cli.py` | Create | CLI command implementation |
| `src/fabulae/main.py` | Modify | Add check command |
| `tests/unit/features/check_test.py` | Create | Unit tests |

## Example Output

```bash
$ fabulae check ./my-novel --checks all

Running checks...
  ✓ Consistency checks complete
  ✓ Pacing checks complete
  ✓ Character checks complete
  ✓ World checks complete

Errors:
  ✗ [consistency] Character "Marcus" is described as left-handed in scene-01
    but uses his right hand in scene-05
    Location: scene:scene-05, beat:beat-02
    Suggestion: Update scene-05 to maintain left-handed consistency

Warnings:
  ⚠ [pacing] Chapter 2 contains only 2 scenes while other chapters average 5
    Location: chapter:chapter-02
    Suggestion: Consider expanding or merging with adjacent chapter

  ⚠ [characters] Character "Inspector Chen" appears in 1 scene but is
    listed as a major supporting character
    Location: character:inspector-chen
    Suggestion: Increase appearances or adjust role designation

Info:
  ℹ [world] The "synesthesia lab" location is defined but never used in any scene
    Location: world-fact:synesthesia-lab
    Suggestion: Consider adding a scene set in this location

Summary: Found 1 error, 2 warnings, and 1 info across 4 check categories.
```

## Acceptance Criteria

- [ ] `fabulae check` command runs all check categories
- [ ] `--checks` option allows selecting specific categories
- [ ] Results formatted clearly with severity indicators
- [ ] JSON output works for programmatic use
- [ ] Progress feedback during long-running checks
- [ ] `--model` and `--temperature` options work correctly
- [ ] Partial results returned if some checks fail
- [ ] All tests pass
- [ ] `ruff check`, `mypy`, and `pytest` pass

## Notes

- Consider caching check results to avoid re-running unchanged checks
- May want to add `--fix` option in future to auto-fix simple issues
- Check prompts are critical for quality - invest time in prompt engineering
- Consider adding severity thresholds (e.g., `--fail-on warning`)
