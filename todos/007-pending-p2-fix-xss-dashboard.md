---
name: 007-pending-p2-fix-xss-dashboard
description: Fix XSS risk points in the dashboard template and harden autoescape configuration
metadata:
  type: project
  status: pending
  priority: p2
  tags: [code-review, security, xss]
---

## Problem Statement
Scraped job content flows through the dashboard with multiple XSS risk points. (1) `data-title`, `data-company`, `data-site` attributes in the template rely on Jinja2 implicit escaping rather than explicit filters. (2) `claude_rationale` is rendered directly and could contain prompt injection payloads from scraped content. (3) `autoescape=select_autoescape(["html","j2"])` is extension-based — fragile if templates are renamed or a new extension is introduced.

## Findings
- templates/dashboard.html.j2:120-126 — data-* attributes rely on implicit escaping only
- templates/dashboard.html.j2:151-153 — rationale div rendered without sanitization
- dashboard.py:17-19 — `autoescape=select_autoescape(["html","j2"])` is extension-gated, not unconditional
- ranker.py:59,68 — source of `claude_rationale` content that reaches the template

## Proposed Solutions
### Option A
Change to `autoescape=True` in dashboard.py; add explicit `| e` filter on all `data-*` attributes in the template; cap and sanitize `claude_rationale` to 300 printable characters in ranker.py before storage; add a CSP meta tag to the dashboard `<head>`: `<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';">`. Effort: Small

### Option B
Add `autoescape=True` only — minimum viable fix that closes the extension-gating hole without touching the template or ranker. Effort: Small (incomplete)

## Acceptance Criteria
- [ ] `autoescape=True` is set unconditionally in dashboard.py (not extension-based)
- [ ] CSP meta tag is present in the dashboard `<head>`
- [ ] `claude_rationale` is capped at 300 printable characters before being stored
- [ ] All `data-*` attributes in the template use explicit `| e` filters

## Work Log
- 2026-06-01: Identified in code review
