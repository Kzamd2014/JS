---
name: 014-pending-p3-fix-walrus-double-regex
description: Replace double regex call in main.py list comprehension with walrus operator, and remove dead return in scrapers/base.py
metadata:
  type: project
  status: pending
  priority: p3
  tags: [code-review, quality, simplicity]
---

## Problem Statement
main.py:68 calls ts_pattern.search(f.stem) twice in the same list comprehension — once for truthiness, once to call .group(1). This is redundant and could theoretically return different results if the filesystem changed between calls (edge case). The walrus operator idiom is already used on line 65 in the same function.

## Findings
- main.py:68 — `ts_pattern.search(f.stem) and ts_pattern.search(f.stem).group(1) == latest_ts`
- scrapers/base.py:88 — dead `return []` that is unreachable after the retry loop's raise

## Proposed Solutions
### Option A
Replace the double call with `(m := ts_pattern.search(f.stem)) and m.group(1) == latest_ts` — one call, consistent with the line 65 idiom. Also remove dead `return []` at scrapers/base.py:88. Effort: Small

## Acceptance Criteria
- [ ] Single regex search per file in the list comprehension (no double call)
- [ ] Dead `return []` removed from scrapers/base.py

## Work Log
- 2026-06-01: Identified in code review
