import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LINKEDIN_COOKIES = os.getenv("LINKEDIN_COOKIES", "")
GLASSDOOR_COOKIES = os.getenv("GLASSDOOR_COOKIES", "")

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

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

RESUME_TEXT = (Path(__file__).parent / "data" / "resume.txt").read_text(encoding="utf-8")
