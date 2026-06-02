from scorer import score, parse_salary_min as _parse_salary_min


def _job(**kwargs):
    return {
        "site": "test", "title": "", "company": "Acme", "location": "KC",
        "url": "", "description": "", "remote": False, "salary": None,
        **kwargs,
    }


# ── Positive signals ──────────────────────────────────────────────────────────

def test_authoring_tools_signal():
    job = _job(title="Instructional Designer", description="Must have Articulate 360 and Camtasia experience.")
    result = score(job)
    assert result["rule_score"] >= 10
    assert any("+10" in s for s in result["rule_signals"])


def test_enterprise_signal():
    job = _job(title="Learning Consultant", description="Salesforce LMS implementation and ERP rollout support.")
    result = score(job)
    assert any("+10 Enterprise" in s for s in result["rule_signals"])


def test_ocm_signal():
    job = _job(title="Learning Consultant", description="OCM planning, change management, stakeholder engagement.")
    result = score(job)
    assert any("OCM" in s for s in result["rule_signals"])


def test_senior_title_signal():
    job = _job(title="Senior Instructional Designer", description="Instructional design role.")
    result = score(job)
    assert any("+8" in s for s in result["rule_signals"])


def test_consultant_title_signal():
    job = _job(title="Learning & Development Consultant", description="elearning design.")
    result = score(job)
    assert any("+8" in s for s in result["rule_signals"])


def test_remote_signal():
    job = _job(title="eLearning Developer", description="Remote position.", remote=True)
    result = score(job)
    assert any("+5" in s and "Remote" in s for s in result["rule_signals"])


def test_salary_positive():
    job = _job(title="Learning Consultant", description="Instructional design tools required.", salary="$90,000 - $110,000/year")
    result = score(job)
    assert any("+5" in s and "Salary" in s for s in result["rule_signals"])


def test_t3_signal():
    job = _job(title="Learning Consultant", description="Build train-the-trainer materials and support go-live.")
    result = score(job)
    assert any("+5 Train" in s for s in result["rule_signals"])


def test_addie_signal():
    job = _job(title="Instructional Designer", description="Apply ADDIE methodology and instructional design best practices.")
    result = score(job)
    assert any("+5 ADDIE" in s for s in result["rule_signals"])


# ── Negative signals ──────────────────────────────────────────────────────────

def test_salary_negative():
    job = _job(title="Trainer", description="elearning development role.", salary="$55,000")
    result = score(job)
    assert any("-15" in s for s in result["rule_signals"])


def test_entry_level_penalty():
    job = _job(title="Junior Instructional Designer", description="elearning, lms, instructional design.")
    result = score(job)
    assert any("-15" in s for s in result["rule_signals"])


def test_entry_level_roman_numeral():
    job = _job(title="Instructional Designer I", description="elearning, lms, instructional design.")
    result = score(job)
    assert any("-15" in s for s in result["rule_signals"])


def test_hr_generalist_penalty():
    job = _job(title="HR Coordinator", description="HRIS, benefits administration, payroll, recruiting, compensation.")
    result = score(job)
    assert any("-20" in s for s in result["rule_signals"])


def test_hr_with_elearn_not_penalized():
    """An HR role that also mentions eLearning tools should NOT get the -20 HR penalty."""
    job = _job(title="HR & Learning Specialist", description="HRIS administration plus Articulate 360 eLearning design.")
    result = score(job)
    assert not any("-20 HR" in s for s in result["rule_signals"])


def test_no_elearn_tools_penalty():
    job = _job(title="HR Generalist", description="General human resources support and administration.")
    result = score(job)
    assert any("-10" in s for s in result["rule_signals"])


def test_high_travel_penalty_percent_first():
    job = _job(title="Training Consultant", description="elearning design. 75% travel required.")
    result = score(job)
    assert any("-20" in s and "Travel" in s for s in result["rule_signals"])


def test_high_travel_penalty_up_to():
    job = _job(title="Training Consultant", description="elearning design. Must be willing to travel up to 50%.")
    result = score(job)
    assert any("-20" in s and "Travel" in s for s in result["rule_signals"])


def test_low_travel_no_penalty():
    job = _job(title="Training Consultant", description="elearning design. Travel up to 20%.")
    result = score(job)
    assert not any("Travel" in s for s in result["rule_signals"])


def test_onsite_penalty():
    job = _job(title="Instructional Designer", description="This is an in-office position. elearning, instructional design.", remote=False)
    result = score(job)
    assert any("-5 Fully onsite" in s for s in result["rule_signals"])


def test_onsite_no_penalty_if_remote():
    job = _job(title="Instructional Designer", description="100% on-site. elearning, instructional design.", remote=True)
    result = score(job)
    assert not any("-5" in s for s in result["rule_signals"])


# ── Salary parser ──────────────────────────────────────────────────────────────

def test_parse_annual_with_commas():
    assert _parse_salary_min("$80,000/year") == 80000


def test_parse_k_suffix():
    assert _parse_salary_min("$80k - $100k") == 80000


def test_parse_hourly():
    assert _parse_salary_min("$40/hour") == 40 * 2080


def test_parse_none():
    assert _parse_salary_min(None) is None


def test_parse_range():
    assert _parse_salary_min("$85,000 - $105,000") == 85000


def test_parse_non_salary_text_ignored():
    """Numbers not preceded by $ should not be treated as salary."""
    assert _parse_salary_min("Posted 7 days ago") is None


def test_parse_401k_not_misread():
    """'401(k)' should not produce a salary value."""
    assert _parse_salary_min("401(k) match available") is None


def test_parse_small_number_no_unit_ignored():
    """A bare $40 without /hr context should be skipped (ambiguous)."""
    assert _parse_salary_min("$40") is None
