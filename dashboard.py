from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape
from scorer import _parse_salary_min


def generate(jobs: list[dict], output_path: Path) -> None:
    enriched = []
    for job in jobs:
        s = job.get("final_score", 0)
        enriched.append({
            **job,
            "score_class": "high" if s >= 80 else ("mid" if s >= 60 else "low"),
            "salary_num": _parse_salary_min(job.get("salary")) or 0,
        })

    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("dashboard.html.j2")
    sites = sorted({j.get("site", "") for j in enriched if j.get("site")})
    html = template.render(
        jobs=enriched,
        sites=sites,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
    )
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard → {output_path}  ({len(enriched)} jobs)")
