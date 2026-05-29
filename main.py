import argparse
import asyncio
import json
import os
import re
from datetime import datetime
from pathlib import Path

from config import ALL_TITLES, OUTPUT_DIR, LOCATIONS
from scrapers.linkedin import LinkedInScraper
from scrapers.indeed import IndeedScraper
from scrapers.glassdoor import GlassdoorScraper
from scrapers.wellfound import WellfoundScraper
from scrapers.hiringcafe import HiringCafeScraper
from scrapers.base import dedupe_jobs
from scorer import score as rule_score
from ranker import rank_jobs
from dashboard import generate

def _atomic_write(path: Path, content: str) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


SCRAPERS = {
    "linkedin": LinkedInScraper,
    "indeed": IndeedScraper,
    "glassdoor": GlassdoorScraper,
    "wellfound": WellfoundScraper,
    "hiringcafe": HiringCafeScraper,
}


async def _run_scrapers(site: str | None) -> list[dict]:
    targets = {k: v for k, v in SCRAPERS.items() if site is None or k == site}
    all_jobs: list[dict] = []
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    for name, cls in targets.items():
        print(f"\nScraping {name}...")
        try:
            scraper = cls()
            jobs = await scraper.scrape(ALL_TITLES, LOCATIONS)
        except Exception as e:
            print(f"  [{name}] Scraper failed: {e}")
            jobs = []

        raw_path = OUTPUT_DIR / f"raw_{name}_{ts}.json"
        _atomic_write(raw_path, json.dumps(jobs, indent=2))
        print(f"  Saved {len(jobs)} jobs → {raw_path}")
        all_jobs.extend(jobs)

    return dedupe_jobs(all_jobs)


def _load_latest_raw() -> list[dict]:
    raw_files = sorted(OUTPUT_DIR.glob("raw_*.json"))
    if not raw_files:
        raise FileNotFoundError("No raw scrape files in output/. Run 'python main.py scrape' first.")

    # Extract YYYYMMDD_HHMMSS timestamp from filename using regex
    ts_pattern = re.compile(r"_(\d{8}_\d{6})$")
    timestamps = sorted({
        m.group(1) for f in raw_files if (m := ts_pattern.search(f.stem))
    })
    latest_ts = timestamps[-1]
    latest_files = [f for f in raw_files if ts_pattern.search(f.stem) and ts_pattern.search(f.stem).group(1) == latest_ts]

    all_jobs: list[dict] = []
    for f in latest_files:
        try:
            all_jobs.extend(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            print(f"  Warning: skipping corrupt file {f.name}: {e}")
    return dedupe_jobs(all_jobs)


def cmd_scrape(args):
    jobs = asyncio.run(_run_scrapers(args.site))
    print(f"\nTotal: {len(jobs)} unique jobs scraped.")


def cmd_rank(args):
    print("Loading scraped jobs...")
    jobs = _load_latest_raw()
    print(f"Loaded {len(jobs)} jobs. Applying rule scorer...")
    jobs = [rule_score(j) for j in jobs]
    print(f"Calling Claude API for semantic scoring ({len(jobs)} jobs)...")
    ranked = rank_jobs(jobs)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ranked_path = OUTPUT_DIR / f"ranked_{ts}.json"
    _atomic_write(ranked_path, json.dumps(ranked, indent=2))
    print(f"Saved ranked results → {ranked_path}")
    generate(ranked, OUTPUT_DIR / "dashboard.html")


def cmd_run(args):
    jobs = asyncio.run(_run_scrapers(None))
    print(f"\n{len(jobs)} unique jobs scraped. Scoring...")
    jobs = [rule_score(j) for j in jobs]
    print(f"Calling Claude API ({len(jobs)} jobs)...")
    ranked = rank_jobs(jobs)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    _atomic_write(OUTPUT_DIR / f"ranked_{ts}.json", json.dumps(ranked, indent=2))
    generate(ranked, OUTPUT_DIR / "dashboard.html")
    print(f"\nDone. Open output/dashboard.html in your browser.")


def main():
    parser = argparse.ArgumentParser(description="Job scraper and ranker")
    sub = parser.add_subparsers(dest="command", required=True)

    p_scrape = sub.add_parser("scrape", help="Scrape job listings and save raw JSON")
    p_scrape.add_argument("--site", choices=list(SCRAPERS.keys()), help="Scrape one site only")
    p_scrape.set_defaults(func=cmd_scrape)

    p_rank = sub.add_parser("rank", help="Score and rank the most recent scraped jobs")
    p_rank.set_defaults(func=cmd_rank)

    p_run = sub.add_parser("run", help="Full pipeline: scrape → rank → dashboard")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
