"""
LinkedIn job scraper via rss.app RSS feeds.
No Playwright, no auth — pure HTTP. Feed URLs are set in LINKEDIN_RSS_FEEDS
in .env (comma-separated). Add more feeds to broaden coverage.
"""
import html.parser
import re
import traceback
import urllib.request
import xml.etree.ElementTree as ET

import config
from scrapers.base import BaseScraper, dedupe_jobs, _infer_remote
from playwright.async_api import BrowserContext


class _TextExtractor(html.parser.HTMLParser):
    _SKIP = frozenset({"script", "style", "head", "noscript"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._depth += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._depth:
            self._depth -= 1

    def handle_data(self, data):
        if not self._depth:
            stripped = data.strip()
            if stripped:
                self._parts.append(stripped)

    def get_text(self) -> str:
        return " ".join(self._parts)


def _strip_html(raw: str) -> str:
    parser = _TextExtractor()
    try:
        parser.feed(raw)
    except Exception:
        return raw
    return parser.get_text()


def _parse_title_line(raw: str) -> tuple[str, str, str]:
    """Parse 'Company hiring Job Title in Location' → (title, company, location)."""
    m = re.match(r"^(.+?)\s+hiring\s+(.+?)\s+in\s+(.+)$", raw, re.IGNORECASE)
    if m:
        return m.group(2).strip(), m.group(1).strip(), m.group(3).strip()
    return raw.strip(), "", ""


def _extract_salary(text: str) -> str | None:
    m = re.search(r"\$[\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?)?", text)
    return m.group(0).replace(".00", "") if m else None


_FETCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}


class LinkedInRssScraper(BaseScraper):
    site_name = "linkedin_rss"

    async def scrape(self, titles: list[str], locations: list[str]) -> list[dict]:
        feed_urls = getattr(config, "LINKEDIN_RSS_FEEDS", [])
        if not feed_urls:
            print("  [linkedin_rss] No LINKEDIN_RSS_FEEDS configured — skipping")
            return []

        all_jobs: list[dict] = []
        for url in feed_urls:
            try:
                jobs = self._fetch_feed(url)
                print(f"  [linkedin_rss] {url} → {len(jobs)} jobs")
                all_jobs.extend(jobs)
            except Exception as e:
                print(
                    f"  [linkedin_rss] Failed to fetch {url}: "
                    f"{type(e).__name__}: {e}\n{traceback.format_exc()}"
                )

        return dedupe_jobs(all_jobs)

    def _fetch_feed(self, url: str) -> list[dict]:
        req = urllib.request.Request(url, headers=_FETCH_HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()

        root = ET.fromstring(raw)
        channel = root.find("channel")
        if channel is None:
            return []

        jobs = []
        for item in channel.findall("item"):
            raw_title = (item.findtext("title") or "").strip()
            link = (item.findtext("link") or "").strip()
            raw_desc = (item.findtext("description") or "").strip()

            title, company, location = _parse_title_line(raw_title)
            if not title:
                continue

            description = _strip_html(raw_desc)
            salary = _extract_salary(description)
            remote = _infer_remote(location, False) or _infer_remote(raw_title, False)

            jobs.append(self._job(
                title=title,
                company=company,
                location=location,
                url=link,
                description=description[:5000],
                remote=remote,
                salary=salary,
            ))

        return jobs

    async def _search(self, context: BrowserContext, title: str, location: str) -> list[dict]:
        return []
