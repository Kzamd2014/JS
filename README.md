# Job Scraper

Scrapes job listings from LinkedIn via RSS feeds (no auth, no browser), then scores each one against a resume using a two-layer ranking system: rule-based point adjustments followed by Claude API semantic scoring. Output is a filterable, sortable HTML dashboard published to GitHub Pages.

## Requirements

- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com)
- LinkedIn RSS feed URLs from [rss.app](https://rss.app) (free tier works)

## Setup

```bash
pip install -r requirements.txt

cp .env.example .env
# Add your API keys and RSS feed URLs to .env
```

## Usage

```bash
# Full pipeline: scrape → score → generate dashboard
python main.py run

# Scrape only (saves raw JSON to output/)
python main.py scrape
python main.py scrape --site linkedin_rss     # one site at a time

# Score and rank previously scraped results
python main.py rank
```

Open `output/index.html` in a browser when done.

## Configuration

All configuration is in `.env`. Copy `.env.example` to get started.

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Used for semantic job scoring |
| `LINKEDIN_RSS_FEEDS` | Yes | Comma-separated rss.app feed URLs for LinkedIn job searches |

## How to get LinkedIn RSS feeds

1. Sign up at [rss.app](https://rss.app)
2. Create a feed for each LinkedIn job search URL you want to monitor
3. Copy the generated RSS URLs into `LINKEDIN_RSS_FEEDS` in `.env`, comma-separated

## Scoring

Each job receives a **final score = Claude semantic score (0–100) + rule-based points**, clamped to [0, 100]. Both components are shown on the dashboard so you can tell apart a high-Claude-fit job from one that scored well on keywords alone.

Rule adjustments are applied automatically based on job title and description content (authoring tools, OCM requirements, enterprise software, primary title match, salary, travel %, seniority, etc.). See `CLAUDE.md` for the full scoring table.

## Tests

```bash
pytest
pytest tests/test_scorer.py   # scorer rules only, no API key needed
```

## Notes

- Raw scraped data is saved to `output/raw_<site>_<date>.json` before scoring. Re-running `python main.py rank` reuses today's scrape without hitting the API again.
- Claude scores are cached in `output/scores_cache.json` by job title + company. The cache auto-invalidates if the resume or scoring prompt changes.
- LinkedIn RSS scraping uses pure HTTP — no Playwright, no login, no session cookies required.
- Resume lives in `data/resume.txt`. After editing it locally, update the GitHub secret too: `gh secret set RESUME_TXT < data/resume.txt`
