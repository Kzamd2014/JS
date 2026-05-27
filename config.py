import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LINKEDIN_COOKIES = os.getenv("LINKEDIN_COOKIES", "[]")
GLASSDOOR_COOKIES = os.getenv("GLASSDOOR_COOKIES", "[]")

OUTPUT_DIR = Path("output")
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

RESUME_TEXT = """
Kelly Zamboni — Instructional Design & OCM Consultant, 18+ years experience
Kansas City, MO

SKILLS:
ADDIE methodology, ILT/VILT, eLearning, Train-the-Trainer, enterprise system training,
go-live support, OCM planning, stakeholder engagement, impact analysis, organizational
readiness assessment, communications planning, LMS administration.

TOOLS: Articulate 360, Adobe Creative Suite, Camtasia, Snagit, Saba Cloud LMS,
Salesforce, Microsoft Teams.

CERTIFICATIONS: Change Management Practitioner, SAFe 6 Scrum Master, CSM,
Certified Product Manager L1.

EXPERIENCE:

Federal Reserve Bank of Kansas City — Learning Consultant (Mar 2023–present)
- Built curated learning paths for Technology division (1,300+ views)
- Overhauled mandatory online training for all 3,000 board employees
- Led skills gap analysis for 80 staff; designed learning pathways and T3 resources

Federal Reserve Bank of Kansas City — Learning Designer (Jul 2020–Mar 2023)
- Built COMPASS eLearning from scratch using Articulate 360, Adobe Creative Suite, Snagit
- Created Train-the-Trainer materials for client-sustained delivery post go-live
- Ran Salesforce VILT for 60+ staff; built async eLearning backup modules

Terracon Consultants — Learning Technology Analyst (Jul 2019–Jul 2020)
- LMS dashboards and reporting for 5,000+ employees; cut manual reporting time ~40%
- Partnered with IT on LMS issue resolution; maintained ~98% uptime

Terracon Consultants — Instructional Designer (May 2016–Jul 2019)
- Safety compliance eLearning for 5,000+ field employees (Articulate 360, Adobe Creative Suite)
- Performance support videos in Camtasia; cut support requests ~20%

Shook Hardy & Bacon — Instructional Designer (Apr 2008–Jul 2013)
- Billing system rollout for 400+ users; 90%+ completion before go-live
- Post-launch help desk tickets reduced ~25% via readiness and comms planning
- Role-specific ID for attorneys, paralegals, and support staff; onboarding time cut ~20%

GMAC Financial — Senior Trainer (Sep 2006–Apr 2008)
- Trained 200+ agents across underwriting, sales, customer service, system apps
- Cut ramp-to-productivity 30%; 95% post-training assessment pass rate

EDUCATION:
MS Human Resource Management — Lindenwood University
BSBA Management & Organizational Behavior — University of Missouri–St. Louis
"""
