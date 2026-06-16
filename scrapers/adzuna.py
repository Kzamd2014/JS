"""
Adzuna job scraper via their REST API. Aggregates jobs from many US boards.
Free tier: 1,000 calls/month. No Playwright needed — pure HTTP.
Auth: app_id and app_key as query parameters.

After the API returns short snippets, we enrich each job by fetching its
redirect_url and extracting the full page text with stdlib html.parser.
"""
import asyncio
import html.parser
import json
import traceback
import urllib.parse
import urllib.request

import config
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, dedupe_jobs, _infer_remote
from playwright.async_api import BrowserContext

_ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/us/search/1"
_ENRICH_CONCURRENCY = 8
_FETCH_TIMEOUT = 10
_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}


class _TextExtractor(html.parser.HTMLParser):
    _SKIP = frozenset({"script", "style", "head", "noscript"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if not self._depth:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _fetch_full_description(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers=_FETCH_HEADERS)
        with urllib.request.urlopen(req, timeout=_FETCH_TIMEOUT) as resp:
            if "html" not in (resp.headers.get_content_type() or ""):
                return None
            raw = resp.read(300_000)
        try:
            parser = _TextExtractor()
            parser.feed(raw.decode("utf-8", errors="replace"))
            text = parser.get_text()
        except Exception:
            return None
        return text[:5000] if len(text) > 200 else None
    except Exception:
        return None


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

        jobs = dedupe_jobs(jobs)
        await self._enrich_descriptions(jobs)
        return jobs

    async def _enrich_descriptions(self, jobs: list[dict]) -> None:
        print(f"  [adzuna] Fetching full descriptions for {len(jobs)} jobs...")
        sem = asyncio.Semaphore(_ENRICH_CONCURRENCY)

        async def _enrich_one(job: dict) -> None:
            url = job.get("url", "")
            if not url:
                return
            async with sem:
                full = await asyncio.to_thread(_fetch_full_description, url)
            if full and len(full) > len(job.get("description", "")):
                job["description"] = full

        await asyncio.gather(*[_enrich_one(j) for j in jobs])
        enriched_count = sum(1 for j in jobs if len(j.get("description", "")) > 200)
        print(f"  [adzuna] {enriched_count}/{len(jobs)} jobs have full descriptions")

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
                description=(item.get("description") or "")[:5000],
                remote=remote,
                salary=salary,
            ))
        return jobs
