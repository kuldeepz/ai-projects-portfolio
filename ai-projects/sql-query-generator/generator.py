...

def validate_environment(schema_paths=None, require_api_key=True):
    if require_api_key:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.strip():
            console.print("[red]Missing OPENAI_API_KEY.[/red] Set it in your environment or .env file.")
            sys.exit(1)

    for path_str in schema_paths or []:
        path = Path(path_str)
        if not path.exists():
            console.print(f"[red]File not found:[/red] {path_str}")
            sys.exit(1)
        if not path.is_file():
            console.print(f"[red]Not a file:[/red] {path_str}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"[red]File is not readable:[/red] {path_str}")
            sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")

...
