import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--export", "-e", nargs="?", const=True, default=False)
    parser.add_argument("paths", nargs="*")
    return parser.parse_args(sys.argv[1:])


def validate_environment(args: argparse.Namespace) -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[bold red]Setup error:[/bold red] OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
        sys.exit(1)

    for raw_arg in args.paths:
        candidate = Path(raw_arg)
        if not candidate.exists():
            console.print(f"[bold red]Setup error:[/bold red] File does not exist: {candidate}")
            sys.exit(1)
        if not candidate.is_file():
            console.print(f"[bold red]Setup error:[/bold red] Path is not a file: {candidate}")
            sys.exit(1)
        if not os.access(candidate, os.R_OK):
            console.print(f"[bold red]Setup error:[/bold red] File is not readable: {candidate}")
            sys.exit(1)


def main(args: argparse.Namespace) -> None:
    export_requested = bool(args.export)
    results = {}

    if export_requested:
        if isinstance(args.export, str):
            export_path = Path(args.export)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            export_path = Path(f"output_{timestamp}.json")

        export_payload = {**results, "generated_at": datetime.now().isoformat()}
        try:
            with export_path.open("w", encoding="utf-8") as f:
                json.dump(export_payload, f, ensure_ascii=False, indent=2)
        except OSError as e:
            console.print(f"[bold red]Export error:[/bold red] {e}")
            sys.exit(1)


if __name__ == "__main__":
    parsed_args = parse_args()
    validate_environment(parsed_args)
    main(parsed_args)
