# Task: Agent Task Breakdown Guidelines

**Priority:** High - improves agent efficiency and task quality.
**Depends on:** None

## Overview

Add comprehensive guidelines to AGENTS.md and CLAUDE.md for how AI coding agents should break down tasks, evaluate complexity per step, and select the appropriate model for each step. This improves task execution quality and helps agents work more efficiently with the right model for each subtask.

## Execution Methodology

This task should be implemented step-by-step, using the recommended model for each step:
- **Haiku**: Simple/straightforward changes (boilerplate, simple edits)
- **Sonnet**: Complex logic and architectural decisions
- **Opus**: Prompt engineering and final verification

After completing all implementation steps, switch to **Opus** model to verify the implementation is correct and complete.

## Current State

The current AGENTS.md and CLAUDE.md have basic guidelines but lack:
1. Instructions on how to break down tasks into steps
2. Guidance on evaluating complexity per step
3. Model selection recommendations per step type
4. Post-implementation documentation review requirements

## Proposed Additions

### Task Breakdown Guidelines

Agents should break down tasks into discrete steps where each step:
- Has a single, clear objective
- Can be implemented and tested independently
- Has identifiable complexity level

### Model Selection Guidance

| Step Type | Complexity | Recommended Model |
|-----------|------------|-------------------|
| Boilerplate code, simple edits, CLI flags | Low | Haiku |
| Business logic, service layer, tests | Medium | Sonnet |
| Prompt engineering, architecture decisions | High | Opus |
| Final verification and review | High | Opus |

### Documentation Review Requirement

After completing any implementation task, agents must:
1. Review if `README.md` needs updates (user-facing changes)
2. Review if `CLAUDE.md` needs updates (architectural/convention changes)
3. Review if `AGENTS.md` needs updates (structure/process changes)

## Implementation Steps

### Step 1: Update AGENTS.md with Task Guidelines
**Model: Sonnet**

Add a new section "Task Execution Guidelines" to AGENTS.md:

```markdown
## Task Execution Guidelines

### Breaking Down Tasks

When implementing a task:
1. Read the full task description to understand scope
2. Identify discrete implementation steps
3. Evaluate complexity per step (Low/Medium/High)
4. Select appropriate model per step (see Model Selection below)
5. Execute steps sequentially, verifying each before proceeding

### Model Selection per Step

| Step Type | Complexity | Recommended Model |
|-----------|------------|-------------------|
| Boilerplate, simple edits, CLI flags, file moves | Low | Haiku |
| Business logic, validation, service layer, tests | Medium | Sonnet |
| Prompt engineering, architecture, complex refactors | High | Opus |
| Final verification, code review, integration checks | High | Opus |

### Post-Implementation Documentation Review

After completing any task, check if documentation updates are needed:

1. **README.md** - Update if:
   - New CLI commands or flags added
   - User-facing behavior changed
   - New features documented

2. **CLAUDE.md** - Update if:
   - Architectural patterns changed
   - New conventions established
   - Key implementation details added

3. **AGENTS.md** - Update if:
   - Project structure changed
   - Testing guidelines updated
   - Commit conventions modified
```

**Files to modify:**
- `AGENTS.md`

**Acceptance criteria:**
- Task breakdown guidelines section added
- Model selection table included
- Documentation review checklist included

### Step 2: Update CLAUDE.md with Task Guidelines
**Model: Sonnet**

Add parallel guidance to CLAUDE.md:

```markdown
## Task Execution

### Complexity-Based Model Selection

When implementing tasks, evaluate each step's complexity and select the appropriate model:

- **Haiku** (Low complexity): Simple edits, boilerplate, file operations
- **Sonnet** (Medium complexity): Business logic, services, tests, refactoring
- **Opus** (High complexity): Prompt engineering, architecture, verification

### Documentation Maintenance

After implementing changes, review and update these files as needed:
- `README.md` for user-facing changes (CLI commands, features)
- `CLAUDE.md` for architectural/convention changes
- `AGENTS.md` for structural/process changes

Keep documentation concise but comprehensive for both human developers and AI coding agents.
```

**Files to modify:**
- `CLAUDE.md`

**Acceptance criteria:**
- Model selection guidance added
- Documentation maintenance section added

### Final Step: Opus Verification
**Model: Opus**

After all implementation steps are complete:

1. **Review both files for consistency** - Guidelines should align between AGENTS.md and CLAUDE.md
2. **Verify clarity** - Guidelines should be clear and actionable
3. **Test verification** - Run `uv run ruff check --fix && uv run mypy && uv run pytest`

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `AGENTS.md` | Modify | Add task execution guidelines section |
| `CLAUDE.md` | Modify | Add task execution and documentation maintenance sections |

## Acceptance Criteria

- [ ] Task breakdown guidelines added to AGENTS.md
- [ ] Model selection table added to AGENTS.md
- [ ] Post-implementation documentation review added to AGENTS.md
- [ ] Parallel guidance added to CLAUDE.md
- [ ] Guidelines are consistent between both files
- [ ] All checks pass (`ruff`, `mypy`, `pytest`)
