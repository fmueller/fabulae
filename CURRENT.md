# Current

Scratchpad for what's happening right now. Start here.

## Last

- Added third-party license audit and Apache-2.0 release compliance checklist (`docs/THIRD_PARTY_LICENSE_AUDIT.md`)
- **TASK-14**: Standard scene prompts strengthened to match enhanced mode
  - Detailed location formatting (sensory details) now used in standard prompts
  - System prompt includes inner thought, multi-sensory grounding, desire/flaw-driven dialogue
  - User prompt instructions expanded: varied attribution, inner thoughts, sensory environment
- **TASK-13**: Per-format prose differentiation in build prompts
  - Novel: expansive — room for immersive description, layered subtext, extended interiority
  - Novella: focused — every scene earns its place, suggestive detail over exhaustive description
  - Short-story: economical — every sentence earns its place, implication over exposition
  - Applied to both standard and enhanced scene system prompts
- **TASK-12**: Short-story scene breaks replace `## title` headers
  - Short-story format now uses `---` scene separators instead of `## {title}` headers
  - Text output converts `---` to `* * *` (traditional fiction scene break)
  - Novel/novella formats unchanged — still use `## title` headers
- **TASK-11**: Added prose craft guidelines to build prompts
- **TASK-10**: Scene hooks now rendered distinctly in build output
- **TASK-9**: Enriched continuity summaries to preserve dialogue threads and character emotional states
- **TASK-8**: Added word count targets to build scene prompts
- **TASK-7**: Strengthened dialogue in build prompts — both standard and enhanced modes
- **TASK-6**: Added scene title generation — LLM generates short 2-5 word titles instead of using bloated summaries as headers
- **TASK-5**: Fixed pipeline selection bug — large models now correctly default to batch mode

## Next

- v0.1.0 release after remaining bug fixes
- TUI, check, doctor commands moved to v0.2.0

## Don't Forget

- OpenSpec workflow is now in `openspec/WORKFLOW.md` — no more `/opsx:*` slash commands
- Legacy tasks (01a–09) were removed along with `tasks/` folder; not migrated to backlog
- Build improvement issues migrated to backlog (TASK-5 through TASK-14)
- The `backlog board` command shows the full task board
