---
name: 008-pending-p2-fix-broad-exception-handlers
description: Replace broad except-Exception handlers that silently swallow auth failures, API errors, and programmer mistakes
metadata:
  type: project
  status: pending
  priority: p2
  tags: [code-review, reliability, error-handling]
---

## Problem Statement
Broad `except Exception` handlers throughout the codebase swallow programmer errors, authentication failures, and API errors silently. A broken API key causes all jobs to silently rank at 50 with no user-visible error. Scraper failures discard full tracebacks, making debugging painful.

## Findings
- scrapers/linkedin.py:59,86,92,105 — `except Exception: pass` blocks that silently discard errors
- ranker.py:65 — catches all API errors and assigns `claude_score=50`, masking a broken API key
- main.py:45-47 — catches all scraper errors with a one-line print, discarding the full traceback
- scrapers/base.py:50-51 — broad catch in base scraper class

## Proposed Solutions
### Option A
Replace `except Exception: pass` in linkedin.py with `logger.warning(...)` calls that include the exception message. In ranker.py, distinguish `anthropic.AuthenticationError` (halt pipeline with a clear message) from `anthropic.RateLimitError` (retry with exponential backoff) from other errors (log and assign a sentinel score of -1 so they sort to the bottom). In main.py:45-47, log the full traceback with `traceback.format_exc()`. Effort: Small

### Option B
Add a `--debug` flag to main.py that converts all broad catches to re-raises, giving developers a fast path to unmasked exceptions without changing production behavior. Effort: Small (complementary, not a substitute for Option A)

## Acceptance Criteria
- [ ] Authentication failures (`anthropic.AuthenticationError`) halt the pipeline immediately with a clear, user-readable message
- [ ] Scraper errors log the full traceback (not just the exception message)
- [ ] API errors other than auth/rate-limit log a warning and assign a sentinel score (`-1`), not the neutral `50`
- [ ] No `except Exception: pass` blocks remain in scrapers/linkedin.py

## Work Log
- 2026-06-01: Identified in code review
