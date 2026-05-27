import re


def _parse_salary_min(salary: str | None) -> int | None:
    """Extract minimum annual salary. Only parses $-anchored numbers to avoid false positives."""
    if not salary:
        return None
    cleaned = salary.replace(",", "")
    pattern = re.compile(
        r'\$\s*(\d+(?:\.\d+)?)\s*(k|per\s*hr|per\s*hour|/hr|/hour|per\s*yr|per\s*year|/yr|/year)?',
        re.IGNORECASE,
    )
    values = []
    for m in pattern.finditer(cleaned):
        val = float(m.group(1))
        suffix = (m.group(2) or "").lower().replace(" ", "")
        if "k" in suffix:
            val *= 1000
        elif "hr" in suffix or "hour" in suffix:
            val *= 2080
        elif val < 1000:
            # Small number with no unit context — skip (avoids "$7 days ago"-style misreads)
            continue
        values.append(int(val))
    return min(values) if values else None


def _text(job: dict) -> str:
    return f"{job.get('title', '')} {job.get('description', '')}".lower()


def score(job: dict) -> dict:
    text = _text(job)
    title = job.get("title", "").lower()
    points = 0
    signals: list[str] = []

    # --- Positive signals ---

    authoring_patterns = [
        r'articulate\s*360', r'articulate\s*storyline', r'adobe\s*creative\s*suite',
        r'\bcamtasia\b', r'\bsnagit\b',
    ]
    if any(re.search(p, text) for p in authoring_patterns):
        points += 10
        signals.append("+10 Authoring tools (Articulate/Adobe/Camtasia)")

    enterprise_patterns = [
        r'\bsalesforce\b', r'\blms\b', r'\berp\b',
        r'enterprise\s+(?:system|software|application|platform)',
    ]
    if any(re.search(p, text) for p in enterprise_patterns):
        points += 10
        signals.append("+10 Enterprise software (Salesforce/LMS/ERP)")

    ocm_patterns = [
        r'organizational\s+change', r'change\s+management', r'\bocm\b',
        r'change\s+enablement', r'\bprosci\b', r'\badkar\b',
    ]
    if any(re.search(p, text) for p in ocm_patterns):
        points += 10
        signals.append("+10 OCM / change management required")

    senior_patterns = [r'\bsenior\b', r'\blead\b', r'\bconsultant\b', r'\bprincipal\b', r'\bdirector\b']
    if any(re.search(p, title) for p in senior_patterns):
        points += 8
        signals.append("+8 Senior/lead/consultant title")

    if job.get("remote", False):
        points += 5
        signals.append("+5 Remote or hybrid offered")

    salary_min = _parse_salary_min(job.get("salary"))
    if salary_min is not None:
        if salary_min >= 80000:
            points += 5
            signals.append(f"+5 Salary ≥$80k (${salary_min:,})")
        else:
            points -= 15
            signals.append(f"-15 Salary <$80k (${salary_min:,})")

    t3_patterns = [
        r'train[\s-]the[\s-]trainer', r'go[\s-]live', r'post[\s-]launch', r'\bhypercare\b',
    ]
    if any(re.search(p, text) for p in t3_patterns):
        points += 5
        signals.append("+5 Train-the-Trainer / go-live support")

    id_patterns = [
        r'\baddie\b', r'instructional\s+design', r'\bisd\b',
        r'instructional\s+systems\s+design', r'sam\s+model', r'agile\s+learning',
    ]
    if any(re.search(p, text) for p in id_patterns):
        points += 5
        signals.append("+5 ADDIE / instructional design methodology")

    # --- Negative signals ---

    elearn_patterns = [
        r'\barticulate\b', r'\bstoryline\b', r'\bcaptivate\b', r'\bcamtasia\b',
        r'\belearning\b', r'e[\s-]learning', r'learning\s+management',
        r'instructional\s+design', r'curriculum\s+design', r'course\s+development',
        r'\blms\b', r'\bilt\b', r'\bvilt\b', r'training\s+design',
    ]
    hr_generic_patterns = [
        r'\bhris\b', r'benefits\s+administration', r'\bpayroll\b',
        r'talent\s+acquisition', r'\brecruiting\b', r'hr\s+business\s+partner',
        r'\bhrbp\b', r'compensation\s+and\s+benefits', r'employee\s+relations',
    ]
    if (any(re.search(p, text) for p in hr_generic_patterns)
            and not any(re.search(p, text) for p in elearn_patterns)):
        points -= 20
        signals.append("-20 HR generalist (no L&D focus)")

    travel_pct = None
    for pat in [
        r'(\d+)\s*%\s*(?:travel|traveling)',
        r'travel\s+(?:up\s+to\s+|approximately\s+|about\s+)?(\d+)\s*%',
        r'(\d+)\s*%?\s*(?:travel|traveling|on\s+the\s+road)',
    ]:
        m = re.search(pat, text)
        if m:
            travel_pct = int(m.group(1))
            break
    if travel_pct and travel_pct > 25:
        points -= 20
        signals.append(f"-20 Travel >{travel_pct}%")

    entry_patterns = [
        r'entry[\s-]level', r'\bjunior\b', r'\btrainee\b', r'\bintern\b',
        r'new\s+grad(?:uate)?', r'level\s*[i1]\b', r'associate\s+level',
    ]
    if any(re.search(p, title) for p in entry_patterns):
        points -= 15
        signals.append("-15 Entry-level / junior title")

    if not any(re.search(p, text) for p in elearn_patterns):
        points -= 10
        signals.append("-10 No eLearning or ID tools mentioned")

    onsite_patterns = [
        r'on[\s-]?site\s+only', r'onsite\s+only', r'fully\s+in[\s-]office',
        r'100\s*%\s*on[\s-]?site', r'no\s+remote\s+work', r'must\s+be\s+on[\s-]?site',
        r'this\s+(?:role\s+)?is\s+(?:fully\s+)?in[\s-]office',
        r'office[\s-]based\s+only', r'required\s+(?:to\s+be\s+)?(?:on[\s-]?site|in[\s-]office)',
    ]
    if not job.get("remote", False) and any(re.search(p, text) for p in onsite_patterns):
        points -= 5
        signals.append("-5 Fully onsite")

    return {**job, "rule_score": points, "rule_signals": signals}
