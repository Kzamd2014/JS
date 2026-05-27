"""
Wellfound (formerly AngelList Talent) scraper.
No login required. Startup/tech-heavy, good source for remote roles.
"""
import urllib.parse
from playwright.async_api import BrowserContext
from scrapers.base import BaseScraper


class WellfoundScraper(BaseScraper):
    site_name = "wellfound"

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        params: dict = {"q": title}
        if not is_remote:
            params["l"] = location
        else:
            params["remote"] = "true"

        url = "https://wellfound.com/jobs?" + urllib.parse.urlencode(params)
        page = await context.new_page()
        jobs = []
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._delay()

            # Wellfound is React-heavy; wait for job cards to render
            try:
                await page.wait_for_selector("[data-test='JobSearchResult'], .styles_component__", timeout=10000)
            except Exception:
                pass

            cards = await page.query_selector_all("[data-test='JobSearchResult'], .styles_jobResult__")
            if not cards:
                cards = await page.query_selector_all("div[class*='JobSearchResult']")

            for card in cards[:20]:
                try:
                    title_el = await card.query_selector("a[class*='jobTitle'], h2 a, [data-test='job-title']")
                    company_el = await card.query_selector("a[class*='companyName'], [data-test='company-name']")
                    location_el = await card.query_selector("[class*='location'], [data-test='job-location']")
                    salary_el = await card.query_selector("[class*='salary'], [data-test='job-salary']")

                    job_title = (await title_el.inner_text()).strip() if title_el else ""
                    company = (await company_el.inner_text()).strip() if company_el else ""
                    job_location = (await location_el.inner_text()).strip() if location_el else ""
                    salary = (await salary_el.inner_text()).strip() if salary_el else None

                    href = await title_el.get_attribute("href") if title_el else ""
                    job_url = ("https://wellfound.com" + href) if href and href.startswith("/") else href or ""

                    # Load description from job detail page
                    description = ""
                    if job_url:
                        detail = await context.new_page()
                        try:
                            await detail.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                            await self._delay()
                            desc_el = await detail.query_selector(
                                "[data-test='job-description'], .styles_description__, [class*='jobDescription']"
                            )
                            if desc_el:
                                description = (await desc_el.inner_text()).strip()
                        finally:
                            await detail.close()

                    remote = is_remote or "remote" in job_location.lower() or "hybrid" in job_location.lower()

                    if job_title and company:
                        jobs.append(self._job(
                            title=job_title,
                            company=company,
                            location=job_location or location,
                            url=job_url,
                            description=description,
                            remote=remote,
                            salary=salary,
                        ))
                except Exception:
                    continue
        finally:
            await page.close()

        return jobs
