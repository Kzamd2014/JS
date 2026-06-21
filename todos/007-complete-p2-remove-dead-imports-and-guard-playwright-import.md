---
name: 007-pending-p2-remove-dead-imports-and-guard-playwright-import
description: Dead scraper imports at main.py startup and unguarded Playwright import in linkedin_rss.py pollute the import graph
metadata:
  type: project
  status: complete
  priority: p2
  tags: [code-review, quality, imports]
---

## Problem Statement
Three import issues pollute every process startup:

1. `main.py:12-13` imports `AdzunaScraper` and `HiringCafeScraper` unconditionally even though both are commented out of `SCRAPERS`. These modules transitively import Playwright. If Playwright is not installed (minimal environment, or after todo 005 removes it from CI), `python main.py rank` fails at import before reaching any ranking logic.

2. `scrapers/linkedin_rss.py:14` imports `from playwright.async_api import BrowserContext` at module load. This symbol is only used as a type annotation in the no-op `_search` stub. The import forces Playwright to be resolvable just to annotate a method that returns `[]`.

3. `linkedin_rss.py:78` uses `getattr(config, "LINKEDIN_RSS_FEEDS", [])` — `LINKEDIN_RSS_FEEDS` is an unconditionally defined module-level list in `config.py:12`. The `getattr` with default implies "might not exist" which is false, and suppresses `AttributeError` if the attribute is ever accidentally renamed.

## Findings
- `main.py:12-13` — `from scrapers.adzuna import AdzunaScraper` / `from scrapers.hiringcafe import HiringCafeScraper`
- `scrapers/linkedin_rss.py:14` — `from playwright.async_api import BrowserContext`
- `scrapers/linkedin_rss.py:78` — `getattr(config, "LINKEDIN_RSS_FEEDS", [])`
- `config.py:12` — `LINKEDIN_RSS_FEEDS` defined unconditionally as a module-level list

## Proposed Solutions
### Option A — Remove dead imports, guard type-only import (Recommended)
**main.py:** Remove lines 12-13. The commented-out SCRAPERS entries are sufficient documentation.

**linkedin_rss.py:** Guard the import:
```python
from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from playwright.async_api import BrowserContext
```
With `from __future__ import annotations`, all annotations are strings at runtime — the import is never executed outside type checkers.

**linkedin_rss.py:78:** Replace `getattr`:
```python
feed_urls = config.LINKEDIN_RSS_FEEDS
```

- Effort: Small
- Risk: None

### Option B — Remove the _search stub entirely (Better long-term, pairs with todo 010)
If `LinkedInRssScraper` is decoupled from `BaseScraper`, the `_search` stub and its `BrowserContext` import disappear together. This is the correct fix but depends on todo 010.

## Acceptance Criteria
- [ ] `main.py` does not import `AdzunaScraper` or `HiringCafeScraper`
- [ ] `linkedin_rss.py` does not import Playwright at runtime (TYPE_CHECKING guard or removed)
- [ ] `linkedin_rss.py:78` uses `config.LINKEDIN_RSS_FEEDS` directly
- [ ] `python main.py rank` succeeds in an environment without Playwright installed
- [ ] `pytest` passes

## Work Log
- 2026-06-20: Identified by Python quality, architecture, and simplicity review agents
