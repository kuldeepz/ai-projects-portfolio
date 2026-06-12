import argparse
import json
import os
from datetime import datetime, timezone


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite-file", default="suite.json")
    parser.add_argument("--export", action="store_true")
    return parser.parse_args()


def validate_environment():
    args = _parse_args()

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or not api_key.strip():
        raise SystemExit(1)

    if not os.path.isfile(args.suite_file):
        raise SystemExit(1)

    if not os.access(args.suite_file, os.R_OK):
        raise SystemExit(1)



def validate_suite(suite):
    required_fields = ["name", "system_prompt", "test_cases"]
    for field in required_fields:
        if field not in suite:
            raise SystemExit(1)
        if isinstance(suite[field], str) and not suite[field].strip():
            raise SystemExit(1)

    if not isinstance(suite["test_cases"], list) or len(suite["test_cases"]) == 0:
        raise SystemExit(1)



def run_evaluation(*args, **kwargs):
    return {"summary": {"passed": 0, "failed": 0}, "details": []}



def _build_export_filename(now=None):
    now = now or datetime.now(timezone.utc)
    return f"output_{now.strftime('%Y%m%d_%H%M%S')}.json"



def _export_results(results):
    payload = {"generated_at": datetime.now(timezone.utc).isoformat(), **results}
    output_path = _build_export_filename()
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return output_path



def main():
    args = _parse_args()

    validate_environment()

    with open(args.suite_file, "r", encoding="utf-8") as f:
        suite = json.load(f)

    validate_suite(suite)
    results = run_evaluation(suite)

    if args.export:
        _export_results(results)

    return results
