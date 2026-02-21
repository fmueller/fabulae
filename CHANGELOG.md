# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

- Third-party dependency license audit document with Apache-2.0 compatibility and release checklist
- Prose craft guidelines in build prompts — show-don't-tell, anti-purple-prose, sentence variation, tangible details, scene entry/exit
- Distinct rendering of scene hooks in build output — italic in markdown/text, `<p class="hook">` in HTML using existing CSS
- Enriched continuity summaries with dialogue thread and emotional state tracking for better scene-to-scene coherence
- Word count targets in build scene prompts — format-aware defaults per beat (novel ~400, novella ~250, short-story ~150) with scene-level totals
- Dialogue craft guidelines in build prompts — speaker paragraph breaks, varied attribution, proportion balance
- Character desire/need/flaw now included in standard build prompts (was enhanced-only)
- Scene title generation in build — LLM produces short 2-5 word titles instead of using summaries as headers
- `title` field on Scene model with `--title` option in scene add/edit CLI
- `openspec/WORKFLOW.md` documenting the full OpenSpec workflow for agents and humans
- `BuildProgress` class with dual timer for build feature
- HTTP 400 to non-retryable errors; clean up empty response patterns
- Skip retries for HTTP 404/422 errors in JSON guard
- Increased JSON retries to all create pipelines
- Specific JSON error types for preamble text and unescaped chars
- JSON output guard for small LLM reliability
- Enhanced build command with pipeline options
- Info messages for language guard reprompts
- Language guard correction prompts for create and build

### Changed

- Replaced OpenSpec skills/commands with documentation-based workflow (`openspec/WORKFLOW.md`)
- Unified warning indicator to `⚠` across codebase
- Removed `JsonGuardConfig`, consolidated JSON retry logic across pipelines
- Unified small model detection messages across create and build
- Unified guard configuration between build and create commands

### Removed

- OpenSpec skills (10 SKILL.md files under `openspec/skills/`)
- OpenSpec commands (10 .md files under `openspec/commands/opsx/`)
- `.claude/skills/openspec-*` and `.claude/commands/opsx` symlinks

### Fixed

- Pipeline selection always defaulting to sequential regardless of model size
- Retry callback firing on exhausted final attempt
- Prioritize explicit size over keyword patterns in small model detection
- Build language guard tests made self-contained
- YAML parse errors in build command now produce clean error output
