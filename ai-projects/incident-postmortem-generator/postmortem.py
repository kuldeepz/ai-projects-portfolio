import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Generate incident postmortems")
    parser.add_argument("files", nargs="+", help="Input incident file(s)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "-e",
        "--export",
        action="store_true",
        help="Export output as timestamped JSON",
    )
    return parser.parse_args(argv)


def validate_environment(args=None):
    if args is None:
        args = parse_args(sys.argv[1:])

    if not os.getenv("OPENAI_API_KEY"):
        console.print("OPENAI_API_KEY is not set")
        raise SystemExit(1)

    if not args.files:
        console.print("Provide at least one input file")
        raise SystemExit(2)

    for file_path in args.files:
        if not os.path.exists(file_path):
            console.print(f"File not found: {file_path}")
            raise SystemExit(1)
        if not os.path.isfile(file_path):
            console.print(f"Not a file: {file_path}")
            raise SystemExit(1)
        if not os.access(file_path, os.R_OK):
            console.print(f"File is not readable: {file_path}")
            raise SystemExit(1)

    if args.verbose:
        console.print("Setup OK")

    return args


def print_usage(response):
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if not usage:
        return

    prompt_tokens = getattr(usage, "prompt_tokens", None)
    completion_tokens = getattr(usage, "completion_tokens", None)
    total_tokens = getattr(usage, "total_tokens", None)

    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
        completion_tokens = usage.get("completion_tokens", completion_tokens)
        total_tokens = usage.get("total_tokens", total_tokens)

    prompt_tokens = prompt_tokens or 0
    completion_tokens = completion_tokens or 0
    total_tokens = total_tokens or (prompt_tokens + completion_tokens)

    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(
        f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}"
    )


def export_results(results):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"postmortem_export_{timestamp}.json")
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    return output_path


def run(args=None):
    args = validate_environment(args)

    # Placeholder processing result structure.
    results = {"files": args.files, "status": "ok"}

    if args.export:
        export_results(results)

    return results


if __name__ == "__main__":
    run()
