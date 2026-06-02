---
name: 011-pending-p2-fix-regex-recompilation
description: Move regex compilation out of function bodies in scorer.py so patterns are compiled once at module load
metadata:
  type: project
  status: pending
  priority: p2
  tags: [code-review, performance]
---

## Problem Statement
scorer.py recompiles the salary regex pattern inside `_parse_salary_min()` on every invocation — and `_parse_salary_min()` is called for every job scored. The ~40 additional pattern strings in the hot `score()` loop also rely on Python's implicit `re` module cache rather than explicit pre-compilation, which can cause cache pressure and repeated overhead at scale.

## Findings
- scorer.py:15-16 — `re.compile()` called inside `_parse_salary_min()` function body, executed on every job
- scorer.py:54-168 — raw string patterns passed to `re.search()` throughout `score()` without pre-compilation

## Proposed Solutions
### Option A
Move the `_parse_salary_min` regex to module scope as a compiled constant (e.g. `_SALARY_RE = re.compile(...)`). Compile all major pattern lists used in `score()` to compiled `re.Pattern` objects at module load time, grouped by category (tools patterns, OCM patterns, etc.). Effort: Small

### Option B
Move only the salary regex to module scope — lowest effort, highest impact fix since `_parse_salary_min` is called for every job while the `score()` patterns benefit from the implicit cache on repeated runs. Effort: Extra Small

## Acceptance Criteria
- [ ] No `re.compile()` calls exist inside any function body in scorer.py
- [ ] All patterns used in `score()` are compiled once at module load
- [ ] All existing scorer tests pass unchanged after the refactor
- [ ] A comment documents that the module-scope constants are intentional pre-compilation

## Work Log
- 2026-06-01: Identified in code review
