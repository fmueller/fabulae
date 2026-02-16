# OpenSpec Workflow

OpenSpec is a spec-driven development workflow for planning, specifying, and implementing non-trivial changes. It uses a directory-based artifact system — no CLI binary required. Agents and humans interact with it by reading and writing files.

This document replaces the previous skill/command system. Everything an agent needs to follow the workflow is here.

## When to Use OpenSpec

- **Trivial fix** (typo, one-liner, config change) → backlog task only, skip OpenSpec
- **Non-trivial behavior change** (new feature, architectural change, prompt rewrite) → backlog task + OpenSpec change

## Directory Structure

```
openspec/
├── config.yaml              # Project config (schema, context, rules)
├── specs/                   # Main specs (living documentation of requirements)
│   └── <capability>/
│       └── spec.md
├── changes/                 # Active changes (in-progress work)
│   ├── <change-name>/
│   │   ├── proposal.md      # Why we're doing this
│   │   ├── specs/           # Delta specs (what changes)
│   │   │   └── <capability>/
│   │   │       └── spec.md
│   │   ├── design.md        # How we'll build it
│   │   └── tasks.md         # Implementation checklist
│   └── archive/             # Completed changes
│       └── YYYY-MM-DD-<name>/
└── WORKFLOW.md              # This file
```

## The Artifact Sequence

Changes follow a **spec-driven** schema with four artifacts created in order:

```
proposal → specs → design → tasks
```

Each artifact builds on the previous ones:

| Artifact | Purpose | Depends On |
|----------|---------|------------|
| `proposal.md` | Why we're doing this, what changes, capabilities, impact | Nothing |
| `specs/<capability>/spec.md` | Detailed requirements with testable scenarios | Proposal |
| `design.md` | Technical decisions, architecture, approach | Proposal + Specs |
| `tasks.md` | Implementation checklist with checkboxes | All above |

## Workflow Phases

### Phase 1: Explore (Optional)

Think through the problem before committing to a direction. This is a thinking stance, not a workflow step.

**Rules:**
- Read files, search code, investigate the codebase freely
- Use ASCII diagrams to visualize
- NEVER write application code during exploration
- MAY create OpenSpec artifacts if the user asks (that's capturing thinking, not implementing)

**When exploring with an active change**, read existing artifacts for context and offer to capture decisions:

| Insight Type | Where to Capture |
|---|---|
| New requirement discovered | `specs/<capability>/spec.md` |
| Design decision made | `design.md` |
| Scope changed | `proposal.md` |
| New work identified | `tasks.md` |

### Phase 2: New Change

Create the change directory and scaffold.

**Steps:**
1. Determine a kebab-case name from the user's description (e.g., "add user authentication" → `add-user-auth`)
2. Create the directory structure:
   ```
   mkdir -p openspec/changes/<name>/specs
   ```
3. Show the artifact sequence and what comes first (the proposal)
4. Stop and wait for user direction — do NOT create artifacts yet

**Naming rules:**
- Must be kebab-case (e.g., `add-dark-mode`, `fix-auth-bug`)
- If a change with that name already exists, suggest continuing it instead

### Phase 3: Continue (Create Artifacts)

Create artifacts one at a time, in dependency order.

**For each artifact:**
1. Read all completed dependency artifacts for context
2. Create the artifact file using the templates below
3. Show progress (N/M artifacts complete) and what's now unlocked
4. Stop after creating ONE artifact

**Fast-forward variant:** Create ALL artifacts in one pass when the user wants to move quickly. Use the todo list to track progress through the artifacts.

#### Artifact Templates

**proposal.md:**
```markdown
## Why

[1-2 sentences explaining the problem/opportunity]

## What Changes

- [Bullet points of what will be different]

## Capabilities

### New Capabilities
- `<capability-name>`: [brief description]

### Modified Capabilities
- `<capability-name>`: [what changes]

## Impact

- `src/path/to/file.ext`: [what changes]
```

**specs/\<capability\>/spec.md** (delta spec format):
```markdown
## ADDED Requirements

### Requirement: <Name>

<Description of what the system should do>

#### Scenario: <Scenario name>

- **WHEN** <trigger condition>
- **THEN** <expected outcome>
- **AND** <additional outcome if needed>

## MODIFIED Requirements

### Requirement: <Existing Name>
#### Scenario: <New scenario to add>
- **WHEN** <trigger>
- **THEN** <outcome>

## REMOVED Requirements

### Requirement: <Deprecated Name>

## RENAMED Requirements

- FROM: `### Requirement: Old Name`
- TO: `### Requirement: New Name`
```

Only include sections that apply (e.g., skip REMOVED if nothing is removed).

**design.md:**
```markdown
## Context

[Brief context about the current state]

## Goals / Non-Goals

**Goals:**
- [What we're trying to achieve]

**Non-Goals:**
- [What's explicitly out of scope]

## Decisions

### Decision 1: [Key decision]

[Explanation of approach and rationale]
```

**tasks.md:**
```markdown
## 1. [Category or file area]

- [ ] 1.1 [Specific task description]
- [ ] 1.2 [Specific task description]

## 2. [Another category]

- [ ] 2.1 [Specific task description]

## 3. Verify

- [ ] 3.1 [Verification step]
```

#### Artifact Creation Rules

- Each capability listed in the proposal's Capabilities section gets its own spec file
- The `specs/` directory uses the **capability name**, not the change name
- Delta specs represent **intent**, not wholesale replacement — include only what's changing
- Design should reference specs; tasks should reference design decisions
- Keep tasks small, clear, and in logical order

### Phase 4: Apply (Implementation)

Implement tasks from `tasks.md`, checking them off as you go.

**Steps:**
1. Read ALL context files (proposal, specs, design, tasks) before starting
2. Show current progress: "N/M tasks complete"
3. For each pending task:
   - Announce which task is being worked on
   - Make the code changes
   - Keep changes minimal and focused
   - Mark complete in tasks.md: `- [ ]` → `- [x]`
   - Also update the corresponding backlog task status (see [Backlog Integration](#backlog-integration))
4. On completion or pause, show status

**Pause if:**
- Task is unclear → ask for clarification
- Implementation reveals a design issue → suggest updating artifacts
- Error or blocker encountered → report and wait for guidance

**The workflow is fluid** — you can apply before all artifacts are done (if tasks exist), update artifacts mid-implementation, and interleave with other phases.

### Phase 5: Verify (Optional)

Verify that implementation matches the change artifacts across three dimensions:

**Completeness:**
- Are all tasks in `tasks.md` checked off?
- Are all requirements from delta specs implemented? (Search codebase for evidence)

**Correctness:**
- Does implementation match requirement intent? (Map requirements to code)
- Are scenarios from specs covered? (Check for tests or code handling each scenario)

**Coherence:**
- Does implementation follow design decisions? (Compare `design.md` to code)
- Does new code follow project patterns? (File naming, directory structure, style)

**Scoring:**
- CRITICAL: Must fix before archive (incomplete tasks, missing requirements)
- WARNING: Should fix (spec divergence, missing scenario coverage)
- SUGGESTION: Nice to fix (pattern inconsistencies)

**Graceful degradation:** If only `tasks.md` exists, verify task completion only. If tasks + specs exist, add correctness. If full artifacts, verify all three.

### Phase 6: Sync Specs

Merge delta specs from a change into main specs. This is an **agent-driven** operation — read delta specs and directly edit main specs for intelligent merging.

**Steps:**
1. Find delta specs at `openspec/changes/<name>/specs/*/spec.md`
2. For each capability with a delta spec:
   a. Read the delta spec
   b. Read the main spec at `openspec/specs/<capability>/spec.md` (may not exist)
   c. Apply changes:
      - **ADDED**: Add new requirements (if already exists, update it)
      - **MODIFIED**: Apply partial changes — add scenarios without copying existing ones
      - **REMOVED**: Remove the entire requirement block
      - **RENAMED**: Find and rename the requirement
   d. Create new main spec file if the capability doesn't exist yet
3. Show summary of what was updated

**Key principle:** Delta specs represent *intent*, not wholesale replacement. Adding a scenario means including just that scenario under MODIFIED — existing scenarios in the main spec are preserved.

**Idempotency:** Running sync twice should give the same result.

### Phase 7: Archive

Move a completed change to the archive.

**Steps:**
1. Check artifact completion — warn if any artifacts are incomplete
2. Check task completion — warn if any tasks are unchecked
3. Assess delta spec sync state:
   - If delta specs exist and haven't been synced → offer to sync first (recommended)
   - If already synced or no delta specs → proceed
4. Move the change:
   ```bash
   mkdir -p openspec/changes/archive
   mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>
   ```
5. Show summary (change name, archive location, sync status)

**Don't block on warnings** — inform and confirm, then proceed if the user agrees.

### Bulk Archive

When archiving multiple changes at once:

1. List active changes, let user select which to archive
2. For each selected change, gather: artifact status, task completion, delta specs
3. Detect spec conflicts (2+ changes touching the same capability)
4. Resolve conflicts by checking the codebase:
   - Only one implemented → sync that one's specs
   - Both implemented → apply in chronological order (older first)
   - Neither implemented → skip sync, warn user
5. Show consolidated status table, confirm, then archive in order

## Backlog Integration

The backlog (`backlog/` directory) is the **single source of truth** for all task tracking. OpenSpec's `tasks.md` is a detailed checklist within a change, but every task must also exist in the backlog.

### When Creating tasks.md

After creating the `tasks.md` artifact for a change, **create a matching backlog task for each item**:

```bash
backlog task create "<task title>" \
  --ref "openspec/changes/<name>/tasks.md" \
  --label "<change-name>" \
  --priority <priority>
```

Rules:
- Include `--ref openspec/changes/<name>/tasks.md` to link back to the change
- Add a label matching the change name (e.g., `--label add-auth`)
- The **backlog task is the source of truth** for status
- The OpenSpec checkbox is kept **in sync** when applying (check off in both places)

### When Applying Tasks

When marking a task complete in `tasks.md`:
1. Check off the task: `- [ ]` → `- [x]`
2. Update the corresponding backlog task status to match

### Why Both?

- `backlog board` always shows the **full picture** across all work — OpenSpec and non-OpenSpec
- `tasks.md` provides **detailed context** within a change (references to specs, design decisions)
- The backlog is what humans and agents check first; OpenSpec artifacts are the deep context

## Typical Workflow Summary

```
1. Identify non-trivial work
2. Explore the problem space (optional)
3. Create a new change:     mkdir -p openspec/changes/<name>/specs
4. Create artifacts:        proposal → specs → design → tasks
5. Sync tasks to backlog:   backlog task create for each task
6. Implement:               work through tasks, check off in tasks.md + backlog
7. Verify (optional):       check completeness, correctness, coherence
8. Sync specs:              merge delta specs to main specs
9. Archive:                 mv to openspec/changes/archive/YYYY-MM-DD-<name>
10. Update CURRENT.md:      move to "Last", update "Next"
```

## Reference: config.yaml

```yaml
schema: spec-driven

# Project context (optional)
# Shown to agents when creating artifacts.
# context: |
#   Tech stack: Python, Typer, Pydantic v2
#   We use conventional commits

# Per-artifact rules (optional)
# rules:
#   proposal:
#     - Keep proposals under 500 words
#   tasks:
#     - Break tasks into chunks of max 2 hours
```

Context and rules from config.yaml are **constraints for the agent**, not content for artifact files. Never copy `context` or `rules` blocks into artifact output.
