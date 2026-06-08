"""
Google Jobs scraper via SerpAPI. Replaces the Playwright-based scraper that
triggered CAPTCHA challenges on Google's udm=8 endpoint. SerpAPI handles bot
detection and returns structured JSON from Google's Jobs index.
"""
import json
import traceback
import urllib.parse
import urllib.request

import config
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, dedupe_jobs, _infer_remote
from playwright.async_api import BrowserContext

_SERPAPI_URL = "https://serpapi.com/search.json"


class GoogleJobsScraper(BaseScraper):
    site_name = "google_jobs"

    async def scrape(self, titles: list[str], locations: list[str]) -> list[dict]:
        if not config.SERPAPI_KEY:
            print("  [google_jobs] SERPAPI_KEY not set — skipping")
            return []
        jobs: list[dict] = []
        for title in titles:
            for location in locations:
                try:
                    results = await self._search_with_retry(None, title, location)
                    jobs.extend(results)
                    print(f"  [google_jobs] '{title}' / '{location}' → {len(results)} jobs")
                except Exception as e:
                    safe_tb = traceback.format_exc().replace(config.SERPAPI_KEY, "REDACTED") if config.SERPAPI_KEY else traceback.format_exc()
                    print(
                        f"  [google_jobs] Failed '{title}'/'{location}': "
                        f"{type(e).__name__}: {str(e).replace(config.SERPAPI_KEY, 'REDACTED') if config.SERPAPI_KEY else e}\n{safe_tb}"
                    )
                await self._delay()
        return dedupe_jobs(jobs)

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        query = f"{title} remote" if is_remote else title
        chips = "date_posted:today,work_from_home:1" if is_remote else "date_posted:today"

        params: dict = {
            "engine": "google_jobs",
            "q": query,
            "chips": chips,
            "api_key": config.SERPAPI_KEY,
        }
        if not is_remote:
            params["location"] = location

        url = _SERPAPI_URL + "?" + urllib.parse.urlencode(params)
        with urllib.request.urlopen(url, timeout=15) as resp:
            data = json.loads(resp.read())

        jobs = []
        for item in data.get("jobs_results", [])[:MAX_CARDS_PER_QUERY]:
            ext = item.get("detected_extensions", {})
            job_location = item.get("location", location)
            remote = ext.get("work_from_home", False) or _infer_remote(job_location, is_remote)
            apply_options = item.get("apply_options", [])
            job_url = apply_options[0].get("link", "") if apply_options else ""
            job_title = item.get("title", "")
            company = item.get("company_name", "")
            if job_title and company:
                jobs.append(self._job(
                    title=job_title,
                    company=company,
                    location=job_location,
                    url=job_url,
                    description=item.get("description", "")[:5000],
                    remote=remote,
                    salary=ext.get("salary"),
                ))
        return jobs
