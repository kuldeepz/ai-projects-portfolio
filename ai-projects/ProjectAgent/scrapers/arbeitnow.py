"""
Arbeitnow.com scraper — free public API, best for Germany/EU jobs.
API docs: https://www.arbeitnow.com/api/job-board-api
"""

import time
import requests
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import SEARCH_KEYWORDS, ALL_LOCATIONS
from visa_checker import has_visa_sponsorship

API_URL = "https://www.arbeitnow.com/api/job-board-api"


def _matches(job: dict) -> bool:
    title = (job.get("title") or "").lower()
    tags  = " ".join(job.get("tags") or []).lower()
    loc   = (job.get("location") or "").lower()

    keyword_hit  = any(kw in title or kw in tags for kw in SEARCH_KEYWORDS)
    location_hit = any(loc_term in loc for loc_term in ALL_LOCATIONS)
    return keyword_hit and location_hit


def _normalize(job: dict) -> dict:
    title = job.get("title", "N/A")
    desc  = job.get("description", "") or ""
    loc   = job.get("location", "N/A")
    return {
        "id":                  f"arbeitnow_{job.get('slug', title)}",
        "title":               title,
        "company":             job.get("company_name", "N/A"),
        "location":            loc,
        "url":                 job.get("url", ""),
        "source":              "Arbeitnow",
        "posted":              job.get("created_at", ""),
        "remote":              job.get("remote", False),
        "salary":              "",
        "description_snippet": desc[:300].strip(),
        "visa_sponsor":        has_visa_sponsorship(title, desc, loc),
    }


def fetch_jobs(max_pages: int = 5) -> list:
    results = []

    for page in range(1, max_pages + 1):
        for attempt in range(3):
            try:
                resp = requests.get(API_URL, params={"page": page}, timeout=15)
                if resp.status_code == 429:
                    wait = 10 * (attempt + 1)
                    print(f"[Arbeitnow] Rate limited, retrying in {wait}s…")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                data = resp.json().get("data", [])
                break
            except Exception as e:
                print(f"[Arbeitnow] Error page {page} attempt {attempt+1}: {e}")
                if attempt == 2:
                    print(f"[Arbeitnow] Found {len(results)} matching jobs")
                    return results
                time.sleep(5)
        else:
            break

        if not data:
            break

        for job in data:
            if _matches(job):
                results.append(_normalize(job))

        time.sleep(2)

    print(f"[Arbeitnow] Found {len(results)} matching jobs")
    return results
