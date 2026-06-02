---
name: 003-pending-p1-clamp-final-score
description: final_score is unbounded (range -70 to 153), breaking dashboard classification thresholds calibrated for 0-100
metadata:
  type: project
  status: pending
  priority: p1
  tags: [code-review, bug, scoring]
---

## Problem Statement
ranker.py:76 computes final_score = claude_score + rule_score. claude_score is 0–100 but rule_score is unbounded: the maximum positive adjustment is +53 and the maximum negative adjustment is -70. final_score can therefore reach 153 or drop to -70. dashboard.py:12-14 classifies scores using thresholds (>=80 → "high", >=60 → "mid") that were calibrated assuming a 0–100 range, causing systematic misclassification for any job with significant rule adjustments.

## Findings
- /home/kzamd22/job/ranker.py:76 — `final_score = claude_score + rule_score` (no clamping)
- /home/kzamd22/job/dashboard.py:12-14 — classification thresholds assume 0–100 range
- Example misclassification A: Claude score 55 + all positive rule signals (+53) = 108 → classified "high" by accident despite mediocre semantic fit
- Example misclassification B: Claude score 90 + travel >25% penalty (-20) + onsite penalty (-5) + no eLearning tools (-10) = 55 → classified "mid" even though semantic fit is excellent

## Proposed Solutions
### Option A
Clamp final_score to 0–100 at the point of computation in ranker.py:

```python
final_score = max(0, min(100, claude_score + rule_score))
```

Add a docstring documenting the contract: claude_score is 0–100, rule adjustments shift it, result is clamped. Existing dashboard thresholds remain valid.

- Pros: Minimal change, preserves existing threshold calibration, easy to reason about
- Cons: Extreme rule adjustments lose resolution at the boundaries (a job that would score 120 looks the same as one that scores 100)
- Effort: Small
- Risk: Low

### Option B
Recalibrate dashboard thresholds to match the actual unbounded range: high >= 120, mid >= 90, given that the theoretical max is 153. No clamping needed.

- Pros: Preserves full numeric range for sorting; high-signal jobs float further above
- Cons: Thresholds feel arbitrary without a clear 0–100 mental model; confusing for future maintainers
- Effort: Small
- Risk: Medium

## Acceptance Criteria
- [ ] final_score is always in the range 0–100 for every job processed
- [ ] Dashboard "high" / "mid" / "low" classifications correctly reflect job quality relative to thresholds
- [ ] A unit test covers the boundary: claude_score=90 + rule_score=+53 → final_score=100 (not 143)
- [ ] A unit test covers the floor: claude_score=10 + rule_score=-70 → final_score=0 (not -60)

## Work Log
- 2026-06-01: Identified in code review
