---
name: 004-pending-p1-fix-load-latest-raw-drops-old-scraper-files
description: _load_latest_raw() silently skips raw JSON files from scrapers not in the active SCRAPERS dict
metadata:
  type: project
  status: complete
  priority: p1
  tags: [code-review, correctness, data-loss]
---

## Problem Statement
`main.py:_load_latest_raw()` (line 87) filters raw files with `if site not in SCRAPERS: continue`. Since `SCRAPERS` currently contains only `"linkedin_rss"`, any `raw_adzuna_*.json` or `raw_hiringcafe_*.json` files in `output/` are silently ignored by `python main.py rank`. If those scrapers are ever temporarily re-enabled, scraped, then disabled again before ranking, their results vanish from the ranked output with no warning. The same applies if a scraper is disabled mid-week but its files from earlier in the week are still valid.

Additionally, `cmd_rank` (unlike `cmd_run`) does not guard against an empty job list — it proceeds to `rank_jobs([])`, generates a blank `ranked_*.json`, and overwrites `output/index.html` with an empty dashboard.

## Findings
- `main.py:87` — `if site not in SCRAPERS: continue` — couples file loading to active scraper list
- `main.py:107-118` (cmd_rank) — no empty-list guard before calling `rank_jobs(jobs)`
- `main.py:121-127` (cmd_run) — correctly guards with `if not jobs: sys.exit(1)`, but cmd_rank does not

## Proposed Solutions
### Option A — Remove SCRAPERS guard from _load_latest_raw (Recommended)
```python
# Remove or replace:
if site not in SCRAPERS:
    continue
# → Remove entirely, load all raw_*.json files regardless of SCRAPERS
```
If intentional exclusion of disabled scrapers is desired, add an explicit flag:
```python
def _load_latest_raw(sites=None) -> list[dict]:
    ...
    if sites is not None and site not in sites:
        continue
```

Also add empty-list guard to `cmd_rank`:
```python
def cmd_rank(args):
    jobs = _load_latest_raw()
    if not jobs:
        print("ERROR: No jobs loaded — run 'python main.py scrape' first.")
        sys.exit(1)
    ...
```

- Pros: No silent data loss; consistent with cmd_run behavior
- Cons: If old Adzuna files are stale, they may inflate the ranked list — but this is the caller's problem, not _load_latest_raw's
- Effort: Small
- Risk: Low

### Option B — Log a warning instead of silently skipping
Keep the SCRAPERS filter but emit a warning when files are found and skipped:
```python
if site not in SCRAPERS:
    print(f"  Skipping {f.name} (site '{site}' not in active SCRAPERS)")
    continue
```
- Pros: Preserves filter behavior, surfaces the skip
- Cons: Does not fix the data-loss problem

**Recommended: Option A** — decouple file loading from active scraper list.

## Acceptance Criteria
- [ ] `_load_latest_raw()` no longer filters by `SCRAPERS` keys (or filtering is explicit)
- [ ] `cmd_rank` exits with non-zero status and a clear message when job list is empty
- [ ] `python main.py rank` correctly loads `raw_adzuna_*.json` files if they exist in `output/`

## Work Log
- 2026-06-20: Identified by architecture review agent
