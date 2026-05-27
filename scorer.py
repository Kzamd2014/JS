import re
from typing import Optional


def _parse_salary_min(salary: Optional[str]) -> Optional[int]:
    if not salary:
        return None
    cleaned = salary.lower().replace(",", "").replace("$", "")
    nums = re.findall(r"(\d+(?:\.\d+)?)(k)?", cleaned)
    values = []
    for num, suffix in nums:
        val = float(num)
        if suffix == "k":
            val *= 1000
        elif val < 500:
            val *= 2080  # assume hourly → annual
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

    authoring_tools = ["articulate 360", "articulate storyline", "adobe creative suite", "camtasia", "snagit"]
    if any(t in text for t in authoring_tools):
        points += 10
        signals.append("+10 Authoring tools (Articulate/Adobe/Camtasia)")

    enterprise_terms = ["salesforce", " lms", "erp ", "enterprise system", "enterprise software", "enterprise application"]
    if any(e in text for e in enterprise_terms):
        points += 10
        signals.append("+10 Enterprise software (Salesforce/LMS/ERP)")

    ocm_terms = ["organizational change", "change management", "ocm ", "change enablement", "prosci", "adkar"]
    if any(o in text for o in ocm_terms):
        points += 10
        signals.append("+10 OCM / change management required")

    senior_terms = ["senior", "lead ", "principal", "consultant", "manager", "director", "specialist"]
    if any(s in title for s in senior_terms):
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

    t3_terms = ["train-the-trainer", "train the trainer", "go-live", "go live", "post-launch", "post launch", "hypercare"]
    if any(t in text for t in t3_terms):
        points += 5
        signals.append("+5 Train-the-Trainer / go-live support")

    id_terms = ["addie", "instructional design", " isd ", "instructional systems design", "sam model", "agile learning"]
    if any(i in text for i in id_terms):
        points += 5
        signals.append("+5 ADDIE / instructional design methodology")

    # --- Negative signals ---

    elearn_terms = [
        "articulate", "storyline", "captivate", "camtasia", "elearning", "e-learning",
        "learning management", "instructional design", "curriculum design", "course development",
        "lms", "ilt", "vilt", "training design",
    ]
    hr_generic_terms = [
        "hris", "benefits administration", "payroll", "talent acquisition", "recruiting",
        "hr business partner", "hrbp", "compensation and benefits", "employee relations",
    ]
    if any(h in text for h in hr_generic_terms) and not any(e in text for e in elearn_terms):
        points -= 20
        signals.append("-20 HR generalist (no L&D focus)")

    travel_match = re.search(r"(\d{2,3})\s*%?\s*(?:travel|traveling|on the road)", text)
    if travel_match:
        pct = int(travel_match.group(1))
        if pct > 25:
            points -= 20
            signals.append(f"-20 Travel >{pct}%")

    entry_terms = ["entry level", "entry-level", "junior ", "associate level", "level i ", "level 1 "]
    if any(e in title for e in entry_terms):
        points -= 15
        signals.append("-15 Entry-level / junior title")

    if not any(e in text for e in elearn_terms):
        points -= 10
        signals.append("-10 No eLearning or ID tools mentioned")

    onsite_terms = ["on-site only", "onsite only", "must be on-site", "must work on-site", "fully in-office", "in office full"]
    if any(o in text for o in onsite_terms) and not job.get("remote", False):
        points -= 5
        signals.append("-5 Fully onsite")

    return {**job, "rule_score": points, "rule_signals": signals}
