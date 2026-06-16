# Job Scraper

Scrapes job listings from Adzuna (REST API) and Hiring Cafe (Playwright), then scores each one against a resume using a two-layer ranking system: rule-based point adjustments followed by Claude API semantic scoring. Output is a filterable, sortable HTML dashboard.

## Requirements

- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com)
- An [Adzuna API key](https://developer.adzuna.com) (free tier: 1,000 calls/month)

## Setup

```bash
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Add your API keys to .env
```

## Usage

```bash
# Full pipeline: scrape → score → generate dashboard
python main.py run

# Scrape only (saves raw JSON to output/)
python main.py scrape
python main.py scrape --site adzuna     # one site at a time

# Score and rank previously scraped results
python main.py rank
```

Open `output/index.html` in a browser when done.

## Configuration

All configuration is in `.env`. Copy `.env.example` to get started.

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Used for semantic job scoring |
| `ADZUNA_APP_ID` | Yes | Adzuna API app ID |
| `ADZUNA_APP_KEY` | Yes | Adzuna API app key |
| `NOTIFY_EMAIL` | No | Gmail address for success/failure notifications |
| `GMAIL_APP_PASSWORD` | No | Gmail app password for sending notifications |

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
- Adzuna's free tier allows 1,000 API calls/month. With 15 title queries × 2 locations = 30 calls per run, a daily schedule stays well within limits.
- Resume lives in `data/resume.txt`. After editing it locally, update the GitHub secret too: `gh secret set RESUME_TXT < data/resume.txt`
