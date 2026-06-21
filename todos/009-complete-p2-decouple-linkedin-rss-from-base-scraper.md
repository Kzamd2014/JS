---
name: 009-pending-p2-decouple-linkedin-rss-from-base-scraper
description: LinkedInRssScraper inherits from a Playwright ABC but never uses a browser — false inheritance breaks LSP and forces Playwright dependency
metadata:
  type: project
  status: complete
  priority: p2
  tags: [code-review, architecture, simplicity]
---

## Problem Statement
`LinkedInRssScraper` extends `BaseScraper`, a Playwright-based abstract base class. The subclass overrides `scrape()` entirely and satisfies the `@abstractmethod _search()` requirement with a permanent no-op stub. The only value gained from the inheritance is the `_job()` helper method. This creates:

1. A required-but-dead `_search` stub that must import `BrowserContext` for its type hint
2. Misleading `scrape(titles, locations)` interface — the RSS scraper ignores both parameters
3. False promise to callers that a `LinkedInRssScraper` behaves like other `BaseScraper` subclasses (Liskov Substitution violation)
4. Playwright as a runtime dependency for a pure-HTTP module

Additionally, `AdzunaScraper._search_with_retry` is called with `context=None` (adzuna.py line ~97) because Adzuna is also pure-HTTP. Both scrapers misuse the Playwright-centric base class.

## Findings
- `scrapers/linkedin_rss.py:74` — `class LinkedInRssScraper(BaseScraper)`
- `scrapers/linkedin_rss.py:133-134` — `async def _search(self, context: BrowserContext, ...):\n    return []`
- `scrapers/adzuna.py:~97` — `await self._search_with_retry(None, title, location)` — `None` for context
- `scrapers/base.py:88` — `@abstractmethod async def _search(...)` — forces stub on all subclasses

## Proposed Solutions
### Option A — Make LinkedInRssScraper a standalone class (Recommended)
Move `_job()` to a module-level function in `base.py` (or inline it). Remove inheritance:
```python
# scrapers/linkedin_rss.py
def _job(site: str, **kwargs) -> dict:
    return {"site": site, "title": "", "company": "", "location": "",
            "url": "", "description": "", "remote": False, "salary": None, **kwargs}

class LinkedInRssScraper:
    site_name = "linkedin_rss"
    async def scrape(self, titles: list[str], locations: list[str]) -> list[dict]:
        ...
        jobs.append(_job("linkedin_rss", title=title, ...))
```
No `_search` stub needed. No Playwright import.

- Pros: Correct model — RSS scraper is not a Playwright scraper; removes dead code
- Cons: `_job()` is duplicated as a standalone function (but it's 10 lines)
- Effort: Small
- Risk: Low

### Option B — Split BaseScraper into BasePlaywrightScraper and BaseHttpScraper
Create a thin `BaseHttpScraper` with a `scrape() -> list[dict]` contract (no titles/locations, no browser). Both `LinkedInRssScraper` and `AdzunaScraper` extend `BaseHttpScraper`.
- Pros: Clean hierarchy for future HTTP scrapers
- Cons: Slightly more files; better to do when a second HTTP scraper is added
- Effort: Medium

**Recommended: Option A now, Option B when next HTTP scraper is added.**

## Acceptance Criteria
- [ ] `LinkedInRssScraper` does not inherit from `BaseScraper`
- [ ] No `_search` stub exists in `linkedin_rss.py`
- [ ] `python main.py run` works correctly
- [ ] `pytest` passes

## Work Log
- 2026-06-20: Identified by architecture and simplicity review agents
