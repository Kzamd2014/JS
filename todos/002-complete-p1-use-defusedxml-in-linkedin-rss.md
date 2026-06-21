---
name: 002-pending-p1-use-defusedxml-in-linkedin-rss
description: linkedin_rss.py uses stdlib ET instead of defusedxml — entity expansion DoS possible from malicious RSS feed
metadata:
  type: project
  status: complete
  priority: p1
  tags: [code-review, security, xml]
---

## Problem Statement
`scrapers/linkedin_rss.py` imports `xml.etree.ElementTree as ET` from the stdlib. `defusedxml` is already declared in `requirements.txt` and is correctly used in `scrapers/indeed.py`. The stdlib expat parser ignores external entity declarations (no classic XXE file exfiltration), but it **is** vulnerable to "billion laughs" XML entity expansion — a single malicious RSS response with deeply nested entity references causes runaway memory consumption that can OOM-kill the CI runner. The fix is already in the dependency list.

## Findings
- `scrapers/linkedin_rss.py:10` — `import xml.etree.ElementTree as ET`
- `scrapers/indeed.py:8` — correctly uses `import defusedxml.ElementTree as ET`
- `requirements.txt` — `defusedxml` is already declared
- Exploitability: low (feed URL comes from a controlled GitHub secret), but severity is high and fix is trivial

## Proposed Solutions
### Option A — One-line import swap (Recommended)
Change line 10 of `scrapers/linkedin_rss.py`:
```python
# Before
import xml.etree.ElementTree as ET
# After
import defusedxml.ElementTree as ET
```
`defusedxml.ElementTree` is a drop-in replacement. No other changes needed.

- Pros: Zero-effort, closes the gap that defusedxml was installed to address, consistent with indeed.py
- Cons: None
- Effort: Small
- Risk: None

### Option B — Validate RSS responses before parsing
Limit raw response size before calling `ET.fromstring` to cap memory usage:
```python
raw = resp.read(max_size)
if len(raw) >= max_size:
    raise ValueError("RSS response too large")
```
- Pros: Defense-in-depth regardless of parser
- Cons: Does not prevent entity expansion within the size limit; Option A is strictly better
- Effort: Small
- Risk: Low

## Acceptance Criteria
- [ ] `scrapers/linkedin_rss.py:10` imports `defusedxml.ElementTree as ET`
- [ ] No other file in `scrapers/` imports `xml.etree.ElementTree` (grep confirms)

## Work Log
- 2026-06-20: Identified by security and performance review agents
