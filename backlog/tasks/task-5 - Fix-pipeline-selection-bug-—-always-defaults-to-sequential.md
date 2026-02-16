---
id: TASK-5
title: Fix pipeline selection bug — always defaults to sequential
status: To Do
assignee: []
created_date: '2026-02-16 12:14'
labels:
  - bug
  - build
dependencies: []
priority: high
---

## Description

<!-- SECTION:DESCRIPTION:BEGIN -->
In build/cli.py:120, both branches of the ternary return 'sequential'. Large models never get 'batch' mode automatically. Fix: 'sequential' if is_small else 'batch'. Originally: docs/issues/build-improvements.md#issue-1
<!-- SECTION:DESCRIPTION:END -->
