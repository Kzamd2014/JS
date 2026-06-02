---
name: 005-pending-p1-parallelize-scrapers-and-ranker
description: Serial scraper and ranker loops make the pipeline take 45-75 minutes despite async infrastructure already being in place
metadata:
  type: project
  status: pending
  priority: p1
  tags: [code-review, performance, async]
---

## Problem Statement
All 5 scrapers execute serially in main.py:40-54 despite being fully async and I/O-bound. All Claude API ranking calls also execute serially in ranker.py:80-92 using a synchronous client. With 15 title variants × 2 locations × 5 scrapers = 150 search queries, plus 2–5s mandatory delay per request, total pipeline runtime is 45–75 minutes. The async infrastructure (Playwright, asyncio) is already in place but is never leveraged at the orchestration level. This makes iterating on the pipeline impractical.

## Findings
- /home/kzamd22/job/main.py:40-54 — scrapers called one at a time in a for loop; no concurrency
- /home/kzamd22/job/ranker.py:80-92 — ranking loop is synchronous, one API call completes before the next begins
- /home/kzamd22/job/scrapers/base.py:44-52 — inner title×location loop is serial; 30 iterations × 3.5s avg delay = ~105s in sleeps alone per scraper, ×5 scrapers = ~525s just in mandatory wait time
- Scrapers are already written as async coroutines — parallelism at the orchestration level requires minimal changes

## Proposed Solutions
### Option A
Full parallelization of both scrapers and ranker:
- In main.py: replace the serial scraper loop with `asyncio.gather(*[scraper.run() for scraper in scrapers])`
- In ranker.py: switch from `Anthropic` to `AsyncAnthropic`, wrap ranking in `asyncio.gather` with a `asyncio.Semaphore(10)` concurrency cap to avoid rate limit errors

Expected improvement: 45–75 min → 12–20 min for a typical 100-job run.

- Pros: Maximum throughput; Claude API calls are pure network I/O and parallelize perfectly
- Cons: More complex error handling — one scraper crash must not abort others; requires AsyncAnthropic client change
- Effort: Medium
- Risk: Medium

### Option B
Parallelize scrapers only (main.py change), leave ranker serial. Defer async ranker refactor.

Expected improvement: 45–75 min → 20–35 min.

- Pros: Smaller diff, easier to reason about and review; ranker stays synchronous and simple
- Cons: Ranking still dominates runtime at scale; only partial win
- Effort: Small
- Risk: Low

## Acceptance Criteria
- [ ] Full pipeline (`python main.py run`) completes in under 20 minutes for a 100-job scrape run
- [ ] A failure in one scraper does not abort the remaining scrapers (errors are logged and skipped)
- [ ] Ranked output is identical in content to the serial baseline (order may differ; scores must not)
- [ ] Rate limit errors from the Claude API are handled with exponential backoff, not silent score=50 fallback

## Work Log
- 2026-06-01: Identified in code review
