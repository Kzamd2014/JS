from scorer import score, _parse_salary_min


def _job(**kwargs):
    return {
        "site": "test", "title": "", "company": "Acme", "location": "KC",
        "url": "", "description": "", "remote": False, "salary": None,
        **kwargs,
    }


def test_authoring_tools_signal():
    job = _job(title="Instructional Designer", description="Must have Articulate 360 and Camtasia experience.")
    result = score(job)
    assert result["rule_score"] >= 10
    assert any("+10" in s for s in result["rule_signals"])


def test_ocm_signal():
    job = _job(title="Learning Consultant", description="OCM planning, change management, stakeholder engagement.")
    result = score(job)
    assert any("OCM" in s for s in result["rule_signals"])


def test_senior_title_signal():
    job = _job(title="Senior Instructional Designer", description="Instructional design role.")
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


def test_salary_negative():
    job = _job(title="Trainer", description="elearning development role.", salary="$55,000")
    result = score(job)
    assert any("-15" in s for s in result["rule_signals"])


def test_entry_level_penalty():
    job = _job(title="Junior Instructional Designer", description="elearning, lms, instructional design.")
    result = score(job)
    assert any("-15" in s for s in result["rule_signals"])


def test_hr_generalist_penalty():
    job = _job(title="HR Coordinator", description="HRIS, benefits administration, payroll, recruiting, compensation.")
    result = score(job)
    assert any("-20" in s for s in result["rule_signals"])


def test_no_elearn_tools_penalty():
    job = _job(title="HR Generalist", description="General human resources support and administration.")
    result = score(job)
    assert any("-10" in s for s in result["rule_signals"])


def test_high_travel_penalty():
    job = _job(title="Training Consultant", description="elearning design. Must be willing to travel 75% of the time.")
    result = score(job)
    assert any("-20" in s and "Travel" in s for s in result["rule_signals"])


# --- Salary parser ---

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
