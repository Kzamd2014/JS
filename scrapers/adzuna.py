"""
Adzuna job scraper via their REST API. Aggregates jobs from many US boards.
Free tier: 1,000 calls/month. No Playwright needed — pure HTTP.
Auth: app_id and app_key as query parameters.
"""
import json
import traceback
import urllib.parse
import urllib.request

import config
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, dedupe_jobs, _infer_remote
from playwright.async_api import BrowserContext

_ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"


def _fmt_salary(lo, hi) -> str | None:
    if lo and hi:
        return f"${int(lo):,}–${int(hi):,}"
    if lo:
        return f"${int(lo):,}+"
    return None


class AdzunaScraper(BaseScraper):
    site_name = "adzuna"

    async def scrape(self, titles: list[str], locations: list[str]) -> list[dict]:
        if not config.ADZUNA_APP_ID or not config.ADZUNA_APP_KEY:
            print("  [adzuna] ADZUNA_APP_ID or ADZUNA_APP_KEY not set — skipping")
            return []
        jobs: list[dict] = []
        for title in titles:
            for location in locations:
                try:
                    results = await self._search_with_retry(None, title, location)
                    jobs.extend(results)
                    print(f"  [adzuna] '{title}' / '{location}' → {len(results)} jobs")
                except Exception as e:
                    safe_tb = traceback.format_exc().replace(config.ADZUNA_APP_KEY, "REDACTED")
                    print(
                        f"  [adzuna] Failed '{title}'/'{location}': "
                        f"{type(e).__name__}: {str(e).replace(config.ADZUNA_APP_KEY, 'REDACTED')}\n{safe_tb}"
                    )
                await self._delay()
        return dedupe_jobs(jobs)

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        params: dict = {
            "app_id": config.ADZUNA_APP_ID,
            "app_key": config.ADZUNA_APP_KEY,
            "results_per_page": MAX_CARDS_PER_QUERY,
            "what": f"{title} remote" if is_remote else title,
            "sort_by": "date",
            "max_days_old": 4,
        }
        if not is_remote:
            params["where"] = location

        url = _ADZUNA_URL + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())

        jobs = []
        for item in data.get("results", []):
            job_title = item.get("title", "")
            company = item.get("company", {}).get("display_name", "")
            if not job_title or not company:
                continue
            job_location = item.get("location", {}).get("display_name", location)
            remote = _infer_remote(job_location, is_remote) or _infer_remote(job_title, False)
            salary = _fmt_salary(item.get("salary_min"), item.get("salary_max"))
            jobs.append(self._job(
                title=job_title,
                company=company,
                location=job_location,
                url=item.get("redirect_url", ""),
                description=item.get("description", "")[:5000],
                remote=remote,
                salary=salary,
            ))
        return jobs
