---
name: 010-pending-p2-save-ranker-cache-incrementally
description: Ranker cache written only after all futures complete — API calls are lost and re-billed if process is killed mid-run
metadata:
  type: project
  status: complete
  priority: p2
  tags: [code-review, reliability, caching]
---

## Problem Statement
`ranker.py:rank_jobs()` accumulates scored results in `new_cache_entries` and writes to `scores_cache.json` only after the `ThreadPoolExecutor` context exits (all futures complete). If the process is killed mid-run — OOM on CI, manual Ctrl-C, network timeout that exceeds the job-level timeout — all Claude API calls completed so far are lost. The next run re-scores everything at full API cost.

With 50 uncached jobs at $0.0008/1k tokens (Haiku pricing) and ~300 tokens per call, this is ~$0.012/run. Low financial impact today, but it also means waiting another 2-3 minutes for the re-run.

## Findings
- `ranker.py:180-229` — `new_cache_entries` accumulated, `_save_cache` called only at line 220 after all futures complete
- `ranker.py:194` — `with ThreadPoolExecutor(max_workers=2) as executor:` — cache save happens after `__exit__`
- No `try/finally` around the executor block

## Proposed Solutions
### Option A — Save cache inside the as_completed loop (Recommended)
Save after every N completions (e.g., every 10 jobs):
```python
CACHE_SAVE_INTERVAL = 10
completed = len(pre_ranked)
pending_saves: list[tuple[str, dict]] = []

for future in as_completed(futures):
    ...
    if cache_entry:
        pending_saves.append(cache_entry)
    completed += 1
    if len(pending_saves) >= CACHE_SAVE_INTERVAL:
        for k, v in pending_saves:
            cache[k] = v
        _save_cache(cache)
        pending_saves.clear()

# Final flush
if pending_saves:
    for k, v in pending_saves:
        cache[k] = v
    _save_cache(cache)
```
- Pros: At most N results lost on crash; atomic writes already use tmp+replace
- Cons: Slight overhead from multiple file writes (10 writes at 10-job intervals for 100 jobs)
- Effort: Small
- Risk: Low

### Option B — Wrap executor in try/finally and save on any exit
```python
try:
    with ThreadPoolExecutor(...) as executor:
        ...
finally:
    if new_cache_entries:
        for k, v in new_cache_entries:
            cache[k] = v
        _save_cache(cache)
```
- Pros: Simple; saves everything on clean or abrupt exit
- Cons: On SIGKILL (not just Ctrl-C/exception), `finally` still may not run
- Effort: Trivial

**Recommended: Option B as minimum; Option A for full protection.**

## Acceptance Criteria
- [ ] Cache is saved in a `finally` block or periodically within the loop
- [ ] Completed Claude scores are persisted even if the run is interrupted
- [ ] `_save_cache` uses the existing atomic write (tmp+replace) — no regression

## Work Log
- 2026-06-20: Identified by Python quality review agent
