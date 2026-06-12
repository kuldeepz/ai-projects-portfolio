"""
ADO Release Notes Generator
Takes a list of ADO work items (completed in a sprint/release) and generates
polished, audience-appropriate release notes.
"""

import os, sys, json
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Error:[/red] OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
        sys.exit(1)

    if len(sys.argv) >= 2:
        path = sys.argv[1]
        if not os.path.isfile(path):
            console.print(f"[red]Error:[/red] Input file not found: {path}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"[red]Error:[/red] Input file is not readable: {path}")
            sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")

SCHEMA = {
    "name": "release_notes",
    "description": "Structured release notes for multiple audiences",
    "parameters": {
        "type": "object",
        "properties": {
            "version": {"type": "string"},
            "release_date": {"type": "string"},
            "headline": {"type": "string", "description": "One-line summary of this release"},
            "executive_summary": {"type": "string", "description": "2-3 sentences for non-technical stakeholders"},
            "new_features": {"type": "array", "items": {"type": "string"}},
            "improvements": {"type": "array", "items": {"type": "string"}},
            "bug_fixes": {"type": "array", "items": {"type": "string"}},
            "breaking_changes": {"type": "array", "items": {"type": "string"}},
            "technical_notes": {"type": "array", "items": {"type": "string"}, "description": "Notes for engineering team"},
            "full_markdown": {"type": "string", "description": "Complete formatted markdown release notes"}
        },
        "required": ["version", "headline", "executive_summary", "new_features",
                     "improvements", "bug_fixes", "breaking_changes", "full_markdown"]
    }
}

SAMPLE_ITEMS = {
    "version": "v2.4.0",
    "release_date": str(date.today()),
    "product": "Customer Portal",
    "completed_items": [
        {"id": "US-101", "type": "User Story", "title": "Multi-factor authentication for login", "team": "Security"},
        {"id": "US-102", "type": "User Story", "title": "Dashboard with real-time analytics widgets", "team": "Frontend"},
        {"id": "US-104", "type": "User Story", "title": "Automated email notifications for order updates", "team": "Backend"},
        {"id": "BUG-55", "type": "Bug", "title": "Fixed login redirect loop on mobile Safari", "team": "Frontend"},
        {"id": "BUG-61", "type": "Bug", "title": "Resolved data export timeout for large datasets", "team": "Backend"},
        {"id": "TECH-12", "type": "Tech Debt", "title": "Upgraded React from v16 to v18 for performance", "team": "Frontend"},
        {"id": "US-108", "type": "User Story", "title": "Admin panel for user role management", "team": "Backend"},
    ]
}

def generate_notes(data: dict) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are a technical writer generating release notes for a SaaS product. "
                "Write clearly for multiple audiences: executives need the business impact, "
                "users need plain English feature descriptions, engineers need technical specifics. "
                "Group items by type. Use active voice."
            )},
            {"role": "user", "content": f"Generate release notes for:\n\n{json.dumps(data, indent=2)}"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "release_notes"}},
        temperature=0.4,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def main():
    validate_environment()

    if len(sys.argv) < 2:
        console.print("[dim]No file provided — using sample release data...[/dim]\n")
        data = SAMPLE_ITEMS
    else:
        with open(sys.argv[1]) as f:
            data = json.load(f)

    with console.status("[bold green]Generating release notes...[/bold green]"):
        notes = generate_notes(data)

    console.print()
    console.print(Panel(Markdown(notes["full_markdown"]),
                        title=f"[bold cyan]Release Notes — {notes['version']}[/bold cyan]",
                        border_style="cyan", padding=(1, 2)))

    out = f"release_notes_{notes['version'].replace('.','_')}.md"
    with open(out, "w") as f:
        f.write(notes["full_markdown"])
    console.print(f"\n[green]Saved:[/green] {out}\n")

if __name__ == "__main__":
    main()
