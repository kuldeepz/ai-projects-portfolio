"""Detects visa sponsorship mentions in job postings."""

import re

_PATTERNS = [
    r"visa\s+sponsor",
    r"sponsor.*visa",
    r"h-?1b",
    r"work\s+visa",
    r"relocation\s+visa",
    r"immigration\s+support",
    r"work\s+permit",
    r"right\s+to\s+work",
    r"employment\s+visa",
    r"visa\s+assist",
    r"visa\s+support",
]


def has_visa_sponsorship(title: str, description: str, location: str = "") -> bool:
    text = f"{title} {description} {location}".lower()
    return any(re.search(p, text) for p in _PATTERNS)
