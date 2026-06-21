---
name: 011-pending-p3-minor-code-quality-fixes
description: Batch of small code quality fixes — stale comments, truthiness check bug, description length mismatch, dead HiringCafe branch
metadata:
  type: project
  status: complete
  priority: p3
  tags: [code-review, quality, cleanup]
---

## Problem Statement
A collection of low-severity but clear quality issues found across the codebase.

## Findings

### 1. scorer.py:163 — `if travel_pct` swallows 0% travel
```python
if travel_pct and travel_pct > 25:
```
`travel_pct = 0` is falsy. A job advertising "0% travel" skips the penalty check. The penalty wouldn't apply (0 is not > 25), but the pattern is wrong. Should be:
```python
if travel_pct is not None and travel_pct > 25:
```

### 2. Description truncation mismatch — 5000 vs 4000 chars
- `scrapers/linkedin_rss.py:126` — `description[:5000]` written to raw JSON
- `ranker.py:90` — `description[:4000]` before sending to Claude
- The extra 1,000 chars stored per job are always discarded at scoring. Should be a shared constant in `config.py`:
```python
DESCRIPTION_MAX_CHARS = 4000
```

### 3. main.py:54-57 — dead HiringCafe branch in `_run_one`
```python
# HiringCafe is slow (~40s/query) — primary titles + remote only (Adzuna covers KC)
titles = PRIMARY_TITLES if name == "hiringcafe" else ALL_TITLES
locations = ["remote"] if name == "hiringcafe" else LOCATIONS
```
Both `hiringcafe` and `adzuna` are disabled. The `if name == "hiringcafe"` branch is unreachable. Simplify to:
```python
jobs = await scraper.scrape(ALL_TITLES, LOCATIONS)
```
(Note: `linkedin_rss` ignores titles and locations anyway.)

### 4. ranker.py:84 — retry message magic number
```python
print(f"  Rate limited — waiting {wait}s before retry {attempt + 1}/3...")
```
The `3` is hardcoded. If `range(4)` on line 77 changes to `range(5)`, the message silently becomes wrong. Use `attempt + 1}/{max_attempts - 1}` consistently.

### 5. config.py:43 — `__getattr__` for RESUME_TEXT unnecessarily clever
`ranker.py` imports `RESUME_TEXT` at module level via `from config import RESUME_TEXT`. This triggers `__getattr__` immediately at import time, so the lazy-load provides no practical benefit. A plain module-level assignment is equally correct and much more readable:
```python
_resume_path = Path(__file__).parent / "data" / "resume.txt"
if not _resume_path.exists():
    raise FileNotFoundError(f"Resume not found at {_resume_path}...")
RESUME_TEXT = _resume_path.read_text(encoding="utf-8")
```

### 6. ranker.py:220 — variable `url` is actually a cache key
```python
for url, entry in new_cache_entries:
    cache[url] = entry
```
`url` is the string returned by `_cache_key()` (e.g., `"instructional designer||acme"`), not a URL. Rename to `cache_key`.

## Proposed Solutions
Fix each item independently — all are small, safe, targeted changes.

## Acceptance Criteria
- [ ] `scorer.py:163` uses `if travel_pct is not None and travel_pct > 25`
- [ ] Description max length is a shared constant (or both limits aligned to 4000)
- [ ] `_run_one` in main.py removed the dead hiringcafe title/location branch
- [ ] `ranker.py:220` uses `cache_key` not `url`
- [ ] `config.py` RESUME_TEXT loading is a plain assignment (or `__getattr__` is documented)
- [ ] `pytest` passes after all changes

## Work Log
- 2026-06-20: Identified by Python quality and architecture review agents
