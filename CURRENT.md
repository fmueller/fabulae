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

- All 11 completed legacy tasks (01a–09) are in `tasks/` for reference; not migrated to backlog
- Build improvement issues originated from `docs/issues/build-improvements.md`
- The `backlog board` command shows the full task board
