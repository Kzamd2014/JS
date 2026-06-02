---
name: 012-pending-p3-deduplicate-cmd-run-rank
description: Eliminate duplicated scoring/saving/dashboard logic shared between cmd_run and cmd_rank in main.py
metadata:
  type: project
  status: pending
  priority: p3
  tags: [code-review, quality, duplication]
---

## Problem Statement
main.py:98-107 (cmd_run) copy-pastes ~8 lines of scoring/saving/dashboard logic from cmd_rank (main.py:84-95). Any change to ranking logic must be made in two places.

## Findings
main.py:84-95 and main.py:98-107 — identical body for score → rank → atomic_write → generate → print

## Proposed Solutions
### Option A
cmd_run calls asyncio.run(_run_scrapers(None)) then delegates to cmd_rank(args). cmd_rank already handles the rest. Remove duplicated lines from cmd_run. Effort: Small

## Acceptance Criteria
- [ ] cmd_run body is 3-4 lines
- [ ] Ranking logic exists in exactly one place (cmd_rank)

## Work Log
- 2026-06-01: Identified in code review
