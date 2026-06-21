import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ADZUNA_APP_ID = os.getenv("ADZUNA_APP_ID", "")
ADZUNA_APP_KEY = os.getenv("ADZUNA_APP_KEY", "")
LINKEDIN_COOKIES = os.getenv("LINKEDIN_COOKIES", "")
GLASSDOOR_COOKIES = os.getenv("GLASSDOOR_COOKIES", "")
LINKEDIN_RSS_FEEDS = [u.strip() for u in os.getenv("LINKEDIN_RSS_FEEDS", "").split(",") if u.strip()]

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.chmod(0o700)

DESCRIPTION_MAX_CHARS = 4000

PRIMARY_TITLES = [
    "Instructional Designer",
    "Senior Instructional Designer",
    "Learning Consultant",
    "Learning & Development Consultant",
    "OCM Consultant",
    "Change Management Specialist",
    "Learning Experience Designer",
    "eLearning Developer",
]

SECONDARY_TITLES = [
    "LMS Administrator",
    "Learning Technology Specialist",
    "IT Training Specialist",
    "Talent Development Consultant",
    "Technical Trainer",
    "HR Technology Consultant",
    "Performance Consultant",
]

ALL_TITLES = PRIMARY_TITLES + SECONDARY_TITLES

LOCATIONS = ["Kansas City, MO", "remote"]

def __getattr__(name: str) -> str:
    if name == "RESUME_TEXT":
        path = Path(__file__).parent / "data" / "resume.txt"
        if not path.exists():
            raise FileNotFoundError(
                f"Resume not found at {path}. "
                "Copy data/resume.txt.example to data/resume.txt and fill it in."
            )
        text = path.read_text(encoding="utf-8")
        globals()["RESUME_TEXT"] = text  # cache so __getattr__ isn't called again
        return text
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
