import json
import os
from config import SEEN_JOBS_FILE


def load_seen_jobs() -> set:
    if not os.path.exists(SEEN_JOBS_FILE):
        return set()
    with open(SEEN_JOBS_FILE, "r") as f:
        return set(json.load(f))


def save_seen_jobs(seen: set):
    with open(SEEN_JOBS_FILE, "w") as f:
        json.dump(list(seen), f)


def filter_new_jobs(jobs: list, seen: set) -> list:
    return [j for j in jobs if j["id"] not in seen]


def mark_seen(jobs: list, seen: set) -> set:
    return seen | {j["id"] for j in jobs}
