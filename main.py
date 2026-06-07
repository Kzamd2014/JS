import argparse
import asyncio
import json
import os
import re
import traceback
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
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    async def _run_one(name: str, cls) -> list[dict]:
        print(f"\nScraping {name}...")
        try:
            scraper = cls()
            jobs = await scraper.scrape(ALL_TITLES, LOCATIONS)
        except Exception as e:
            print(f"  [{name}] Scraper failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
            jobs = []
        raw_path = OUTPUT_DIR / f"raw_{name}_{ts}.json"
        _atomic_write(raw_path, json.dumps(jobs, indent=2))
        print(f"  [{name}] Saved {len(jobs)} jobs → {raw_path}")
        return jobs

    results = await asyncio.gather(*[_run_one(name, cls) for name, cls in targets.items()])
    all_jobs = [job for site_jobs in results for job in site_jobs]
    return dedupe_jobs(all_jobs)


def _load_latest_raw() -> list[dict]:
    raw_files = sorted(OUTPUT_DIR.glob("raw_*.json"))
    if not raw_files:
        raise FileNotFoundError("No raw scrape files in output/. Run 'python main.py scrape' first.")

    # Group by site name, pick the latest file per site
    site_pattern = re.compile(r"^raw_(.+)_(\d{8}_\d{6})$")
    latest_per_site: dict[str, Path] = {}
    for f in raw_files:
        m = site_pattern.match(f.stem)
        if not m:
            continue
        site, ts = m.group(1), m.group(2)
        if site not in latest_per_site or ts > site_pattern.match(latest_per_site[site].stem).group(2):
            latest_per_site[site] = f

    all_jobs: list[dict] = []
    for site, f in sorted(latest_per_site.items()):
        try:
            jobs = json.loads(f.read_text(encoding="utf-8"))
            print(f"  Loaded {len(jobs)} jobs from {f.name}")
            all_jobs.extend(jobs)
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
    asyncio.run(_run_scrapers(None))
    cmd_rank(args)
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
