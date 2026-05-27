"""
LinkedIn scraper. Requires LINKEDIN_COOKIES in .env (JSON array exported from browser DevTools).
Without cookies the scraper will be redirected to login and return 0 results.

To export cookies:
  1. Log in to linkedin.com in Chrome
  2. DevTools → Application → Cookies → linkedin.com
  3. Export all cookies as JSON (e.g. via EditThisCookie extension)
  4. Paste the JSON array into LINKEDIN_COOKIES in .env
"""
import urllib.parse
from playwright.async_api import BrowserContext
from config import LINKEDIN_COOKIES
from scrapers.base import BaseScraper


class LinkedInScraper(BaseScraper):
    site_name = "linkedin"

    async def _make_context(self, browser):
        return await self._make_context_with_cookies(browser, LINKEDIN_COOKIES)

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        params = {
            "keywords": title,
            "location": "" if is_remote else location,
            "f_WT": "2" if is_remote else "",  # 2 = remote filter
            "position": "1",
            "pageNum": "0",
        }
        url = "https://www.linkedin.com/jobs/search/?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v}
        )

        page = await context.new_page()
        jobs = []
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._delay()

            # Check if redirected to login
            if "login" in page.url or "authwall" in page.url:
                print(f"  [linkedin] Not authenticated — set LINKEDIN_COOKIES in .env")
                return []

            await page.wait_for_selector(".jobs-search-results__list-item, .base-card", timeout=10000)

            cards = await page.query_selector_all(".jobs-search-results__list-item, .base-card")
            for card in cards[:20]:
                try:
                    title_el = await card.query_selector(".job-card-list__title, .base-search-card__title")
                    company_el = await card.query_selector(".job-card-container__company-name, .base-search-card__subtitle")
                    location_el = await card.query_selector(".job-card-container__metadata-item, .job-search-card__location")
                    link_el = await card.query_selector("a.job-card-list__title, a.base-card__full-link")

                    job_title = (await title_el.inner_text()).strip() if title_el else ""
                    company = (await company_el.inner_text()).strip() if company_el else ""
                    job_location = (await location_el.inner_text()).strip() if location_el else ""
                    href = await link_el.get_attribute("href") if link_el else ""
                    job_url = href.split("?")[0] if href else ""

                    # Click card to load description in side panel
                    description = ""
                    if link_el:
                        await card.click()
                        await self._delay()
                        desc_el = await page.query_selector(".jobs-description__content, .show-more-less-html__markup")
                        if desc_el:
                            description = (await desc_el.inner_text()).strip()

                    remote = is_remote or "remote" in job_location.lower() or "hybrid" in job_location.lower()

                    if job_title and company:
                        jobs.append(self._job(
                            title=job_title,
                            company=company,
                            location=job_location or location,
                            url=job_url,
                            description=description,
                            remote=remote,
                        ))
                except Exception:
                    continue
        finally:
            await page.close()

        return jobs
