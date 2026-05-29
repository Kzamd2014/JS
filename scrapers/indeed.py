import urllib.parse
from playwright.async_api import BrowserContext
from scrapers.base import BaseScraper

# Remote filter token used by Indeed's URL
_REMOTE_TOKEN = "032b3046-06a3-4876-8dfd-474eb5e7ed11"

_CHALLENGE_KEYWORDS = ("robot", "captcha", "human verification", "access denied", "blocked")


class IndeedScraper(BaseScraper):
    site_name = "indeed"

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        params: dict = {"q": title, "radius": "25"}
        if is_remote:
            params["remotejob"] = _REMOTE_TOKEN
        else:
            params["l"] = location

        url = "https://www.indeed.com/jobs?" + urllib.parse.urlencode(params)
        page = await context.new_page()
        jobs = []
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await self._delay()

            # Detect bot challenge pages before iterating
            page_title = (await page.title()).lower()
            if any(kw in page_title for kw in _CHALLENGE_KEYWORDS):
                print(f"  [indeed] Bot challenge detected for '{title}' — skipping")
                return []

            cards = await page.query_selector_all("[data-testid='slider_item'], .job_seen_beacon")
            for card in cards[:20]:
                try:
                    title_el = await card.query_selector("h2.jobTitle a, [data-testid='jobTitle']")
                    company_el = await card.query_selector("[data-testid='company-name']")
                    location_el = await card.query_selector("[data-testid='text-location']")
                    salary_el = await card.query_selector("[data-testid='attribute_snippet_testid'], .salary-snippet-container")

                    job_title = (await title_el.inner_text()).strip() if title_el else ""
                    company = (await company_el.inner_text()).strip() if company_el else ""
                    job_location = (await location_el.inner_text()).strip() if location_el else ""
                    salary = (await salary_el.inner_text()).strip() if salary_el else None

                    href = await title_el.get_attribute("href") if title_el else ""
                    job_url = "https://www.indeed.com" + href if href and href.startswith("/") else href or ""

                    # Load full description, wait for panel to update to this job's content
                    description = ""
                    if title_el:
                        prev_text = ""
                        try:
                            prev_el = await page.query_selector(
                                "#jobDescriptionText, .jobsearch-jobDescriptionText"
                            )
                            if prev_el:
                                prev_text = await prev_el.inner_text()
                        except Exception:
                            pass

                        await title_el.click()
                        try:
                            await page.wait_for_function(
                                """(prev) => {
                                    const el = document.querySelector(
                                        '#jobDescriptionText, .jobsearch-jobDescriptionText'
                                    );
                                    return el && el.innerText.trim() !== prev.trim() && el.innerText.trim().length > 0;
                                }""",
                                arg=prev_text,
                                timeout=5000,
                            )
                        except Exception:
                            pass
                        desc_el = await page.query_selector(
                            "#jobDescriptionText, .jobsearch-jobDescriptionText"
                        )
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
                            salary=salary,
                        ))
                except Exception as e:
                    print(f"  [indeed] Card error ({type(e).__name__}): {e}")
                    continue
        finally:
            await page.close()

        return jobs
