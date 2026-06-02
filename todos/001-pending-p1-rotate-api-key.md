---
name: 001-pending-p1-rotate-api-key
description: Live Anthropic API key stored in .env may be exposed in git history
metadata:
  type: project
  status: pending
  priority: p1
  tags: [code-review, security, credentials]
---

## Problem Statement
A live Anthropic API key (sk-ant-api03-...) exists in /home/kzamd22/job/.env. While .gitignore excludes .env from future commits, if the file was ever committed at any point the key is permanently embedded in git history and accessible to anyone with repo access. A leaked key enables unauthorized API usage billed to the account owner.

## Findings
- /home/kzamd22/job/.env:1 — contains live sk-ant-api03-... key
- Verify history exposure: `git log --all --full-history -- .env`
- If output is non-empty, the key was committed and must be treated as compromised regardless of current .gitignore state

## Proposed Solutions
### Option A
Rotate the key at console.anthropic.com immediately, then inject the new key via runtime environment variables (e.g., system-level env or a secrets manager) rather than storing it in any file on disk. Remove .env from the project entirely and update .env.example to document the expected variable names only.

- Pros: Eliminates the file-based secret entirely; works cleanly in CI/CD
- Cons: Slightly more setup friction for new developers
- Effort: Small
- Risk: Low

### Option B
Keep the .env workflow but add a pre-commit hook (e.g., using `detect-secrets` or a simple grep) that scans staged files for sk-ant-api03- patterns and blocks the commit. Rotate the current key regardless.

- Pros: Preserves familiar .env developer experience; catches future accidents
- Cons: Does not fix an already-leaked key; hooks can be bypassed with --no-verify
- Effort: Small
- Risk: Medium

## Acceptance Criteria
- [ ] API key rotated at console.anthropic.com and old key confirmed invalid
- [ ] `git log --all --full-history -- .env` returns empty (key was never committed) or rotation is confirmed as mitigation if history is non-empty
- [ ] .env file permissions set to 600 (`chmod 600 .env`)
- [ ] .env.example contains only placeholder values, no real credentials

## Work Log
- 2026-06-01: Identified in code review
