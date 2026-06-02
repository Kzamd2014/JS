---
name: 006-pending-p2-add-score-cache
description: Add a persistent URL-keyed cache so the Claude API is only called for new or stale jobs
metadata:
  type: project
  status: pending
  priority: p2
  tags: [code-review, performance, api-cost]
---

## Problem Statement
Every run re-calls the Claude API for every job regardless of prior runs. If 80 jobs are scraped and the run is interrupted after 40 API calls, all 80 are re-scored from scratch on the next run. At Claude API pricing this wastes money on every re-run.

## Findings
- ranker.py:80-92 — iterates all jobs serially with no cache check before calling the API
- main.py:84-95 — cmd_rank always re-scores everything, no mechanism to skip already-scored jobs

## Proposed Solutions
### Option A
Add a URL-keyed JSON cache at `output/scores_cache.json` mapping `url → {claude_score, claude_rationale, scored_at}`. `rank_job()` checks the cache first and calls the API only for new URLs. Add a 7-day TTL so stale entries are re-scored automatically. Effort: Small

### Option B
Use SQLite (`output/cache.db`) with a `scores` table indexed on `url` for better concurrent-write safety and query performance at scale. Effort: Medium

## Acceptance Criteria
- [ ] Re-running rank on the same job corpus skips API calls for already-scored jobs
- [ ] Cache file (or DB) persists between runs and survives process interruption
- [ ] Entries older than 7 days are re-scored on the next run
- [ ] Cache hit/miss counts are logged at the end of a rank run

## Work Log
- 2026-06-01: Identified in code review
