# Current

Scratchpad for what's happening right now. Start here.

## Last

- **TASK-5**: Fixed pipeline selection bug — large models now correctly default to batch mode
- Unified warning indicator to `⚠` across codebase
- Removed `JsonGuardConfig`, consolidated JSON retry logic across pipelines
- Unified small model detection messages across create and build
- Fixed retry callback firing on exhausted final attempt
- Added `BuildProgress` class with dual timer for build feature
- Documented build command improvement issues (10 items → backlog TASK-5 through TASK-14)

## Next

- **TASK-6 – TASK-14**: Build prompt and output improvements (`medium`, `enhancement`)
- v0.1.0 release after build improvements and bug fixes are done
- TUI, check, doctor commands moved to v0.2.0

## Don't Forget

- Legacy tasks (01a–09) were removed along with `tasks/` folder; not migrated to backlog
- Build improvement issues migrated to backlog (TASK-5 through TASK-14)
- The `backlog board` command shows the full task board
