---
name: 016-pending-p3-normalize-card-cap
description: Replace per-scraper hard-coded card caps with a single MAX_CARDS_PER_QUERY constant in scrapers/base.py
metadata:
  type: project
  status: pending
  priority: p3
  tags: [code-review, quality, consistency]
---

## Problem Statement
Scrapers cap results inconsistently — linkedin.py:63 and indeed.py:36 use cards[:20], wellfound.py:40 and hiringcafe.py:40 use cards[:15], glassdoor.py:41 uses cards[:20]. No named constant. Changing the cap requires editing 5 files.

## Findings
- scrapers/linkedin.py:63 — `cards[:20]`
- scrapers/indeed.py:36 — `cards[:20]`
- scrapers/glassdoor.py:41 — `cards[:20]`
- scrapers/wellfound.py:40 — `cards[:15]`
- scrapers/hiringcafe.py:40 — `cards[:15]`

## Proposed Solutions
### Option A
Add `MAX_CARDS_PER_QUERY = 20` constant to scrapers/base.py. All scrapers import and use it. Decide on one value (20 recommended) to normalize the inconsistency between scrapers. Effort: Small

## Acceptance Criteria
- [ ] Single MAX_CARDS_PER_QUERY constant defined in scrapers/base.py
- [ ] All 5 scrapers reference MAX_CARDS_PER_QUERY instead of a hard-coded integer

## Work Log
- 2026-06-01: Identified in code review
