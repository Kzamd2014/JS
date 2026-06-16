# CONTEXT.md

Domain glossary for the job scraper project. Implementation details belong in CLAUDE.md, not here.

---

## Scraper

A component that retrieves raw job listings from a single external source and returns a list of **Job** dicts. Two kinds exist:

- **API Scraper** — fetches from a REST endpoint (no browser). Currently: Adzuna.
- **Playwright Scraper** — drives a headless Chromium browser. Currently: HiringCafe.

Both kinds extend `BaseScraper` and produce the same **Job** shape.

---

## Description Enrichment

An extra pass run by the Adzuna scraper after the initial API fetch. The Adzuna API returns short snippets; enrichment follows each job's redirect URL, fetches the full page, and extracts plain text to replace the snippet. Falls back to the original snippet on any fetch error. Enrichment runs concurrently (capped at 8 in-flight requests) and is transparent to the rest of the pipeline — the **Job** shape is identical either way.

---

## Job

A raw listing as returned by a Scraper. Required fields: `title`, `company`, `location`, `url`, `description`, `remote` (bool), `salary` (str|None), `site` (source name).

A Job becomes a **Scored Job** after passing through the Rule Scorer, and a **Ranked Job** after the Claude Ranker adds `claude_score` and `final_score`.

---

## Rule Score

An integer (can be negative) produced by `scorer.py` from keyword signals in a Job's title and description. Signals include authoring tools, OCM keywords, seniority, remote status, salary, and whether the title matches a **Primary Title**. Added to `claude_score` to produce `final_score`.

---

## Primary Title

A job title that directly targets Kelly's core roles (Instructional Designer, Learning Consultant, OCM Consultant, etc.), as distinct from secondary titles (Technical Trainer, LMS Administrator, etc.). Jobs whose title matches a Primary Title receive a rule score bonus. The full list lives in `config.py`.

---

## Claude Score

An integer 0–100 produced by the Claude API representing semantic fit between a Job and Kelly's resume. The system prompt (which embeds the resume) is hashed; if the hash changes between runs, the **Score Cache** is invalidated automatically.

---

## Final Score

`claude_score + rule_score`, clamped to [0, 100]. Used to sort the dashboard. Displayed alongside its components (`claude_score` and `rule_score`) so the source of a high or low score is visible at a glance.

---

## Score Cache

A persistent JSON file (`output/scores_cache.json`) keyed by `"title||company"` that stores prior Claude scores to avoid re-calling the API for jobs seen in previous runs. Invalidated automatically when the system prompt (resume + instructions) changes, detected via a stored SHA-256 hash prefix.
