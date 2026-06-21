---
name: 012-pending-p3-ci-and-ops-cleanup
description: CI timeout too long for current pipeline; .env not cleaned up after use; feed URL scheme not validated before fetch
metadata:
  type: project
  status: complete
  priority: p3
  tags: [code-review, ci, security, ops]
---

## Problem Statement
Three small operational hardening items that don't affect correctness but improve safety and CI hygiene.

## Findings

### 1. daily-scrape.yml:10 — timeout-minutes: 60 (HiringCafe-era setting)
HiringCafe took ~40s per query × many title/location combinations = long runs. The LinkedIn RSS scraper completes in under 5 minutes. A 60-minute timeout means a hung run burns a full Actions hour slot before failing. Reduce to 15 minutes.

### 2. daily-scrape.yml — .env not deleted after use
Secrets are written to `.env` and `data/resume.txt` during the workflow and never explicitly removed. GitHub-hosted runners are ephemeral (destroyed after each job), so there is no cross-run exposure. However, if any step later in the workflow (including a compromised action) reads the working directory, `.env` is accessible as plaintext. Defense-in-depth: add a cleanup step:
```yaml
- name: Remove secrets from disk
  if: always()
  run: rm -f .env data/resume.txt
```

### 3. linkedin_rss.py:99 — no scheme guard before urlopen
`_fetch_feed` fetches whatever URL is in `LINKEDIN_RSS_FEEDS` without validating the scheme. A `file://` or `ftp://` URL in the env var would be followed by `urllib`. The value comes from a controlled GitHub secret, so exploitability is negligible. Defensive guard:
```python
if not url.startswith(("https://", "http://")):
    raise ValueError(f"Refusing non-HTTP feed URL: {url!r}")
```

## Proposed Solutions
All three are independent, each is 1-3 lines.

## Acceptance Criteria
- [ ] `daily-scrape.yml` `timeout-minutes` set to 15
- [ ] Workflow has a cleanup step removing `.env` and `data/resume.txt` with `if: always()`
- [ ] `_fetch_feed` raises `ValueError` for non-HTTP URLs

## Work Log
- 2026-06-20: Identified by security and simplicity review agents
