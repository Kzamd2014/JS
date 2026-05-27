import asyncio
import json
import random
from abc import ABC, abstractmethod
from playwright.async_api import async_playwright, Browser, BrowserContext

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


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
                            results = await self._search(context, title, location)
                            jobs.extend(results)
                            print(f"  [{self.site_name}] '{title}' / '{location}' → {len(results)} jobs")
                        except Exception as e:
                            print(f"  [{self.site_name}] Error '{title}' / '{location}': {e}")
                        await self._delay()
            finally:
                await browser.close()
        return self._dedupe(jobs)

    async def _make_context(self, browser: Browser) -> BrowserContext:
        return await browser.new_context(user_agent=USER_AGENT)

    async def _make_context_with_cookies(self, browser: Browser, cookies_json: str) -> BrowserContext:
        context = await browser.new_context(user_agent=USER_AGENT)
        try:
            cookies = json.loads(cookies_json)
            if cookies:
                await context.add_cookies(cookies)
        except (json.JSONDecodeError, Exception):
            pass
        return context

    @abstractmethod
    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        pass

    async def _delay(self):
        await asyncio.sleep(random.uniform(2, 5))

    def _dedupe(self, jobs: list[dict]) -> list[dict]:
        seen: set[tuple] = set()
        result = []
        for job in jobs:
            key = (job.get("title", "").lower().strip(), job.get("company", "").lower().strip())
            if key not in seen:
                seen.add(key)
                result.append(job)
        return result

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
