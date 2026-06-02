import re

# Keywords that indicate a dollar amount is NOT a salary figure
_NON_SALARY = re.compile(
    r'\b(bonus|401\s*k|match|sign[\s-]on|equity|stock\s+option|referral|relocation)\b',
    re.IGNORECASE,
)

# Compiled once at module load — matches dollar amounts with optional unit suffix
_SALARY_PATTERN = re.compile(
    r'\$\s*(\d+(?:\.\d+)?)\s*(k|per\s*hr|per\s*hour|/hr|/hour|per\s*yr|per\s*year|/yr|/year)?',
    re.IGNORECASE,
)


def parse_salary_min(salary: str | None) -> int | None:
    """Extract minimum annual salary. Rejects bonus/perk dollar amounts and implausibly small values."""
    if not salary:
        return None
    cleaned = salary.replace(",", "")
    values = []
    for m in _SALARY_PATTERN.finditer(cleaned):
        trailing = cleaned[m.end():m.end() + 40]
        if _NON_SALARY.search(trailing):
            continue
        val = float(m.group(1))
        suffix = (m.group(2) or "").lower().replace(" ", "")
        if "k" in suffix:
            val *= 1000
        elif "hr" in suffix or "hour" in suffix:
            val *= 2080
        elif val < 1000:
            continue
        if val < 15000:
            continue
        values.append(int(val))
    return min(values) if values else None


def _text(job: dict) -> str:
    return f"{job.get('title', '')} {job.get('description', '')}".lower()


# Compile all pattern lists once at module load
_AUTHORING_PATTERNS = [re.compile(p) for p in [
    r'articulate\s*360', r'articulate\s*storyline', r'adobe\s*creative\s*suite',
    r'\bcamtasia\b', r'\bsnagit\b',
]]
_ENTERPRISE_PATTERNS = [re.compile(p) for p in [
    r'\bsalesforce\b', r'\blms\b', r'\berp\b',
    r'enterprise\s+(?:system|software|application|platform)',
]]
_OCM_PATTERNS = [re.compile(p) for p in [
    r'organizational\s+change', r'change\s+management', r'\bocm\b',
    r'change\s+enablement', r'\bprosci\b', r'\badkar\b',
]]
_SENIOR_PATTERNS = [re.compile(p) for p in [
    r'\bsenior\b', r'\blead\b', r'\bconsultant\b', r'\bprincipal\b', r'\bdirector\b',
]]
_T3_PATTERNS = [re.compile(p) for p in [
    r'train[\s-]the[\s-]trainer', r'go[\s-]live', r'post[\s-]launch', r'\bhypercare\b',
]]
_ID_PATTERNS = [re.compile(p) for p in [
    r'\baddie\b', r'instructional\s+design', r'\bisd\b',
    r'instructional\s+systems\s+design', r'sam\s+model', r'agile\s+learning',
]]
_ELEARN_PATTERNS = [re.compile(p) for p in [
    r'\barticulate\b', r'\bstoryline\b', r'\bcaptivate\b', r'\bcamtasia\b',
    r'\belearning\b', r'e[\s-]learning', r'learning\s+management',
    r'instructional\s+design', r'curriculum\s+design', r'course\s+development',
    r'\blms\b', r'\bilt\b', r'\bvilt\b', r'training\s+design',
]]
_HR_GENERIC_PATTERNS = [re.compile(p) for p in [
    r'\bhris\b', r'benefits\s+administration', r'\bpayroll\b',
    r'talent\s+acquisition', r'\brecruiting\b', r'hr\s+business\s+partner',
    r'\bhrbp\b', r'compensation\s+and\s+benefits', r'employee\s+relations',
    r'\bhr\s+generalist\b', r'human\s+resources\s+generalist',
    r'\bhr\s+coordinator\b',
]]
_ENTRY_PATTERNS = [re.compile(p) for p in [
    r'entry[\s-]level', r'\bjunior\b', r'\btrainee\b', r'\bintern\b',
    r'new\s+grad(?:uate)?', r'level\s*[i1]\b', r'associate\s+level',
    r'\bi$',
]]
_ONSITE_PATTERNS = [re.compile(p) for p in [
    r'on[\s-]?site\s+only', r'onsite\s+only', r'fully\s+in[\s-]office',
    r'100\s*%\s*on[\s-]?site', r'no\s+remote\s+work', r'must\s+be\s+on[\s-]?site',
    r'this\s+(?:role\s+)?is\s+(?:an?\s+)?(?:fully\s+)?in[\s-]office',
    r'office[\s-]based\s+only', r'required\s+(?:to\s+be\s+)?(?:on[\s-]?site|in[\s-]office)',
    r'in[\s-]office\s+(?:position|role|job)',
]]
_TRAVEL_PATTERNS = [
    re.compile(r'(\d+)\s*%\s*(?:travel|traveling)'),
    re.compile(r'travel\s+(?:up\s+to\s+|approximately\s+|about\s+)?(\d+)\s*%'),
]


def score(job: dict) -> dict:
    text = _text(job)
    title = job.get("title", "").lower()
    has_description = bool(job.get("description", "").strip())
    points = 0
    signals: list[str] = []

    # --- Positive signals ---

    if any(p.search(text) for p in _AUTHORING_PATTERNS):
        points += 10
        signals.append("+10 Authoring tools (Articulate/Adobe/Camtasia)")

    if any(p.search(text) for p in _ENTERPRISE_PATTERNS):
        points += 10
        signals.append("+10 Enterprise software (Salesforce/LMS/ERP)")

    if any(p.search(text) for p in _OCM_PATTERNS):
        points += 10
        signals.append("+10 OCM / change management required")

    if any(p.search(title) for p in _SENIOR_PATTERNS):
        points += 8
        signals.append("+8 Senior/lead/consultant title")

    if job.get("remote", False):
        points += 5
        signals.append("+5 Remote or hybrid offered")

    salary_min = parse_salary_min(job.get("salary"))
    if salary_min is not None:
        if salary_min >= 80000:
            points += 5
            signals.append(f"+5 Salary ≥$80k (${salary_min:,})")
        else:
            points -= 15
            signals.append(f"-15 Salary <$80k (${salary_min:,})")

    if any(p.search(text) for p in _T3_PATTERNS):
        points += 5
        signals.append("+5 Train-the-Trainer / go-live support")

    if any(p.search(text) for p in _ID_PATTERNS):
        points += 5
        signals.append("+5 ADDIE / instructional design methodology")

    # --- Negative signals ---

    if (any(p.search(text) for p in _HR_GENERIC_PATTERNS)
            and not any(p.search(text) for p in _ELEARN_PATTERNS)):
        points -= 20
        signals.append("-20 HR generalist (no L&D focus)")

    travel_pct = None
    for pat in _TRAVEL_PATTERNS:
        m = pat.search(text)
        if m:
            travel_pct = int(m.group(1))
            break
    if travel_pct and travel_pct > 25:
        points -= 20
        signals.append(f"-20 Travel >{travel_pct}%")

    if any(p.search(title) for p in _ENTRY_PATTERNS):
        points -= 15
        signals.append("-15 Entry-level / junior title")

    if not has_description:
        signals.append("(skip) No description — eLearning/onsite penalties suppressed")
    else:
        if not any(p.search(text) for p in _ELEARN_PATTERNS):
            points -= 10
            signals.append("-10 No eLearning or ID tools mentioned")

        if not job.get("remote", False) and any(p.search(text) for p in _ONSITE_PATTERNS):
            points -= 5
            signals.append("-5 Fully onsite")

    result = {**job, "rule_score": points, "rule_signals": signals}
    if salary_min is not None:
        result["salary_min"] = salary_min
    return result
