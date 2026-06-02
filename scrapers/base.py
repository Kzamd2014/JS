import asyncio
import json
import random
import traceback
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, BrowserContext

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

MAX_CARDS_PER_QUERY = 20


def dedupe_jobs(jobs: list[dict]) -> list[dict]:
    """Deduplicate by (title, company, location). When the same job appears from multiple
    sites, keep the version with the longer description so scoring has more signal."""
    seen: dict[tuple, int] = {}
    result = []
    for job in jobs:
        key = (
            job.get("title", "").lower().strip(),
            job.get("company", "").lower().strip(),
            job.get("location", "").lower().strip(),
        )
        if key not in seen:
            seen[key] = len(result)
            result.append(job)
        else:
            idx = seen[key]
            if len(job.get("description", "")) > len(result[idx].get("description", "")):
                result[idx] = job
    return result


def _infer_remote(location: str, is_remote_search: bool) -> bool:
    loc = location.lower()
    return is_remote_search or "remote" in loc or "hybrid" in loc


class BaseScraper(ABC):
    site_name: str = ""

    async def scrape(self, titles: list[str], locations: list[str]) -> list[dict]:
        jobs: list[dict] = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await self._make_context(browser)
            try:
                for title in titles:
                    for location in locations:
                        try:
                            results = await self._search_with_retry(context, title, location)
                            jobs.extend(results)
                            print(f"  [{self.site_name}] '{title}' / '{location}' → {len(results)} jobs")
                        except Exception as e:
                            print(
                                f"  [{self.site_name}] Failed '{title}'/'{location}' after retries: "
                                f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                            )
                        await self._delay()
            finally:
                await browser.close()
        return dedupe_jobs(jobs)

    async def _make_context(self, browser: Browser) -> BrowserContext:
        return await browser.new_context(user_agent=USER_AGENT)

    async def _make_context_with_cookies(self, browser: Browser, cookies_json: str) -> BrowserContext:
        context = await browser.new_context(user_agent=USER_AGENT)
        if not cookies_json or not cookies_json.strip() or cookies_json.strip() == "[]":
            return context
        try:
            cookies = json.loads(cookies_json)
            if isinstance(cookies, list) and cookies:
                await context.add_cookies(cookies)
        except json.JSONDecodeError as e:
            print(f"  [{self.site_name}] Warning: cookie JSON parse error at position {e.pos}")
        except Exception as e:
            print(f"  [{self.site_name}] Warning: could not apply cookies: {type(e).__name__}: {e}")
        return context

    @abstractmethod
    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        pass

    async def _search_with_retry(
        self, context: BrowserContext, title: str, location: str, max_attempts: int = 3
    ) -> list[dict]:
        for attempt in range(max_attempts):
            try:
                return await self._search(context, title, location)
            except Exception as e:
                if attempt == max_attempts - 1:
                    raise
                wait = 2 ** (attempt + 1) + random.uniform(0, 1)
                print(f"  [{self.site_name}] Retry {attempt + 1}/{max_attempts - 1} in {wait:.1f}s: {e}")
                await asyncio.sleep(wait)
        return []

    async def _delay(self):
        await asyncio.sleep(random.uniform(2, 5))

    def _job(self, **kwargs) -> dict:
        return {
            "site": self.site_name,
            "title": "",
            "company": "",
            "location": "",
            "url": "",
            "description": "",
            "remote": False,
            "salary": None,
            **kwargs,
        }
