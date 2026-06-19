# config.py — loads all settings from .env (or environment variables).
# Edit .env to change your search. Never put secrets in this file.

import os
from pathlib import Path

# ── Load .env without external dependencies ──────────────────
_env_path = Path(__file__).parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── Email ────────────────────────────────────────────────────
NOTIFY_EMAIL      = os.environ.get("NOTIFY_EMAIL", "")
SMTP_HOST         = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT         = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER         = os.environ.get("SMTP_USER", "")
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "").replace(" ", "")

# ── AI Scoring ───────────────────────────────────────────────
# Standard OpenAI
OPENAI_API_KEY  = os.environ.get("OPENAI_API_KEY", "")

# Azure OpenAI (takes precedence if both are set)
AZURE_OPENAI_KEY        = os.environ.get("AZURE_OPENAI_KEY", "")
AZURE_OPENAI_ENDPOINT   = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
AZURE_OPENAI_DEPLOYMENT = os.environ.get("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

RESUME_PATH = os.environ.get("RESUME_PATH", "resume.md")
# Resolve relative paths from the project directory
if not os.path.isabs(RESUME_PATH):
    RESUME_PATH = str(Path(__file__).parent / RESUME_PATH)

MIN_SCORE        = int(os.environ.get("MIN_SCORE", "40"))
MAX_JOB_AGE_DAYS = int(os.environ.get("MAX_JOB_AGE_DAYS", "30"))
SEEN_JOBS_FILE   = "seen_jobs.json"

# ── Search keywords ──────────────────────────────────────────
_kw_raw = os.environ.get(
    "SEARCH_KEYWORDS",
    "engineering manager,AI lead,ML manager,tech lead,head of engineering,AI manager,machine learning lead"
)
SEARCH_KEYWORDS = [k.strip().lower() for k in _kw_raw.split(",") if k.strip()]

# ── Target locations ─────────────────────────────────────────
# Parsed from: "Germany: berlin, munich; Netherlands: amsterdam"
def _parse_locations(raw: str) -> dict:
    result = {}
    if not raw or raw.strip().lower() == "remote":
        return {"worldwide": ["remote", "worldwide", "anywhere"]}
    for segment in raw.split(";"):
        segment = segment.strip()
        if ":" in segment:
            country, cities_str = segment.split(":", 1)
            cities = [c.strip().lower() for c in cities_str.split(",") if c.strip()]
            if cities:
                result[country.strip().lower()] = cities
    return result or {"worldwide": ["remote", "worldwide", "anywhere"]}

_loc_raw = os.environ.get(
    "LOCATIONS",
    "Germany: berlin, munich, frankfurt; Netherlands: amsterdam, rotterdam, utrecht"
)
LOCATIONS = _parse_locations(_loc_raw)
ALL_LOCATIONS = [loc for locs in LOCATIONS.values() for loc in locs]
