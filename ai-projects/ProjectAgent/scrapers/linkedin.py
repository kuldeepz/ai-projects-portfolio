"""
LinkedIn Jobs scraper — uses public search endpoint (no login required).
Location queries are derived from LOCATIONS in config.
"""

import time
import requests
from bs4 import BeautifulSoup
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import SEARCH_KEYWORDS, LOCATIONS, ALL_LOCATIONS
from visa_checker import has_visa_sponsorship

SEARCH_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def _build_location_queries() -> list:
    """Convert config LOCATIONS dict into LinkedIn location search strings."""
    queries = []
    country_display = {
        "germany": "Germany",
        "netherlands": "Netherlands",
        "uk": "United Kingdom",
        "france": "France",
        "usa": "United States",
        "canada": "Canada",
        "australia": "Australia",
    }
    for country, cities in LOCATIONS.items():
        country_label = country_display.get(country.lower(), country.title())
        for city in cities:
            if city not in ("remote", "worldwide", "anywhere"):
                queries.append(f"{city.title()}, {country_label}")
    if not queries:
        queries = ["Remote"]
    return queries


def _location_allowed(loc: str) -> bool:
    loc_lower = loc.lower()
    allowed_terms = ALL_LOCATIONS + ["remote"]
    # Also allow country names from LOCATIONS keys
    allowed_terms += [c.lower() for c in LOCATIONS.keys()]
    return any(term in loc_lower for term in allowed_terms)


def _fetch_page(keyword: str, location: str) -> list:
    params = {
        "keywords": keyword,
        "location": location,
        "f_TPR": "r2592000",  # last 30 days
        "start": 0,
    }
    try:
        resp = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        jobs = []
        for card in soup.find_all("li"):
            try:
                title_el   = card.find("h3", class_="base-search-card__title")
                company_el = card.find("h4", class_="base-search-card__subtitle")
                loc_el     = card.find("span", class_="job-search-card__location")
                link_el    = card.find("a", class_="base-card__full-link")
                id_el      = card.find("div", class_="base-card")

                title   = title_el.get_text(strip=True)   if title_el   else ""
                company = company_el.get_text(strip=True) if company_el else ""
                loc     = loc_el.get_text(strip=True)     if loc_el     else ""
                url     = link_el["href"].split("?")[0]   if link_el    else ""
                job_id  = id_el.get("data-entity-urn", url) if id_el   else url

                if title:
                    jobs.append({
                        "id":                  f"linkedin_{job_id}",
                        "title":               title,
                        "company":             company,
                        "location":            loc,
                        "url":                 url,
                        "source":              "LinkedIn",
                        "posted":              "",
                        "remote":              False,
                        "salary":              "",
                        "description_snippet": "",
                        "visa_sponsor":        has_visa_sponsorship(title, "", loc),
                    })
            except Exception:
                continue
        return jobs
    except Exception as e:
        print(f"[LinkedIn] Error fetching '{keyword}' / '{location}': {e}")
        return []


def fetch_jobs() -> list:
    seen_urls = set()
    results   = []
    location_queries = _build_location_queries()

    # Use up to 3 keywords to avoid rate limiting
    keywords_to_try = SEARCH_KEYWORDS[:3]

    for keyword in keywords_to_try:
        for location in location_queries:
            for job in _fetch_page(keyword, location):
                if job["url"] and job["url"] not in seen_urls and _location_allowed(job["location"]):
                    seen_urls.add(job["url"])
                    results.append(job)
            time.sleep(1.5)

    print(f"[LinkedIn] Found {len(results)} matching jobs")
    return results
