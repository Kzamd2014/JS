"""
Glassdoor scraper. Full descriptions require login.
Without GLASSDOOR_COOKIES set, we scrape preview text only (~200 chars).
"""
import urllib.parse
from playwright.async_api import BrowserContext
from config import GLASSDOOR_COOKIES
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, _infer_remote


class GlassdoorScraper(BaseScraper):
    site_name = "glassdoor"

    async def _make_context(self, browser):
        return await self._make_context_with_cookies(browser, GLASSDOOR_COOKIES)

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        encoded_title = urllib.parse.quote(title)
        if is_remote:
            url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded_title}&remoteWorkType=1&fromAge=7"
        else:
            url = f"https://www.glassdoor.com/Job/jobs.htm?sc.keyword={encoded_title}&locT=C&locKeyword={urllib.parse.quote(location)}&fromAge=7"

        page = await context.new_page()
        jobs = []
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._delay()

            # Dismiss sign-in modal if present
            try:
                close_btn = await page.query_selector("[alt='Close'], .modal_closeIcon, [data-test='modal-close-btn']")
                if close_btn:
                    await close_btn.click()
                    await self._delay()
            except Exception:
                pass

            cards = await page.query_selector_all("[data-test='jobListing'], .react-job-listing, li[data-id]")
            for card in cards[:MAX_CARDS_PER_QUERY]:
                try:
                    title_el = await card.query_selector("[data-test='job-title'], .job-title, a.jobLink")
                    company_el = await card.query_selector("[data-test='employer-name'], .job-search-key-l2wjgv")
                    location_el = await card.query_selector("[data-test='emp-location'], .job-search-key-iii9i9")
                    salary_el = await card.query_selector("[data-test='detailSalary'], .salary-estimate")

                    job_title = (await title_el.inner_text()).strip() if title_el else ""
                    company = (await company_el.inner_text()).strip() if company_el else ""
                    job_location = (await location_el.inner_text()).strip() if location_el else ""
                    salary = (await salary_el.inner_text()).strip() if salary_el else None

                    href = await title_el.get_attribute("href") if title_el else ""
                    job_url = ("https://www.glassdoor.com" + href) if href and href.startswith("/") else href or ""

                    # Try to get description (requires login for full text)
                    description = ""
                    if title_el:
                        prev_text = ""
                        try:
                            prev_el = await page.query_selector(
                                ".desc, [data-test='description'], .jobDescriptionContent"
                            )
                            if prev_el:
                                prev_text = await prev_el.inner_text()
                        except Exception:
                            pass
                        await card.click()
                        try:
                            await page.wait_for_function(
                                """(prev) => {
                                    const el = document.querySelector(
                                        '.desc, [data-test="description"], .jobDescriptionContent'
                                    );
                                    return el && el.innerText.trim() !== prev.trim() && el.innerText.trim().length > 0;
                                }""",
                                arg=prev_text,
                                timeout=5000,
                            )
                        except Exception:
                            pass
                        desc_el = await page.query_selector(
                            ".desc, [data-test='description'], .jobDescriptionContent"
                        )
                        if desc_el:
                            description = (await desc_el.inner_text()).strip()

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
                    print(f"  [glassdoor] Card error ({type(e).__name__}): {e}")
                    continue
        finally:
            await page.close()

        return jobs
