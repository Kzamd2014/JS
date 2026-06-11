"""
Hiring Cafe scraper. Low bot protection, straightforward to scrape.
Job data lives on individual detail pages (/job/{id}), not the search results listing.
Search uses a JSON searchState URL parameter.
"""
import asyncio
import json
import re
import urllib.parse
from playwright.async_api import BrowserContext
from playwright._impl._errors import TargetClosedError
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, _infer_remote


def _posted_within_days(description: str, max_days: int = 4) -> bool:
    """Return False if the description contains a 'Posted X ago' marker older than max_days.
    4 days covers Mon runs that need to see Fri postings."""
    m = re.search(r'Posted\s+(\d+)\s*(d|w|mo)\s+ago', description, re.IGNORECASE)
    if not m:
        return True  # Can't determine age — include by default
    n, unit = int(m.group(1)), m.group(2).lower()
    days = n if unit == 'd' else n * 7 if unit == 'w' else n * 30
    return days <= max_days

_EXTRACT_JOB_JS = """() => {
    const h2 = document.querySelector('h2');
    const title = h2 ? h2.textContent.trim() : '';

    const companySpan = h2 && h2.parentElement
        ? h2.parentElement.querySelector('span[class*="text-xl"]')
        : null;
    const company = companySpan
        ? companySpan.textContent.replace(/^@\\s*/, '').trim()
        : '';

    // Location: first span sibling of a pin-icon SVG (no child links)
    let location = '';
    for (const div of document.querySelectorAll('div')) {
        const svg = div.querySelector('svg');
        const span = div.querySelector('span');
        if (svg && span && !div.querySelector('a') && span.textContent.includes(',')) {
            location = span.textContent.trim();
            break;
        }
    }

    // Work-type badges (Onsite, Remote, Hybrid, Full Time, etc.)
    const badges = Array.from(
        document.querySelectorAll('span[class*="rounded"][class*="border"]')
    ).map(s => s.textContent.trim());
    const remote = badges.some(b => /remote|hybrid/i.test(b));

    // Description: text after the "Job Description" section header
    const body = document.body ? document.body.innerText : '';
    const marker = 'Job Description\\n';
    const idx = body.indexOf(marker);
    const description = idx >= 0 ? body.slice(idx + marker.length).trim() : '';

    return { title, company, location, remote, description };
}"""


class HiringCafeScraper(BaseScraper):
    site_name = "hiringcafe"

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        search_state: dict = {"searchQuery": title}
        if is_remote:
            search_state["remote"] = True
        else:
            search_state["location"] = location

        url = "https://hiring.cafe/?searchState=" + urllib.parse.quote(json.dumps(search_state))
        page = await context.new_page()
        jobs = []
        try:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3)  # let JS render job cards
            except TargetClosedError:
                return []
            await self._delay()

            # Collect job links from the search results page — dedup first, then cap
            links = await page.query_selector_all("a[href^='/job/']")
            hrefs = []
            seen = set()
            for link in links:
                href = await link.get_attribute("href")
                if href and href not in seen:
                    seen.add(href)
                    hrefs.append("https://hiring.cafe" + href)
                    if len(hrefs) >= MAX_CARDS_PER_QUERY:
                        break

            if not hrefs:
                return []

            # Fetch each detail page
            detail_page = await context.new_page()
            try:
                for job_url in hrefs:
                    try:
                        await detail_page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
                        await asyncio.sleep(2)
                        await self._delay()

                        data = await detail_page.evaluate(_EXTRACT_JOB_JS)
                        job_title = data.get("title", "")
                        company = data.get("company", "")
                        job_location = data.get("location", "") or location
                        remote = data.get("remote", False) or _infer_remote(job_location, is_remote)
                        description = data.get("description", "")[:5000]

                        if job_title and company and _posted_within_days(description):
                            jobs.append(self._job(
                                title=job_title,
                                company=company,
                                location=job_location,
                                url=job_url,
                                description=description,
                                remote=remote,
                            ))
                    except Exception as e:
                        print(f"  [hiringcafe] Detail page error ({type(e).__name__}): {e}")
                        continue
            finally:
                await detail_page.close()
        finally:
            await page.close()

        return jobs
