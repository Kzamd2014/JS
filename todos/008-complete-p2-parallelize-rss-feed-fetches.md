---
name: 008-pending-p2-parallelize-rss-feed-fetches
description: Multiple RSS feed URLs fetched sequentially with blocking urllib in an async scraper — should be parallelized
metadata:
  type: project
  status: complete
  priority: p2
  tags: [code-review, performance, async]
---

## Problem Statement
`scrapers/linkedin_rss.py:84-93` fetches each feed URL sequentially with a for-loop. Each fetch uses `urllib.request.urlopen` (blocking synchronous I/O) inside an `async` method. With a single feed URL and no concurrent scrapers, this is invisible. But:
1. With N feeds, total time is N × network_RTT instead of max(network_RTT)
2. If one feed times out (15s timeout), subsequent feeds are blocked for that full window
3. Blocking I/O in an async context is an event-loop anti-pattern — it would pin the loop if asyncio.gather had other coroutines running alongside

## Findings
- `scrapers/linkedin_rss.py:84` — `for url in feed_urls:` — sequential
- `scrapers/linkedin_rss.py:99` — `urllib.request.urlopen(req, timeout=15)` — blocking sync call
- `main.py:68` — `asyncio.gather(*[_run_one(name, cls) ...])` — scrapers run concurrently, but each scraper's internal feeds are sequential
- Impact at current scale (likely 1-3 feeds): low. At 5+ feeds with slow servers: 15s × 5 = 75s worst-case vs ~15s parallel

## Proposed Solutions
### Option A — asyncio.get_event_loop().run_in_executor (Recommended)
```python
async def scrape(self, titles: list[str], locations: list[str]) -> list[dict]:
    feed_urls = config.LINKEDIN_RSS_FEEDS
    if not feed_urls:
        print("  [linkedin_rss] No LINKEDIN_RSS_FEEDS configured — skipping")
        return []

    loop = asyncio.get_event_loop()
    tasks = [loop.run_in_executor(None, self._fetch_feed, url) for url in feed_urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_jobs: list[dict] = []
    for url, result in zip(feed_urls, results):
        if isinstance(result, Exception):
            print(f"  [linkedin_rss] Failed {url}: {type(result).__name__}: {result}")
        else:
            print(f"  [linkedin_rss] {url} → {len(result)} jobs")
            all_jobs.extend(result)

    return dedupe_jobs(all_jobs)
```
`_fetch_feed` stays synchronous — it runs in the thread pool, not the event loop.

- Pros: Non-blocking, parallelizes all feed fetches, `_fetch_feed` unchanged
- Cons: Minor added complexity
- Effort: Small
- Risk: Low

### Option B — Switch to `httpx` async client
Replace `urllib` with `httpx.AsyncClient` for true async I/O without threads.
- Pros: Idiomatic async
- Cons: New dependency; adds complexity for what is currently a simple GET
- Effort: Medium

**Recommended: Option A** — minimal change, no new dependencies.

## Acceptance Criteria
- [ ] Feed URLs are fetched concurrently (not sequentially)
- [ ] Feed fetch errors are caught and logged per-URL, not raised to scrape()
- [ ] `python main.py scrape` works correctly with multiple LINKEDIN_RSS_FEEDS

## Work Log
- 2026-06-20: Identified by performance review agent
