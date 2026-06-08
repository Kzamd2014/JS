"""
Indeed scraper. Uses the Indeed RSS feed instead of Playwright DOM scraping —
the RSS endpoint doesn't trigger bot detection and requires no cookies or JS.
"""
import re
import urllib.parse
import urllib.request
import defusedxml.ElementTree as ET
from playwright.async_api import BrowserContext
from scrapers.base import BaseScraper, MAX_CARDS_PER_QUERY, _infer_remote

_REMOTE_TOKEN = "032b3046-06a3-4876-8dfd-474eb5e7ed11"
_RSS_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; RSS/2.0)"}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def _parse_field(html: str, label: str) -> str:
    m = re.search(rf"<b>{re.escape(label)}:</b>\s*([^<]+)", html, re.IGNORECASE)
    return m.group(1).strip() if m else ""


class IndeedScraper(BaseScraper):
    site_name = "indeed"

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        is_remote = location.lower() == "remote"
        params: dict = {"q": title, "radius": "25", "fromage": "1", "limit": "25"}
        if is_remote:
            params["remotejob"] = _REMOTE_TOKEN
        else:
            params["l"] = location

        url = "https://www.indeed.com/rss?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers=_RSS_HEADERS)
            with urllib.request.urlopen(req, timeout=20) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            print(f"  [indeed] RSS fetch failed: {e}")
            return []

        try:
            root = ET.fromstring(raw)
        except ET.ParseError as e:
            print(f"  [indeed] RSS parse error: {e}")
            return []

        jobs = []
        for item in root.findall(".//item")[:MAX_CARDS_PER_QUERY]:
            try:
                job_title = (item.findtext("title") or "").strip()
                desc_html = item.findtext("description") or ""
                company = _parse_field(desc_html, "Company")
                job_loc = _parse_field(desc_html, "Location") or location
                job_url = (item.findtext("guid") or item.findtext("link") or "").strip()
                description = _strip_html(desc_html)
                remote = _infer_remote(job_loc, is_remote)
                if job_title:
                    jobs.append(self._job(
                        title=job_title,
                        company=company,
                        location=job_loc,
                        url=job_url,
                        description=description,
                        remote=remote,
                    ))
            except Exception as e:
                print(f"  [indeed] Item parse error: {e}")
                continue
        return jobs
