# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/), and this project adheres to [Conventional Commits](https://www.conventionalcommits.org/).

## [Unreleased]

### Added

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

- Unified warning indicator to `⚠` across codebase
- Removed `JsonGuardConfig`, consolidated JSON retry logic across pipelines
- Unified small model detection messages across create and build
- Unified guard configuration between build and create commands

### Fixed

- Retry callback firing on exhausted final attempt
- Prioritize explicit size over keyword patterns in small model detection
- Build language guard tests made self-contained
- YAML parse errors in build command now produce clean error output
