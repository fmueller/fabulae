# Current

Scratchpad for what's happening right now. Start here.

## Last

- Unified warning indicator to `⚠` across codebase
- Removed `JsonGuardConfig`, consolidated JSON retry logic across pipelines
- Unified small model detection messages across create and build
- Fixed retry callback firing on exhausted final attempt
- Added `BuildProgress` class with dual timer for build feature
- Documented build command improvement issues (10 items → backlog TASK-5 through TASK-14)

## Next

- **TASK-5**: Fix pipeline selection bug — always defaults to sequential (`high`, `bug`)
- **TASK-1**: Simple TUI for v0.1.0 release (`high`, `feature`)
- **TASK-6 – TASK-14**: Build prompt and output improvements (`medium`, `enhancement`)

## Don't Forget

- Legacy tasks (01a–09) were removed along with `tasks/` folder; not migrated to backlog
- Build improvement issues migrated to backlog (TASK-5 through TASK-14)
- The `backlog board` command shows the full task board
