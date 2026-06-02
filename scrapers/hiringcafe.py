"""
Hiring Cafe scraper. Low bot protection, straightforward to scrape.
Uses the search endpoint at hiring.cafe with keyword and location filters.
"""
import urllib.parse
from playwright.async_api import BrowserContext
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, _infer_remote


class HiringCafeScraper(BaseScraper):
    site_name = "hiringcafe"

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        params: dict = {"q": title}
        if not is_remote:
            params["location"] = location
        else:
            params["remote"] = "1"

        url = "https://hiring.cafe/?" + urllib.parse.urlencode(params)
        page = await context.new_page()
        jobs = []
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._delay()

            try:
                await page.wait_for_selector("[class*='job'], article, .result", timeout=10000)
            except Exception:
                pass

            cards = await page.query_selector_all(
                "article, [class*='jobCard'], [class*='job-card'], li[class*='result']"
            )

            # Reuse a single detail page for all cards to avoid opening 20+ tabs
            detail_page = await context.new_page()
            try:
                for card in cards[:MAX_CARDS_PER_QUERY]:
                    try:
                        title_el = await card.query_selector("h2, h3, [class*='title'], [class*='jobTitle']")
                        company_el = await card.query_selector("[class*='company'], [class*='employer']")
                        location_el = await card.query_selector("[class*='location'], [class*='place']")
                        salary_el = await card.query_selector("[class*='salary'], [class*='pay'], [class*='compensation']")
                        link_el = await card.query_selector("a")

                        job_title = (await title_el.inner_text()).strip() if title_el else ""
                        company = (await company_el.inner_text()).strip() if company_el else ""
                        job_location = (await location_el.inner_text()).strip() if location_el else ""
                        salary = (await salary_el.inner_text()).strip() if salary_el else None
                        href = await link_el.get_attribute("href") if link_el else ""
                        job_url = ("https://hiring.cafe" + href) if href and href.startswith("/") else href or ""

                        description = ""
                        if job_url:
                            await detail_page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                            await self._delay()
                            desc_el = await detail_page.query_selector(
                                "[class*='description'], [class*='jobDescription']"
                            )
                            if desc_el:
                                description = (await desc_el.inner_text()).strip()[:5000]

                        remote = _infer_remote(job_location, is_remote)

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
                    except Exception as e:
                        print(f"  [hiringcafe] Card error ({type(e).__name__}): {e}")
                        continue
            finally:
                await detail_page.close()
        finally:
            await page.close()

        return jobs
