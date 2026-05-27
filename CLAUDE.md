# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

Job scraper that pulls listings from LinkedIn, Indeed, Glassdoor, Wellfound, and Hiring Cafe, then scores each job against Kelly's resume using a two-layer ranking system: rule-based point adjustments (defined below) followed by Claude API semantic scoring. Output is a static HTML dashboard.

## Commands

```bash
# Install
pip install -r requirements.txt
playwright install chromium

# Run full pipeline (scrape → rank → generate dashboard)
python main.py run

# Scrape only
python main.py scrape
python main.py scrape --site linkedin   # single site

# Rank already-scraped jobs
python main.py rank

# Tests
pytest
pytest tests/test_ranker.py            # single file
```

API keys go in `.env` (never commit). See `.env.example`.

## Architecture

Two-layer scoring pipeline:

1. **Rule-based scorer** (`scorer.py`) — applies point adjustments from the criteria below to each raw job dict. Fast, no API call.
2. **Claude ranker** (`ranker.py`) — sends job description + resume to Claude API for a 0–100 semantic fit score. Final score = claude_score + rule_adjustments.

```
scrapers/
  base.py          # Abstract Playwright scraper (login handling, rate limiting)
  linkedin.py
  indeed.py
  glassdoor.py
  wellfound.py
  hiringcafe.py
scorer.py          # Rule-based point adjustments
ranker.py          # Claude API integration
dashboard.py       # Renders output/dashboard.html
main.py            # CLI entry point (run / scrape / rank subcommands)
config.py          # Loads search prefs and .env
output/            # Generated HTML (git-ignored)
```

Each scraper returns a list of dicts with at minimum: `title`, `company`, `location`, `url`, `description`, `remote` (bool), `salary` (str|None).

## Resume — Kelly Zamboni

**Role:** Instructional Design & Organizational Change Management Consultant, 18+ years

**Core skills:** ADDIE methodology, ILT/VILT, eLearning, Train-the-Trainer, enterprise system training, go-live support, OCM planning, stakeholder engagement, impact analysis, organizational readiness assessment

**Tools:** Articulate 360, Adobe Creative Suite, Camtasia, Snagit, Saba Cloud LMS, Salesforce, Microsoft Teams

**Certifications:** Change Management Practitioner, SAFe 6 Scrum Master, CSM, Certified Product Manager L1

**Key experience:**
- Federal Reserve Bank of Kansas City (2020–present): Built learning paths (1,300+ views), overhauled mandatory training for 3,000 employees, led skills gap analysis for 80 staff, built COMPASS eLearning from scratch, ran Salesforce VILT for 60+ staff
- Terracon Consultants (2016–2020): LMS dashboards for 5,000+ employees (cut manual reporting 40%), safety compliance eLearning, Articulate 360 production
- Shook Hardy & Bacon (2008–2016): Billing system rollout training for 400+ users (90%+ completion, 25% fewer post-launch help desk tickets), role-specific ID for attorneys/paralegals/support staff, reduced new hire onboarding time 20%
- GMAC Financial (2006–2008): Trained 200+ agents, cut ramp-to-productivity 30%, 95% post-training pass rate

**Education:** MS Human Resource Management (Lindenwood), BSBA Management & Organizational Behavior (UMSL)

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
| Enterprise software implementation (Salesforce, LMS, ERP) | +10 |
| OCM or change management explicitly required | +10 |
| Senior, lead, or consultant-level title | +8 |
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

- **LinkedIn**: Blocks headless browsers aggressively. Requires a logged-in session (store cookies in `.env` or a session file). Expect frequent CAPTCHAs — build in retry logic and a fallback to skip rather than crash.
- **Indeed**: Has bot detection; use realistic `user_agent` and randomized delays (2–5s between requests).
- **Glassdoor**: Requires login for full job descriptions. Scrape the preview text if unauthenticated.
- **Wellfound** (formerly AngelList): Generally accessible without login; startup-heavy, good for remote roles.
- **Hiring Cafe**: Smaller, low bot protection, straightforward to scrape.

Rate-limit all scrapers: minimum 2s delay between page loads, randomized. Store raw results to `output/raw_<site>_<date>.json` before scoring so reruns don't re-scrape.
