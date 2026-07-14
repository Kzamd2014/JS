# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Job scraper that pulls listings from Adzuna (REST API) and Hiring Cafe (Playwright), then scores each job against Kelly's resume using a two-layer ranking system: rule-based point adjustments (defined below) followed by Claude API semantic scoring. Output is a static HTML dashboard.

## Commands

```bash
# Install
pip install -r requirements.txt
# Only if re-enabling the browser scrapers (hiringcafe/adzuna/etc.):
pip install "playwright>=1.45" && playwright install chromium

# Run full pipeline (scrape → rank → generate dashboard)
python main.py run

# Scrape only
python main.py scrape
python main.py scrape --site adzuna     # single site

# Rank already-scraped jobs
python main.py rank

# Tests
pytest
pytest tests/test_ranker.py            # single file
```

API keys go in `.env` (never commit). See `.env.example`.

## Delivery

Two runners execute the pipeline independently:

| Runner | Schedule | Deploys to Pages | Emails |
|---|---|---|---|
| `run_daily.sh` via system-level `job-scraper.timer` | Daily 7am (incl. weekends) | No | Failure only |
| GitHub Actions (`daily-scrape.yml`) | Weekdays 7am CT | Yes | No |

The local timer is the system-level unit (`/etc/systemd/system/job-scraper.timer`).
Concurrent runs are serialized by a flock on `output/.job-scraper.lock` — the loser
logs "skipping" and exits 0.

Local logs: `output/scrape_YYYY-MM-DD.log` (written by `run_daily.sh`, not CI).

## Architecture

Two-layer scoring pipeline:

1. **Rule-based scorer** (`scorer.py`) — applies point adjustments from the criteria below to each raw job dict. Fast, no API call.
2. **Claude ranker** (`ranker.py`) — sends job description + resume to Claude API for a 0–100 semantic fit score. Final score = claude_score + rule_adjustments.

```
scrapers/
  base.py          # BaseScraper (Playwright context, rate limiting, retry, dedupe)
  adzuna.py        # REST API scraper — no browser, pure HTTP (free tier: 1,000 calls/month)
  hiringcafe.py    # Playwright scraper — low bot protection, straightforward
scorer.py          # Rule-based point adjustments
ranker.py          # Claude API integration
dashboard.py       # Renders output/index.html
main.py            # CLI entry point (run / scrape / rank subcommands)
config.py          # Loads search prefs and .env
output/            # Generated HTML and raw JSON (git-ignored)
```

Each scraper returns a list of dicts with at minimum: `title`, `company`, `location`, `url`, `description`, `remote` (bool), `salary` (str|None).

## Resume — Kelly Zamboni

**Two copies exist — keep them in sync:**

| Copy | Used by |
|---|---|
| `data/resume.txt` | Local runs (`python main.py run`) |
| GitHub secret `RESUME_TXT` | CI (daily workflow writes it to `data/resume.txt` at runtime) |

**To update the resume:** edit `data/resume.txt`, then push it to the secret:

```bash
gh secret set RESUME_TXT < data/resume.txt
```

The Claude ranker reads `data/resume.txt` at runtime. Editing only the local file without updating the secret means CI silently uses the old resume. The prompt-hash cache (`output/scores_cache.json`) will auto-invalidate on the next run after either copy changes.

**Summary:** Instructional Design & OCM Consultant, 18+ years. Core background in ADDIE, ILT/VILT, eLearning, Train-the-Trainer, enterprise system rollouts, and go-live support. Key tools: Articulate 360, Adobe Creative Suite, Camtasia, Snagit, Saba Cloud LMS. Based in Kansas City, MO; open to remote.

## Job search preferences

**Location:** Kansas City metro or remote (no relocation)

### Primary titles (weight higher in ranking)
Instructional Designer, Senior Instructional Designer, Learning Consultant, Learning & Development Consultant, OCM Consultant, Change Management Specialist, Learning Experience Designer, eLearning Developer

### Secondary titles (include, lower weight)
LMS Administrator/Analyst, Learning Technology Specialist, IT Training Specialist, Talent Development Consultant, Technical Trainer, HR Technology Consultant, Performance Consultant

## Ranking criteria

### Positive signals (add to score)
| Signal | Points |
|---|---|
| Mentions Articulate 360, Adobe Creative Suite, Camtasia, or Snagit | +10 |
| Enterprise software implementation (LMS, ERP) | +10 |
| OCM or change management explicitly required | +10 |
| Senior, lead, or consultant-level title | +8 |
| Primary title match (Instructional Designer, Learning Consultant, OCM Consultant, etc.) | +5 |
| Remote or hybrid offered | +5 |
| Salary listed ≥ $80k | +5 |
| Train-the-Trainer or go-live support mentioned | +5 |
| ADDIE or instructional design methodology mentioned | +5 |

### Negative signals (subtract from score)
| Signal | Points |
|---|---|
| Pure HR generalist, no L&D focus | −20 |
| Travel requirement > 25% | −20 |
| Salary listed < $80k | −15 |
| Entry-level or junior title | −15 |
| No mention of eLearning or ID tools | −10 |
| Fully onsite only | −5 |

## Scraper constraints

- **Adzuna**: Free tier — 1,000 API calls/month. Requires `ADZUNA_APP_ID` and `ADZUNA_APP_KEY` in `.env`. Aggregates from many US job boards; descriptions are short snippets (not full text). No Playwright needed.
- **Hiring Cafe**: Low bot protection, straightforward to scrape with Playwright. No login required.

Rate-limit all scrapers: minimum 2s delay between requests, randomized. Store raw results to `output/raw_<site>_<date>.json` before scoring so reruns don't re-scrape.
