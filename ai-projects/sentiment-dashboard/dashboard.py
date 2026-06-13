import json
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[bold red]Setup error:[/bold red] OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
        sys.exit(1)

    args = sys.argv[1:]
    path_args = []
    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in ("--export", "-e"):
            if arg == "--export" and i + 1 < len(args) and not args[i + 1].startswith("-"):
                skip_next = True
            continue
        if arg and not arg.startswith("-"):
            path_args.append(arg)

    for raw_arg in path_args:
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


def main() -> None:
    export_requested = "--export" in sys.argv[1:] or "-e" in sys.argv[1:]
    results = {}

    if export_requested:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        export_path = Path(f"output_{timestamp}.json")
        export_payload = {**results, "generated_at": datetime.now().isoformat()}
        with export_path.open("w", encoding="utf-8") as f:
            json.dump(export_payload, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    validate_environment()
    main()
