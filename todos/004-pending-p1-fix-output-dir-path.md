---
name: 004-pending-p1-fix-output-dir-path
description: OUTPUT_DIR uses a relative path, causing output to land in CWD instead of the project directory when invoked from elsewhere
metadata:
  type: project
  status: pending
  priority: p1
  tags: [code-review, bug, paths]
---

## Problem Statement
config.py:11 sets OUTPUT_DIR = Path("output"), which resolves relative to the current working directory at import time. Running `python /home/kzamd22/job/main.py` from /tmp silently writes scraped JSON and the dashboard to /tmp/output. A subsequent `python main.py rank` from the project directory then finds no raw files in /home/kzamd22/job/output and raises FileNotFoundError, making the scrape/rank split workflow unreliable. Additionally, calling Path.mkdir() at module import time (config.py:12) creates directories as a side effect of importing config in tests.

## Findings
- /home/kzamd22/job/config.py:11 — `OUTPUT_DIR = Path("output")` (CWD-relative)
- /home/kzamd22/job/config.py:12 — `OUTPUT_DIR.mkdir(exist_ok=True)` at import time (side effect)
- /home/kzamd22/job/dashboard.py:18 — already uses `Path(__file__).parent / "templates"` (correct pattern)
- The correct fix mirrors the pattern already present in dashboard.py

## Proposed Solutions
### Option A
Change config.py:11 to anchor OUTPUT_DIR to the config file's location:

```python
OUTPUT_DIR = Path(__file__).parent / "output"
```

This is identical to the pattern dashboard.py already uses for templates and is consistent with the project's own existing convention.

- Pros: Zero new dependencies, matches existing codebase pattern, works regardless of CWD
- Cons: None material
- Effort: Small
- Risk: Low

### Option B
Accept a --output-dir CLI argument in main.py and default it to the script-relative path. Propagate the resolved path through to config at runtime.

- Pros: Gives users flexibility to direct output elsewhere
- Cons: More wiring through main.py and config; solves a rare use case at higher complexity
- Effort: Medium
- Risk: Low

## Acceptance Criteria
- [ ] Running `python /home/kzamd22/job/main.py scrape` from /tmp produces files in /home/kzamd22/job/output/, not /tmp/output/
- [ ] Running `python /home/kzamd22/job/main.py rank` from /tmp successfully reads raw files written by a prior scrape run from the project directory
- [ ] Importing config in a test does not create directories on the filesystem as a side effect
- [ ] OUTPUT_DIR resolves to the same absolute path regardless of CWD

## Work Log
- 2026-06-01: Identified in code review
