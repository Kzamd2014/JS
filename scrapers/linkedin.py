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
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, _infer_remote


class LinkedInScraper(BaseScraper):
    site_name = "linkedin"

    async def _make_context(self, browser):
        return await self._make_context_with_cookies(browser, LINKEDIN_COOKIES)

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        if not LINKEDIN_COOKIES:
            print("  [linkedin] No cookies — skipping (set LINKEDIN_COOKIES in .env)")
            return []

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

            # Check if redirected to login or authwall
            if "login" in page.url or "authwall" in page.url:
                print(f"  [linkedin] Not authenticated — set LINKEDIN_COOKIES in .env")
                return []

            # Check for blocking modal (unauthenticated sign-up prompt)
            modal = await page.query_selector(".modal__overlay--visible")
            if modal:
                print(f"  [linkedin] Sign-up modal detected — cookies may be expired")
                return []

            try:
                await page.wait_for_selector(".jobs-search-results__list-item, .base-card", timeout=10000)
            except Exception:
                return []  # No results for this query

            cards = await page.query_selector_all(".jobs-search-results__list-item, .base-card")
            for card in cards[:MAX_CARDS_PER_QUERY]:
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

                    # Click card to load description in side panel, wait for new content
                    description = ""
                    if link_el:
                        prev_text = ""
                        try:
                            prev_el = await page.query_selector(
                                ".jobs-description__content, .show-more-less-html__markup"
                            )
                            if prev_el:
                                prev_text = await prev_el.inner_text()
                        except Exception:
                            pass

                        # Use JS click to bypass any pointer-events blocking from overlays
                        try:
                            await card.evaluate("el => el.click()")
                        except Exception:
                            await card.click()
                        try:
                            await page.wait_for_function(
                                """(prev) => {
                                    const el = document.querySelector(
                                        '.jobs-description__content, .show-more-less-html__markup'
                                    );
                                    return el && el.innerText.trim() !== prev.trim() && el.innerText.trim().length > 0;
                                }""",
                                arg=prev_text,
                                timeout=5000,
                            )
                        except Exception:
                            pass
                        desc_el = await page.query_selector(
                            ".jobs-description__content, .show-more-less-html__markup"
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
                        ))
                except Exception as e:
                    print(f"  [linkedin] Card error ({type(e).__name__}): {e}")
                    continue
        finally:
            await page.close()

        return jobs
