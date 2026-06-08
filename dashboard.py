import secrets
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader


def generate(jobs: list[dict], output_path: Path) -> None:
    enriched = []
    for job in jobs:
        s = job.get("final_score", 0)
        enriched.append({
            **job,
            "score_class": "high" if s >= 80 else ("mid" if s >= 60 else "low"),
            "salary_num": job.get("salary_min", 0),
        })

    env = Environment(
        loader=FileSystemLoader(Path(__file__).parent / "templates"),
        autoescape=True,
    )
    template = env.get_template("dashboard.html.j2")
    sites = sorted({j.get("site", "") for j in enriched if j.get("site")})
    nonce = secrets.token_hex(16)
    html = template.render(
        jobs=enriched,
        sites=sites,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        nonce=nonce,
    )
    output_path.write_text(html, encoding="utf-8")
    print(f"Dashboard → {output_path}  ({len(enriched)} jobs)")
