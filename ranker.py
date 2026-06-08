import json
import os
import re
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from config import RESUME_TEXT, ANTHROPIC_API_KEY, OUTPUT_DIR

_client: anthropic.Anthropic | None = None
_SYSTEM: str | None = None
_CACHE_PATH = OUTPUT_DIR / "scores_cache.json"


def _get_system() -> str:
    global _SYSTEM
    if _SYSTEM is None:
        _SYSTEM = f"""You are a job-fit evaluator. Your task is to score how well the candidate below fits a job description.

CANDIDATE RESUME:
{RESUME_TEXT}

Respond with JSON only — no markdown, no explanation outside the JSON:
{{"score": <integer 0-100>, "rationale": "<1-2 sentences max>"}}

Scoring guide:
- 80-100: Strong match — role clearly fits background, tools, and experience level
- 60-79: Solid fit — most requirements match, minor gaps
- 40-59: Partial fit — some overlap but meaningful gaps
- 0-39: Poor fit — significant mismatch in role, tools, or level
"""
    return _SYSTEM


def _client_instance() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY, timeout=30.0)
    return _client


def _load_cache() -> dict:
    if _CACHE_PATH.exists():
        try:
            return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_cache(cache: dict) -> None:
    tmp = _CACHE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(cache, indent=2), encoding="utf-8")
    os.replace(tmp, _CACHE_PATH)


def _create_with_retry(client: anthropic.Anthropic, **kwargs) -> anthropic.types.Message:
    for attempt in range(4):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError:
            if attempt == 3:
                raise
            wait = 10 * (2 ** attempt)  # 10s, 20s, 40s
            print(f"  Rate limited — waiting {wait}s before retry {attempt + 1}/3...")
            time.sleep(wait)
    raise RuntimeError("unreachable")


def rank_job(job: dict) -> dict:
    description = (job.get("description") or job.get("title") or "")[:4000]
    title = str(job.get("title") or "Unknown")[:200]
    company = str(job.get("company") or "Unknown")[:200]
    location = str(job.get("location") or "")[:100]
    salary = str(job.get("salary") or "Not listed")[:100]
    api_failed = False

    try:
        client = _client_instance()
        time.sleep(1.5)  # ~24 RPM across 2 workers, stays under 50 RPM / 50k TPM limits
        response = _create_with_retry(
            client,
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            system=[{
                "type": "text",
                "text": _get_system(),
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    f"Job Title: {title}\n"
                    f"Company: {company}\n"
                    f"Location: {location}\n"
                    f"Salary: {salary}\n\n"
                    f"<job_description>\n{description}\n</job_description>"
                ),
            }],
        )
        text = response.content[0].text.strip()
        # Strip markdown code fences if the model wraps its output
        m = re.search(r'\{.*?\}', text, re.DOTALL)
        if not m:
            raise json.JSONDecodeError("No JSON object found", text, 0)
        result = json.loads(m.group())
        claude_score = max(0, min(100, int(result.get("score", 50))))
        rationale = str(result.get("rationale", ""))[:300]
    except anthropic.AuthenticationError as e:
        raise RuntimeError(
            "Anthropic API authentication failed — check ANTHROPIC_API_KEY in .env"
        ) from e
    except json.JSONDecodeError as e:
        print(f"  WARNING: JSON parse error for '{job.get('title')}': {e}")
        claude_score = 50
        rationale = "parse error"
        api_failed = True
    except Exception as e:
        print(f"  WARNING: API error for '{job.get('title')}': {type(e).__name__}: {e}")
        claude_score = 50
        rationale = "API error"
        api_failed = True

    rule_score = job.get("rule_score", 0)
    return {
        **job,
        "claude_score": claude_score,
        "claude_rationale": rationale,
        "claude_api_failed": api_failed,
        "final_score": max(0, min(100, claude_score + rule_score)),
    }


def rank_jobs(jobs: list[dict]) -> list[dict]:
    cache = _load_cache()

    # Split into cached and uncached
    pre_ranked: dict[int, dict] = {}
    to_rank: list[tuple[int, dict]] = []
    for i, job in enumerate(jobs):
        url = job.get("url", "")
        if url and url in cache:
            cached = cache[url]
            rule_score = job.get("rule_score", 0)
            claude_score = max(0, min(100, int(cached.get("claude_score", 50))))
            rationale = str(cached.get("claude_rationale", ""))[:300]
            pre_ranked[i] = {
                **job,
                "claude_score": claude_score,
                "claude_rationale": rationale,
                "claude_api_failed": False,
                "final_score": max(0, min(100, claude_score + rule_score)),
            }
        else:
            to_rank.append((i, job))

    if pre_ranked:
        print(f"  [{len(pre_ranked)}/{len(jobs)} loaded from cache]")

    ranked: dict[int, dict] = dict(pre_ranked)
    completed = len(pre_ranked)
    new_cache_entries: list[tuple[str, dict]] = []

    def _rank_one(idx_job: tuple[int, dict]) -> tuple[int, dict, tuple | None]:
        i, job = idx_job
        result = rank_job(job)
        url = job.get("url", "")
        cache_entry = None
        if url and not result.get("claude_api_failed"):
            cache_entry = (url, {
                "claude_score": result["claude_score"],
                "claude_rationale": result["claude_rationale"],
            })
        return i, result, cache_entry

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(_rank_one, item): item for item in to_rank}
        for future in as_completed(futures):
            try:
                i, result, cache_entry = future.result()
            except Exception as e:
                print(f"  WARNING: Ranking failed: {type(e).__name__}: {e}\n{traceback.format_exc()}")
                continue
            ranked[i] = result
            if cache_entry:
                new_cache_entries.append(cache_entry)
            completed += 1
            print(f"  Ranked {completed}/{len(jobs)}: {result.get('title')} @ {result.get('company')}")

    if new_cache_entries:
        for url, entry in new_cache_entries:
            cache[url] = entry
        _save_cache(cache)

    failures = sum(1 for j in ranked.values() if j.get("claude_api_failed"))
    if failures:
        print(f"\n  WARNING: {failures}/{len(ranked)} Claude API calls failed — semantic scores unreliable.")
        if failures == len(ranked):
            print("  All calls failed — check ANTHROPIC_API_KEY in .env.")

    return sorted(ranked.values(), key=lambda j: j["final_score"], reverse=True)
