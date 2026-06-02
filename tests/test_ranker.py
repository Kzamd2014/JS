from unittest.mock import MagicMock, patch
from ranker import rank_job, rank_jobs


def _job(**kwargs):
    return {
        "site": "test", "title": "Senior Instructional Designer", "company": "Acme",
        "location": "Remote", "url": "", "description": "Articulate 360, ADDIE, LMS rollout",
        "remote": True, "salary": "$90k", "rule_score": 15, "rule_signals": [],
        **kwargs,
    }


def _mock_response(score: int, rationale: str = "Good match.") -> MagicMock:
    resp = MagicMock()
    resp.content = [MagicMock(text=f'{{"score": {score}, "rationale": "{rationale}"}}')]
    return resp


def test_rank_job_success():
    with patch("ranker._client_instance") as mock_client:
        mock_client.return_value.messages.create.return_value = _mock_response(85)
        result = rank_job(_job())
    assert result["claude_score"] == 85
    assert result["final_score"] == 85 + 15
    assert result["claude_rationale"] == "Good match."


def test_rank_job_score_clamped_high():
    with patch("ranker._client_instance") as mock_client:
        mock_client.return_value.messages.create.return_value = _mock_response(150)
        result = rank_job(_job())
    assert result["claude_score"] == 100


def test_rank_job_score_clamped_low():
    with patch("ranker._client_instance") as mock_client:
        mock_client.return_value.messages.create.return_value = _mock_response(-10)
        result = rank_job(_job())
    assert result["claude_score"] == 0


def test_rank_job_json_parse_failure():
    resp = MagicMock()
    resp.content = [MagicMock(text="Not valid JSON at all")]
    with patch("ranker._client_instance") as mock_client:
        mock_client.return_value.messages.create.return_value = resp
        result = rank_job(_job(rule_score=5))
    assert result["claude_score"] == 50
    assert result["final_score"] == 55


def test_rank_job_api_error_returns_fallback():
    with patch("ranker._client_instance") as mock_client:
        mock_client.return_value.messages.create.side_effect = Exception("rate limit")
        result = rank_job(_job(rule_score=10))
    assert result["claude_score"] == 50
    assert result["claude_rationale"] == "API error"
    assert result["final_score"] == 60


def test_rank_jobs_sorted_descending():
    responses = [_mock_response(30), _mock_response(90)]
    jobs = [_job(rule_score=0), _job(rule_score=0)]
    with patch("ranker._client_instance") as mock_client:
        mock_client.return_value.messages.create.side_effect = lambda **_: responses.pop(0)
        ranked = rank_jobs(jobs)
    assert ranked[0]["final_score"] >= ranked[1]["final_score"]


def test_rank_jobs_one_api_error_does_not_abort():
    """A single API failure should not prevent other jobs from being ranked."""
    responses = [Exception("timeout"), _mock_response(80)]
    jobs = [_job(rule_score=0), _job(rule_score=0)]
    with patch("ranker._client_instance") as mock_client:
        mock_client.return_value.messages.create.side_effect = responses
        ranked = rank_jobs(jobs)
    assert len(ranked) == 2
    scores = {r["claude_score"] for r in ranked}
    assert 80 in scores
    assert 50 in scores  # fallback for the failed one


def test_missing_api_key_raises():
    with patch("ranker.ANTHROPIC_API_KEY", ""), patch("ranker._client", None):
        try:
            from ranker import _client_instance
            _client_instance()
            assert False, "Expected RuntimeError"
        except RuntimeError as e:
            assert "ANTHROPIC_API_KEY" in str(e)
