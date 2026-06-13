import os
import sys
from pathlib import Path

from rich.console import Console

console: Console = Console()


def validate_environment() -> None:
    api_key: str | None = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[bold red]Setup error:[/bold red] OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
        sys.exit(1)

    path_args: list[str] = [arg for arg in sys.argv[1:] if arg and not arg.startswith("-")]
    for raw_arg in path_args:
        candidate: Path = Path(raw_arg)
        if not candidate.exists():
            console.print(f"[bold red]Setup error:[/bold red] File does not exist: {candidate}")
            sys.exit(1)
        if not candidate.is_file():
            console.print(f"[bold red]Setup error:[/bold red] Path is not a file: {candidate}")
            sys.exit(1)
        if not os.access(candidate, os.R_OK):
            console.print(f"[bold red]Setup error:[/bold red] File is not readable: {candidate}")
            sys.exit(1)

    console.print("[bold green]Setup OK ✓[/bold green]")


def main() -> None:
    pass


if __name__ == "__main__":
    validate_environment()
    main()
