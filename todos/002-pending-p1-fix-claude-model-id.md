---
name: 002-pending-p1-fix-claude-model-id
description: Invalid Claude model ID causes all semantic ranking calls to silently fail and default to score 50
metadata:
  type: project
  status: pending
  priority: p1
  tags: [code-review, bug, ranking]
---

## Problem Statement
ranker.py:39 specifies model="claude-sonnet-4-6" which is not a valid Anthropic model identifier. Every Claude API call raises a NotFoundError that is caught by the broad except block at line 65, which silently assigns claude_score=50 and continues. The entire semantic ranking layer is effectively dead — all jobs receive an identical flat score of 50 plus rule adjustments, making the ranked output meaningless.

## Findings
- /home/kzamd22/job/ranker.py:39 — `model="claude-sonnet-4-6"` (invalid model ID)
- /home/kzamd22/job/ranker.py:65 — broad except swallows NotFoundError and sets claude_score=50
- Observable symptom: all jobs in output have claude_score exactly 50 with no variance; no error is logged to indicate failure

## Proposed Solutions
### Option A
Change model ID to `"claude-sonnet-4-5"` (a valid alias). Add a fail-fast check: make a single test API call at ranker startup and raise immediately (do not catch) if it returns a non-2xx error, so misconfiguration is visible before processing 100 jobs.

- Pros: Fast model, low cost, surface errors immediately rather than silently degrading
- Cons: claude-sonnet-4-5 may be deprecated in future; needs periodic review
- Effort: Small
- Risk: Low

### Option B
Change model ID to `"claude-opus-4-7"` for higher-quality semantic scoring at the cost of higher per-call latency and price. Same fail-fast approach applies.

- Pros: Better semantic reasoning for nuanced job-fit scoring
- Cons: Higher cost and slower; overkill for binary fit scoring
- Effort: Small
- Risk: Low

## Acceptance Criteria
- [ ] First API call in a ranking run succeeds without error
- [ ] Jobs receive varied claude_score values across the 0–100 range (not uniformly 50)
- [ ] Any API error surfaces immediately with a clear message rather than being swallowed silently
- [ ] Model ID matches a currently published Anthropic model identifier

## Work Log
- 2026-06-01: Identified in code review
