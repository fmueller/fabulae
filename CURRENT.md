# Current

Scratchpad for what's happening right now. Start here.

## Last

- Added third-party license audit and Apache-2.0 release compliance checklist (`docs/THIRD_PARTY_LICENSE_AUDIT.md`)
- **TASK-11**: Added prose craft guidelines to build prompts
  - Show-don't-tell instruction with concrete example ("her hands trembled" not "she was nervous")
  - Anti-purple-prose: prefer concrete nouns and strong verbs over adjective/adverb chains
  - Pacing via sentence variation: short for tension, long for reflection
  - Ground abstractions in tangible sensory details
  - Enter scenes late / leave early — skip preamble
  - Applied to all four prompt builders: standard scene, enhanced scene, standard fragment, enhanced fragment
- **TASK-10**: Scene hooks now rendered distinctly in build output
- **TASK-9**: Enriched continuity summaries to preserve dialogue threads and character emotional states
- **TASK-8**: Added word count targets to build scene prompts
- **TASK-7**: Strengthened dialogue in build prompts — both standard and enhanced modes
- **TASK-6**: Added scene title generation — LLM generates short 2-5 word titles instead of using bloated summaries as headers
- **TASK-5**: Fixed pipeline selection bug — large models now correctly default to batch mode

## Next

- **TASK-12 – TASK-14**: Build prompt and output improvements (`medium`, `enhancement`)
- v0.1.0 release after build improvements and bug fixes are done
- TUI, check, doctor commands moved to v0.2.0

## Don't Forget

- OpenSpec workflow is now in `openspec/WORKFLOW.md` — no more `/opsx:*` slash commands
- Legacy tasks (01a–09) were removed along with `tasks/` folder; not migrated to backlog
- Build improvement issues migrated to backlog (TASK-5 through TASK-14)
- The `backlog board` command shows the full task board
