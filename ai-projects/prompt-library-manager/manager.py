"""
Prompt Library Manager
A CLI tool to store, version, test, and compare prompts.
Acts as a local prompt registry for AI teams.
"""

import os, sys, json, hashlib
from datetime import datetime
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

load_dotenv()
console: Console = Console()
MODEL: str = "gpt-4o-mini"
LIBRARY_FILE: str = "prompt_library.json"
VERBOSE: bool = False

_client: OpenAI | None = None
def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def call_openai(input_content: str, temperature: float = 0.3) -> Any:
    if VERBOSE:
        console.print(f"[dim]Model:[/dim] {MODEL}")
        console.print(f"[dim]Input chars:[/dim] {len(input_content)}")
        console.print("⏳ Calling OpenAI API...")
    started = datetime.now()
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": input_content}],
        temperature=temperature,
    )
    if VERBOSE:
        elapsed = (datetime.now() - started).total_seconds()
        console.print(f"[dim]Completed in:[/dim] {elapsed:.2f}s")
        print_usage(response)
    return response

def print_usage(response: Any) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

def validate_environment() -> None:
    cmd = sys.argv[1] if len(sys.argv) >= 2 else None

    api_required = {"test", "compare"}
    if cmd in api_required:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.strip():
            console.print("[red]Error:[/red] OPENAI_API_KEY is not set. Please set it in your environment or .env file.")
            sys.exit(1)

    file_args = []
    if cmd == "add":
        if len(sys.argv) < 4:
            console.print("[red]Error:[/red] Usage: add <name> <prompt_file> [description]")
            sys.exit(1)
        file_args.append(sys.argv[2])

    for file_arg in file_args:
        p = Path(file_arg)
        if not p.exists():
            console.print(f"[red]Error:[/red] File path does not exist: {file_arg}")
            sys.exit(1)
        if not p.is_file():
            console.print(f"[red]Error:[/red] Path is not a file: {file_arg}")
            sys.exit(1)
        if not os.access(p, os.R_OK):
            console.print(f"[red]Error:[/red] File is not readable: {file_arg}")
            sys.exit(1)

def load_library() -> dict:
    if Path(LIBRARY_FILE).exists():
        with open(LIBRARY_FILE) as f:
            return json.load(f)
    return {"prompts": {}}

def save_library(lib: dict) -> None:
    with open(LIBRARY_FILE, "w") as f:
        json.dump(lib, f, indent=2)

def export_results(results: dict) -> None:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output_{timestamp}.json"
    payload = dict(results)
    payload["generated_at"] = datetime.now().isoformat()
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    console.print(f"[green]Exported results[/green] to [bold]{filename}[/bold]")

def cmd_add(name: str, prompt_text: str, description: str = "", tags: list | None = None) -> None:
    lib = load_library()
    version_hash = hashlib.md5(prompt_text.encode()).hexdigest()[:8]
    entry = lib["prompts"].get(name, {"name": name, "description": description, "tags": tags or [], "versions": []})
    entry["versions"].append({
        "hash": version_hash,
        "prompt": prompt_text,
        "created_at": datetime.now().isoformat(),
        "model": MODEL,
        "test_results": []
    })
    entry["current_version"] = version_hash
    lib["prompts"][name] = entry
    save_library(lib)
    console.print(f"[green]Added prompt[/green] [bold]{name}[/bold] (v{version_hash})")

def cmd_list() -> None:
    lib = load_library()
    if not lib["prompts"]:
        console.print("[dim]No prompts in library yet. Use 'add' to create one.[/dim]")
        return
    t = Table(show_header=True, header_style="bold cyan")
    t.add_column("Name"); t.add_column("Description", ratio=2)
    t.add_column("Versions", width=8); t.add_column("Tags"); t.add_column("Current Hash")
    for name, entry in lib["prompts"].items():
        t.add_row(
            name, entry.get("description", ""),
            str(len(entry["versions"])),
            ", ".join(entry.get("tags", [])),
            entry.get("current_version", "—")
        )
    console.print(Panel(t, title="[bold]Prompt Library[/bold]", border_style="cyan"))

def cmd_show(name: str) -> None:
    lib = load_library()
    if name not in lib["prompts"]:
        console.print(f"[red]Prompt not found:[/red] {name}"); return
    entry = lib["prompts"][name]
    for v in entry["versions"]:
        console.print(Panel(
            Syntax(v["prompt"], "text", theme="monokai", word_wrap=True),
            title=f"[bold]{name}[/bold] v{v['hash']} — {v['created_at'][:10]}",
            border_style="cyan"
        ))
        if v["test_results"]:
            for tr in v["test_results"]:
                console.print(Panel(
                    f"[dim]Input:[/dim] {tr['input']}\n\n[green]Output:[/green] {tr['output'][:300]}",
                    title="Test Result", border_style="dim"
                ))

def cmd_test(name: str, test_input: str) -> str | None:
    lib = load_library()
    if name not in lib["prompts"]:
        console.print(f"[red]Prompt not found:[/red] {name}"); return None
    en
