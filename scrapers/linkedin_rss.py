"""
LinkedIn job scraper via rss.app RSS feeds.
No Playwright, no auth — pure HTTP. Feed URLs are set in LINKEDIN_RSS_FEEDS
in .env (comma-separated). Add more feeds to broaden coverage.
"""
from __future__ import annotations

import asyncio
import html.parser
import re
import urllib.request

import defusedxml.ElementTree as ET

import config
from scrapers.base import dedupe_jobs, _infer_remote


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


def _make_job(**kwargs) -> dict:
    return {
        "site": "linkedin_rss",
        "title": "",
        "company": "",
        "location": "",
        "url": "",
        "description": "",
        "remote": False,
        "salary": None,
        **kwargs,
    }


class LinkedInRssScraper:
    site_name = "linkedin_rss"

    async def scrape(self, titles: list[str], locations: list[str]) -> list[dict]:
        feed_urls = config.LINKEDIN_RSS_FEEDS
        if not feed_urls:
            print("  [linkedin_rss] No LINKEDIN_RSS_FEEDS configured — skipping")
            return []

        tasks = [asyncio.to_thread(self._fetch_feed, url) for url in feed_urls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_jobs: list[dict] = []
        for url, result in zip(feed_urls, results):
            if isinstance(result, Exception):
                print(f"  [linkedin_rss] Failed to fetch {url}: {type(result).__name__}: {result}")
            else:
                print(f"  [linkedin_rss] {url} → {len(result)} jobs")
                all_jobs.extend(result)

        return dedupe_jobs(all_jobs)

    def _fetch_feed(self, url: str) -> list[dict]:
        if not url.startswith("https://"):
            raise ValueError(f"Refusing non-HTTPS feed URL: {url!r}")

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
            remote = _infer_remote(f"{location} {raw_title}", False)

            jobs.append(_make_job(
                title=title,
                company=company,
                location=location,
                url=link,
                description=description[:config.DESCRIPTION_MAX_CHARS],
                remote=remote,
                salary=salary,
            ))

        return jobs
