# Job Scraper

Scrapes job listings from LinkedIn, Indeed, Glassdoor, Wellfound, and Hiring Cafe, then scores each one against a resume using a two-layer ranking system: rule-based point adjustments followed by Claude API semantic scoring. Output is a filterable, sortable HTML dashboard.

## Requirements

- Python 3.12+
- An [Anthropic API key](https://console.anthropic.com)

## Setup

```bash
pip install -r requirements.txt
playwright install chromium

cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

## Usage

```bash
# Full pipeline: scrape all sites → score → generate dashboard
python main.py run

# Scrape only (saves raw JSON to output/)
python main.py scrape
python main.py scrape --site indeed   # one site at a time

# Score and rank previously scraped results
python main.py rank
```

Open `output/dashboard.html` in a browser when done.

## Configuration

All configuration is in `.env`. Copy `.env.example` to get started.

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | Used for semantic job scoring |
| `LINKEDIN_COOKIES` | No | JSON cookie array for authenticated LinkedIn scraping (see below) |
| `GLASSDOOR_COOKIES` | No | JSON cookie array for full Glassdoor job descriptions |

**To export LinkedIn cookies:**
1. Log in to linkedin.com in Chrome
2. Open DevTools → Application → Cookies → `linkedin.com`
3. Export all cookies as a JSON array (e.g. via the [EditThisCookie](https://chrome.google.com/webstore/detail/editthiscookie/fngmhnnpilhplaeedifhccceomclgfbg) extension)
4. Paste the JSON array as the value of `LINKEDIN_COOKIES` in `.env`

Without cookies, LinkedIn returns 0 results. Glassdoor returns preview text only.

## Scoring

Each job receives a **final score = Claude semantic score (0–100) + rule-based points**.

Rule adjustments are applied automatically based on job title and description content (authoring tools, OCM requirements, enterprise software, salary, travel %, seniority, etc.). See `CLAUDE.md` for the full scoring table.

## Tests

```bash
pytest
pytest tests/test_scorer.py   # scorer rules only, no API key needed
```

## Notes

- Raw scraped data is saved to `output/raw_<site>_<timestamp>.json` before scoring, so you can re-run `python main.py rank` without re-scraping.
- LinkedIn and Indeed have bot detection. Expect occasional failures — the scraper retries up to 3 times per query with exponential backoff.
- Scraping LinkedIn/Glassdoor may violate their Terms of Service. Use at your own discretion.
