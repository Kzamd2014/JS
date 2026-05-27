import json
import anthropic
from config import RESUME_TEXT, ANTHROPIC_API_KEY

_client: anthropic.Anthropic | None = None

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


def _client_instance() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not ANTHROPIC_API_KEY:
            raise RuntimeError("ANTHROPIC_API_KEY is not set. Add it to your .env file.")
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def rank_job(job: dict) -> dict:
    description = (job.get("description") or job.get("title") or "")[:4000]

    try:
        client = _client_instance()
        response = client.messages.create(
            model="claude-sonnet-4-6-20251001",
            max_tokens=256,
            system=[{
                "type": "text",
                "text": _SYSTEM,
                "cache_control": {"type": "ephemeral"},
            }],
            messages=[{
                "role": "user",
                "content": (
                    f"Job Title: {job.get('title', 'Unknown')}\n"
                    f"Company: {job.get('company', 'Unknown')}\n"
                    f"Location: {job.get('location', '')}\n"
                    f"Salary: {job.get('salary') or 'Not listed'}\n\n"
                    f"Description:\n{description}"
                ),
            }],
        )
        result = json.loads(response.content[0].text)
        claude_score = max(0, min(100, int(result.get("score", 50))))
        rationale = str(result.get("rationale", ""))
    except json.JSONDecodeError:
        claude_score = 50
        rationale = ""
    except Exception as e:
        claude_score = 50
        rationale = f"API error: {e}"

    return {
        **job,
        "claude_score": claude_score,
        "claude_rationale": rationale,
        "final_score": claude_score + job.get("rule_score", 0),
    }


def rank_jobs(jobs: list[dict]) -> list[dict]:
    ranked = []
    for i, job in enumerate(jobs, 1):
        print(f"  Ranking {i}/{len(jobs)}: {job.get('title')} @ {job.get('company')}")
        ranked.append(rank_job(job))
    return sorted(ranked, key=lambda j: j["final_score"], reverse=True)
