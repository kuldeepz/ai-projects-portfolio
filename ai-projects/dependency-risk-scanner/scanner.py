"""
Dependency Risk Scanner
Audits requirements.txt / package.json / pyproject.toml for outdated,
deprecated, or vulnerable packages and recommends upgrades.
"""

import os
import sys
import json
from datetime import datetime, timezone
from pathlib import Path


def validate_environment(argv=None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        print("Error: OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
        sys.exit(1)

    args = list(sys.argv[1:] if argv is None else argv)
    file_args = []
    export_path = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--export", "-e"):
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                export_path = args[i + 1]
                i += 2
            else:
                i += 1
            continue
        if arg.startswith("-"):
            i += 1
            continue
        file_args.append(arg)
        i += 1

    for file_arg in file_args:
        p = Path(file_arg)
        if not p.exists():
            print(f"Error: File does not exist: {file_arg}")
            sys.exit(1)
        if not p.is_file():
            print(f"Error: Path is not a file: {file_arg}")
            sys.exit(1)
        if not os.access(p, os.R_OK):
            print(f"Error: File is not readable: {file_arg}")
            sys.exit(1)

    print("Setup OK ✓")
    return file_args, export_path


def export_report(report: dict, output_path: str) -> str:
    payload = dict(report)
    payload["generated_at"] = datetime.now(timezone.utc).isoformat()

    out = Path(output_path)
    if out.parent and not out.parent.exists():
        out.parent.mkdir(parents=True, exist_ok=True)

    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")

    return str(out)


def _parse_cli(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    files = []
    export_path = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--export", "-e"):
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                export_path = args[i + 1]
                i += 2
            else:
                i += 1
            continue
        if not arg.startswith("-"):
            files.append(arg)
        i += 1

    return files, export_path


def main(argv=None):
    files, export_path = validate_environment(argv)

    # Placeholder scan result to keep this module runnable in isolation.
    report = {
        "ecosystem": "unknown",
        "total_packages": 0,
        "risk_summary": "No scan executed.",
        "packages": [],
        "critical_action_required": [],
    }

    if export_path:
        export_report(report, export_path)

    return report


if __name__ == "__main__":
    main()
