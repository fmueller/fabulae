# Current

Scratchpad for what's happening right now. Start here.

## Last

- **TASK-8**: Added word count targets to build scene prompts
- Format-aware default words per beat: novel ~400, novella ~250, short-story ~150
- Scene-level total target computed from beat targets and shown in prompt
- Both standard and enhanced system prompts now reference word-count targets
- Beats without explicit `target_words` get format-appropriate defaults in the prompt
- **TASK-7**: Strengthened dialogue in build prompts — both standard and enhanced modes
- **TASK-6**: Added scene title generation — LLM generates short 2-5 word titles instead of using bloated summaries as headers
- **TASK-5**: Fixed pipeline selection bug — large models now correctly default to batch mode

## Next

- **TASK-9 – TASK-14**: Build prompt and output improvements (`medium`, `enhancement`)
- v0.1.0 release after build improvements and bug fixes are done
- TUI, check, doctor commands moved to v0.2.0

## Don't Forget

- OpenSpec workflow is now in `openspec/WORKFLOW.md` — no more `/opsx:*` slash commands
- Legacy tasks (01a–09) were removed along with `tasks/` folder; not migrated to backlog
- Build improvement issues migrated to backlog (TASK-5 through TASK-14)
- The `backlog board` command shows the full task board
