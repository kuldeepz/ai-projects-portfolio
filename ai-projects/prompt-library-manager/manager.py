"""
Prompt Library Manager
A CLI tool to store, version, test, and compare prompts.
Acts as a local prompt registry for AI teams.
"""

import os, sys, json, hashlib
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"
LIBRARY_FILE = "prompt_library.json"

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def validate_environment():
    cmd = sys.argv[1] if len(sys.argv) >= 2 else None

    api_required = {"test", "compare"}
    if cmd in api_required:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or not api_key.strip():
            console.print("[red]Error:[/red] OPENAI_API_KEY is not set. Please set it in your environment or .env file.")
            sys.exit(1)

    file_args = []
    if cmd == "add" and len(sys.argv) >= 4:
        file_args.append(sys.argv[3])

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

def save_library(lib: dict):
    with open(LIBRARY_FILE, "w") as f:
        json.dump(lib, f, indent=2)

def cmd_add(name: str, prompt_text: str, description: str = "", tags: list = None):
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

def cmd_list():
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

def cmd_show(name: str):
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

def cmd_test(name: str, test_input: str):
    lib = load_library()
    if name not in lib["prompts"]:
        console.print(f"[red]Prompt not found:[/red] {name}"); return
    entry = lib["prompts"][name]
    current_hash = entry["current_version"]
    version = next((v for v in entry["versions"] if v["hash"] == current_hash), None)
    if not version:
        console.print("[red]Current version not found.[/red]"); return

    prompt = version["prompt"]
    with console.status(f"[bold green]Testing prompt '{name}'...[/bold green]"):
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": f"{prompt}\n\nInput: {test_input}"}],
            temperature=0.3,
        )
    output = response.choices[0].message.content
    console.print(Panel(output, title=f"[bold green]Output ({name} v{current_hash})[/bold green]", border_style="green"))

    version["test_results"].append({"input": test_input, "output": output, "tested_at": datetime.now().isoformat()})
    save_library(lib)

def cmd_compare(name: str, input_text: str):
    """Run the same input against all versions of a prompt and compare."""
    lib = load_library()
    if name not in lib["prompts"]:
        console.print(f"[red]Prompt not found:[/red] {name}"); return
    versions = lib["prompts"][name]["versions"]
    if len(versions) < 2:
        console.print("[yellow]Need at least 2 versions to compare.[/yellow]"); return

    outputs = []
    for v in versions:
        with console.status(f"[bold green]Testing v{v['hash']}...[/bold green]"):
            r = get_client().chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": f"{v['prompt']}\n\nInput: {input_text}"}],
                temperature=0.1,
            )
        outputs.append((v["hash"], r.choices[0].message.content))

    for h, out in outputs:
        console.print(Panel(out[:500], title=f"[bold]Version {h}[/bold]", border_style="cyan"))
