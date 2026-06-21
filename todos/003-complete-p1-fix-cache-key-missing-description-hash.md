---
name: 003-pending-p1-fix-cache-key-missing-description-hash
description: Ranker cache key uses only title+company — reposted or updated jobs silently receive stale Claude scores
metadata:
  type: project
  status: complete
  priority: p1
  tags: [code-review, correctness, caching]
---

## Problem Statement
`ranker.py:_cache_key()` identifies jobs by `"{title}||{company}"`. If the same company reposts a role with updated requirements (common for evergreen positions), the cached `claude_score` from the earlier description is returned without an API call. The ranking order reflects stale data, directly causing missed opportunities for the job search. The existing `prompt_hash` mechanism already handles resume changes; the same approach should be applied per-job for description changes.

Also: the variable at `ranker.py:220` is named `url` but it is actually a cache key string (`"{title}||{company}"`). This naming will cause confusion if anyone assumes the cache is keyed by URL and tries to look up `job["url"]`, producing silent misses.

## Findings
- `ranker.py:18-21` — `_cache_key` returns `f"{title}||{company}"`, ignores description
- `ranker.py:220` — `for url, entry in new_cache_entries` — `url` is misleadingly named; it is a cache key
- Dedupe logic in `base.py:dedupe_jobs` uses `(title, company, location)` — stricter than the cache key (location missing)
- Two different postings for the same title at a large employer (e.g., "Instructional Designer @ Cerner") will collide

## Proposed Solutions
### Option A — Add truncated description hash to key (Recommended)
```python
import hashlib

def _cache_key(job: dict) -> str:
    title = (job.get("title") or "").lower().strip()
    company = (job.get("company") or "").lower().strip()
    desc = (job.get("description") or "")[:4000]
    desc_hash = hashlib.sha256(desc.encode()).hexdigest()[:8]
    return f"{title}||{company}||{desc_hash}"
```
Also rename `url` → `cache_key` at line 220.

- Pros: Precise cache invalidation per description content; aligns with how ranker uses description
- Cons: Existing cache entries have old key format — all get cache-missed on first run after change (acceptable, they'll be refilled)
- Effort: Small
- Risk: Low (one-time cache miss)

### Option B — Include location in key
```python
return f"{title}||{company}||{location}"
```
- Pros: Matches dedupe key more closely
- Cons: Does not detect description changes; same problem if role is reposted with same location

### Option C — Key by job URL
Use `job["url"]` as primary key when available.
- Pros: Stable, unique per listing
- Cons: LinkedIn RSS `link` fields can change (UTM params, pagination artifacts); not reliably stable across runs

**Recommended: Option A** — description hash makes the key content-addressable.

## Acceptance Criteria
- [ ] `_cache_key` includes a truncated hash of `description[:4000]`
- [ ] Variable at `ranker.py:220` renamed from `url` to `cache_key`
- [ ] Existing `output/scores_cache.json` cleared or auto-invalidated on first run (keys won't match)
- [ ] `pytest tests/test_ranker.py` passes

## Work Log
- 2026-06-20: Identified by security, performance, and Python quality review agents
