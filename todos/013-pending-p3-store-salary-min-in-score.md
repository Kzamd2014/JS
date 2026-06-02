---
name: 013-pending-p3-store-salary-min-in-score
description: Store parsed salary_min on the job dict in scorer.py so dashboard.py doesn't need to re-parse or import a private function
metadata:
  type: project
  status: pending
  priority: p3
  tags: [code-review, quality, architecture]
---

## Problem Statement
dashboard.py:4 imports private function `_parse_salary_min` from scorer.py — crosses module boundary with a private function. dashboard.py:14 calls it again to compute salary_num for sorting, even though scorer.py already ran it during score(). Double parse, private cross-module import.

## Findings
- dashboard.py:4 — private import of `_parse_salary_min`
- dashboard.py:14 — re-parses salary string that scorer already parsed
- scorer.py:87-94 — first parse, result discarded after rule adjustment is applied

## Proposed Solutions
### Option A
In scorer.score(), add salary_min to the returned dict alongside rule_score and rule_signals. dashboard.py reads job.get("salary_min", 0) directly — no import needed. Delete the import from dashboard.py. Effort: Small

## Acceptance Criteria
- [ ] `_parse_salary_min` is not imported in dashboard.py
- [ ] salary_min is stored on the job dict by scorer.py

## Work Log
- 2026-06-01: Identified in code review
