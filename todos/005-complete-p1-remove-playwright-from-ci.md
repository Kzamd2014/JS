---
name: 005-pending-p1-remove-playwright-from-ci
description: CI installs Playwright/Chromium on every run but no active scraper uses a browser — wastes 90s+ and 300MB per run
metadata:
  type: project
  status: complete
  priority: p1
  tags: [code-review, ci, performance, simplicity]
---

## Problem Statement
`.github/workflows/daily-scrape.yml` caches, installs, and configures Playwright/Chromium on every weekday run. The only active scraper (`linkedin_rss`) is pure HTTP and never touches a browser. This wastes:
- Cache miss: ~5–8 minutes downloading Chromium + system deps
- Cache hit: ~1–2 minutes running `playwright install-deps chromium` (apt-get install, runs unconditionally)
- ~300MB GitHub Actions cache storage
- `playwright>=1.45.0` pip package (~30MB) installed on every run regardless

Additionally, `scrapers/linkedin_rss.py` imports `from playwright.async_api import BrowserContext` (line 14) solely to type-annotate a no-op `_search` stub. This import forces Playwright to be importable at runtime even in environments where it might not be installed.

## Findings
- `daily-scrape.yml:29-43` — three Playwright steps (cache, install browsers, install deps)
- `requirements.txt` — `playwright>=1.45.0`
- `scrapers/linkedin_rss.py:14` — `from playwright.async_api import BrowserContext` (type-only, used only in stub)
- `main.py:12-13` — `from scrapers.adzuna import AdzunaScraper` / `from scrapers.hiringcafe import HiringCafeScraper` — both pull in Playwright transitively at startup

## Proposed Solutions
### Option A — Remove Playwright steps from CI, keep package for future use (Recommended short-term)
In `daily-scrape.yml`, delete or comment out:
```yaml
# - name: Cache Playwright browsers
# - name: Install Playwright browsers
# - name: Install Playwright system deps
```
Leave `playwright>=1.45.0` in `requirements.txt` so Adzuna/HiringCafe can be re-enabled locally. Guard the `BrowserContext` import in `linkedin_rss.py` with `TYPE_CHECKING` (see todo 007).

- Pros: Immediate CI speedup with no code changes to scrapers
- Cons: `playwright install chromium` still needs to be run manually for local Playwright-based scraping

### Option B — Remove Playwright entirely (Recommended if Adzuna/HiringCafe stay disabled)
1. Remove `playwright>=1.45.0` from `requirements.txt`
2. Remove the three Playwright CI steps
3. Remove the Playwright import from `linkedin_rss.py`
4. Remove dead imports of `AdzunaScraper` and `HiringCafeScraper` from `main.py`
5. Keep `scrapers/adzuna.py` and `scrapers/hiringcafe.py` files for reference (or delete them)

- Pros: Removes ~330MB from CI, cleaner dependency tree
- Cons: Re-enabling Playwright scrapers requires adding back the package and CI steps
- Effort: Small (15 min)
- Risk: Low

## Acceptance Criteria
- [ ] CI workflow does not install Playwright or Chromium
- [ ] `python main.py run` succeeds in CI without Playwright installed (LinkedIn RSS only)
- [ ] If Option B: `playwright` not in `requirements.txt`
- [ ] CI total runtime under 5 minutes for a typical run

## Work Log
- 2026-06-20: Identified by performance and simplicity review agents
