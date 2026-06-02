---
name: 015-pending-p3-deduplicate-remote-detection
description: Extract repeated remote-inference logic from all 5 scrapers into a single helper in scrapers/base.py
metadata:
  type: project
  status: pending
  priority: p3
  tags: [code-review, quality, duplication]
---

## Problem Statement
All 5 scrapers contain the identical remote inference line: `remote = is_remote or "remote" in job_location.lower() or "hybrid" in job_location.lower()`. If the definition of remote changes (add "distributed", change "hybrid" treatment), 5 files must be updated.

## Findings
- scrapers/linkedin.py:113
- scrapers/indeed.py:84
- scrapers/glassdoor.py:73
- scrapers/wellfound.py:65
- scrapers/hiringcafe.py:65

## Proposed Solutions
### Option A
Add `_infer_remote(location: str, is_remote_search: bool) -> bool` helper to scrapers/base.py. All scrapers call it instead of repeating the logic. Effort: Small

## Acceptance Criteria
- [ ] Remote inference logic exists in exactly one place in scrapers/base.py
- [ ] All 5 scrapers call the shared helper instead of inlining the logic

## Work Log
- 2026-06-01: Identified in code review
