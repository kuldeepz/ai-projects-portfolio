"""
Job Search Agent — entry point.

Usage:
  python main.py                          Run once, score, email results
  python main.py --dry-run                Preview matches in console (no email)
  python main.py --sources arbeitnow      Limit to specific source(s)
"""

import sys
import os
import argparse
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

os.chdir(os.path.dirname(os.path.abspath(__file__)))

from scrapers import arbeitnow, linkedin, remotive
from storage import load_seen_jobs, save_seen_jobs, filter_new_jobs, mark_seen
from notifier import send_notification
from scorer import score_jobs


def run(dry_run: bool = False, sources: list = None):
    print(f"\n{'='*60}")
    print(f"Job Agent started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    active = set(sources) if sources else {"arbeitnow", "linkedin", "remotive"}
    all_jobs = []

    if "arbeitnow" in active:
        all_jobs += arbeitnow.fetch_jobs()
    if "linkedin" in active:
        all_jobs += linkedin.fetch_jobs()
    if "remotive" in active:
        all_jobs += remotive.fetch_jobs()

    print(f"\nTotal jobs fetched: {len(all_jobs)}")

    seen = load_seen_jobs()
    new_jobs = filter_new_jobs(all_jobs, seen)
    print(f"New jobs (not seen before): {len(new_jobs)}")

    if not new_jobs:
        print("No new jobs found this run.")
    else:
        print(f"\nScoring {len(new_jobs)} jobs against your resume…")
        relevant = score_jobs(new_jobs)
        print(f"Relevant jobs: {len(relevant)}")

        if relevant:
            if dry_run:
                print("\n[DRY RUN] Jobs that would be emailed:")
                for j in relevant:
                    score_str = f" [{j['score']}%]" if j.get("score") is not None else ""
                    print(f"  [{j['source']}]{score_str} {j['title']} @ {j['company']} ({j['location']})")
                print("\n[DRY RUN] Email skipped. Seen jobs not updated.")
            else:
                send_notification(relevant)
                seen = mark_seen(new_jobs, seen)
                save_seen_jobs(seen)
        else:
            print("No jobs passed relevance threshold — nothing to email.")
            if not dry_run:
                seen = mark_seen(new_jobs, seen)
                save_seen_jobs(seen)

    print(f"\nDone at {datetime.now().strftime('%H:%M:%S')}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Job search agent")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print matches to console without emailing or saving")
    parser.add_argument("--sources", nargs="+",
                        choices=["arbeitnow", "linkedin", "remotive"],
                        help="Limit to specific sources (default: all)")
    args = parser.parse_args()
    run(dry_run=args.dry_run, sources=args.sources)
