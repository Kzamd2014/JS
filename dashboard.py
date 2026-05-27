from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from scorer import _parse_salary_min


def generate(jobs: list[dict], output_path: Path) -> None:
    for job in jobs:
        score = job.get("final_score", 0)
        job["score_class"] = "high" if score >= 80 else ("mid" if score >= 60 else "low")
        job["salary_num"] = _parse_salary_min(job.get("salary")) or 0

    env = Environment(loader=FileSystemLoader(Path(__file__).parent / "templates"))
    template = env.get_template("dashboard.html.j2")
    sites = sorted({j.get("site", "") for j in jobs if j.get("site")})
    html = template.render(
        jobs=jobs,
        sites=sites,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard → {output_path}  ({len(jobs)} jobs)")
