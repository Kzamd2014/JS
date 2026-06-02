---
name: 010-pending-p2-move-resume-to-file
description: Extract the hardcoded resume string from config.py into a plain-text file so it can be updated without editing Python source
metadata:
  type: project
  status: pending
  priority: p2
  tags: [code-review, architecture, maintainability]
---

## Problem Statement
config.py contains a 47-line resume string as a Python literal, mixing configuration (env vars, API keys) with domain data (the resume). The resume cannot be updated without editing Python source. Additionally, ranker.py builds the system prompt at module import time, baking the resume in permanently — making it impossible to swap resumes at runtime without restarting the process.

## Findings
- config.py:39-86 — 47-line `RESUME_TEXT` string literal embedded in source
- ranker.py:3 — imports `RESUME_TEXT` from config alongside `ANTHROPIC_API_KEY`, coupling two unrelated concerns
- ranker.py:7-20 — module-level `_SYSTEM` construction runs at import time

## Proposed Solutions
### Option A
Move the resume to `data/resume.txt`. Load it in config.py with:
```python
RESUME_TEXT = (Path(__file__).parent / "data" / "resume.txt").read_text()
```
Move `_SYSTEM` construction out of module scope and into `rank_job()` (or a lazy-initialized module-level singleton via `functools.lru_cache`). Effort: Small

### Option B
Accept a `--resume PATH` CLI argument in main.py with a default of `data/resume.txt`, passing the loaded text through to `rank_job()`. This allows swapping resumes without any code change and makes the dependency explicit. Effort: Small (complements Option A)

## Acceptance Criteria
- [ ] Resume content lives in `data/resume.txt`, not in any `.py` file
- [ ] Updating the resume requires editing only `data/resume.txt`
- [ ] `_SYSTEM` prompt is not constructed at module import time
- [ ] All existing tests pass after the refactor

## Work Log
- 2026-06-01: Identified in code review
