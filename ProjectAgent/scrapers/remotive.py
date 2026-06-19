"""
Remotive.com scraper — free public API, no auth required.
Good for remote roles worldwide.
API: https://remotive.com/api/remote-jobs
"""

import re
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import SEARCH_KEYWORDS, ALL_LOCATIONS
from visa_checker import has_visa_sponsorship

API_URL = "https://remotive.com/api/remote-jobs"

ALWAYS_ALLOWED = {"worldwide", "anywhere", "remote", "europe", "global"}


def _location_ok(job: dict) -> bool:
    loc = (job.get("candidate_required_location") or "").lower()
    if not loc:
        return True  # No restriction = open worldwide
    if any(t in loc for t in ALWAYS_ALLOWED):
        return True
    return any(city in loc for city in ALL_LOCATIONS)


def _normalize(job: dict) -> dict:
    desc  = job.get("description") or ""
    clean = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", desc)).strip()
    title = job.get("title", "N/A")
    loc   = job.get("candidate_required_location") or "Remote / Worldwide"
    return {
        "id":                  f"remotive_{job.get('id', '')}",
        "title":               title,
        "company":             job.get("company_name", "N/A"),
        "location":            loc,
        "url":                 job.get("url", ""),
        "source":              "Remotive",
        "posted":              job.get("publication_date", ""),
        "remote":              True,
        "salary":              job.get("salary", ""),
        "description_snippet": clean[:300],
        "visa_sponsor":        has_visa_sponsorship(title, desc, loc),
    }


def fetch_jobs() -> list:
    results  = []
    seen_ids = set()

    for query in SEARCH_KEYWORDS[:4]:
        try:
            resp = requests.get(API_URL, params={"search": query, "limit": 100}, timeout=15)
            resp.raise_for_status()
            for job in resp.json().get("jobs", []):
                jid = f"remotive_{job.get('id', '')}"
                if jid not in seen_ids and _location_ok(job):
                    seen_ids.add(jid)
                    results.append(_normalize(job))
        except Exception as e:
            print(f"[Remotive] Error for query '{query}': {e}")

    print(f"[Remotive] Found {len(results)} matching jobs")
    return results
