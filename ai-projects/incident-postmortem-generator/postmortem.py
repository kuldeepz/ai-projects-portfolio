"""
Incident Post-Mortem Generator
Takes an incident timeline + impact description and generates a structured
blameless post-mortem with root cause analysis and action items.
"""

import os, sys, json, time
from datetime import date
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"
VERBOSE = False

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Setup error:[/red] OPENAI_API_KEY is not set. Please set it in your environment or .env file.")
        sys.exit(1)

    args = [a for a in sys.argv[1:] if a not in ("--verbose", "-v")]
    for path in args:
        if not os.path.exists(path):
            console.print(f"[red]Setup error:[/red] File not found: {path}")
            sys.exit(1)
        if not os.path.isfile(path):
            console.print(f"[red]Setup error:[/red] Not a file: {path}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"[red]Setup error:[/red] File is not readable: {path}")
            sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")

SCHEMA = {
    "name": "postmortem",
    "description": "Blameless post-mortem document",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "severity": {"type": "string", "enum": ["P1", "P2", "P3", "P4"]},
            "executive_summary": {"type": "string"},
            "impact_statement": {"type": "string", "description": "Who was affected and how"},
            "timeline": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"time": {"type": "string"}, "event": {"type": "string"}, "actor": {"type": "string"}},
                          "required": ["time", "event"]}
            },
            "root_causes": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"cause": {"type": "string"}, "type": {"type": "string", "enum": ["immediate", "contributing", "systemic"]}},
                          "required": ["cause", "type"]}
            },
            "contributing_factors": {"type": "array", "items": {"type": "string"}},
            "what_went_well": {"type": "array", "items": {"type": "string"}},
            "what_went_poorly": {"type": "array", "items": {"type": "string"}},
            "action_items": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"action": {"type": "string"}, "owner": {"type": "string"},
                                         "priority": {"type": "string", "enum": ["immediate", "short_term", "long_term"]},
                                         "due": {"type": "string"}},
                          "required": ["action", "owner", "priority"]}
            },
            "full_markdown": {"type": "string"}
        },
        "required": ["title", "severity", "executive_summary", "impact_statement",
                     "root_causes", "what_went_well", "what_went_poorly", "action_items", "full_markdown"]
    }
}

SAMPLE_INCIDENT = {
    "incident_id": "INC-2024-089",
    "date": "2024-06-10",
    "product": "Customer Portal API",
    "reported_by": "On-call engineer (Sarah)",
    "duration": "3 hours 20 minutes",
    "description": (
        "The customer portal API became unavailable at 14:32 UTC. "
        "All API calls returned 503. Investigation revealed the Redis cache cluster ran out of memory "
        "due to a missing TTL on session keys introduced in the v2.4.0 deployment at 13:00 UTC. "
        "The cache filled up completely, causing the app to fail on every request that needed session data. "
        "The team noticed alerts at 14:35 UTC but initial triage pointed to the database. "
        "Root cause was identified at 16:45 UTC. Redis was restarted and TTL fix was deployed at 17:52 UTC."
    ),
    "impact": "~4,200 users unable to log in. 3 enterprise clients affected. Est. $18,000 revenue impact.",
    "responders": ["Sarah (on-call)", "Raj (backend)", "Lisa (DevOps)", "Mike (engineering manager)"]
}

def generate_postmortem(incident: dict) -> dict:
    user_content = f"Write a post-mortem for this incident:\n\n{json.dumps(incident, indent=2)}"
    messages = [
        {"role": "system", "content": (
            "You are an SRE lead writing a blameless post-mortem. "
            "Focus on systemic issues, not individuals. Use the 5-Whys approach for root cause. "
            "Action items must be specific, assigned, and prioritized. "
            "The document should prevent recurrence, not assign blame."
        )},
        {"role": "user", "content": user_content}
    ]
    if VERBOSE:
        total_chars = sum(len(m["content"]) for m in messages)
        approx_tokens = total_chars // 4
        console.print(f"[dim]Model:[/dim] {MODEL}")
        console.print(f"[dim]Input size:[/dim] {total_chars} chars (~{approx_tokens} tokens)")
        console.print("⏳ Calling OpenAI API...")
    started = time.time()
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=messages,
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "postmortem"}},
        temperature=0.3,
    )
    if VERBOSE:
        elapsed = time.time() - started
        console.print(f"✅ Done in {elapsed:.1f}s")
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(pm: dict):
    sev_color = {"P1": "bold red", "P2": "red", "P3": "yellow", "P4": "dim"}.get(pm["severity"], "white")
    console.print()
    console.print(Panel.fit(
        f"[bold]{pm['title']}[/bold]\n"
        f"Severity: [{sev_color}]{pm['severity']}[/{sev_color}]",
        title="[bold cyan]Incident Post-Mortem[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(Markdown(pm["full_markdown"]), title="[bold]Full Post-Mortem[/bold]",
                        border_style="dim", padding=(1, 2)))

    out = f"postmortem_{date.today().isoformat()}.md"
    with open(out, "w") as f:
        f.write(pm["full_markdown"])
    console.print(f"\n[green]Saved:[/green] {out}\n")

def main():
    global VERBOSE
    validate_environment()
    args = [a for a in sys.argv[1:] if a not in ("--verbose", "-v")]
    VERBOSE = any(a in ("--verbose", "-v") for a in sys.argv[1:])

    if len(args) < 1:
        console.print("[dim]No file provided — using sample incident...[/dim]\n")
        incident = SAMPLE_INCIDENT
    else:
        with open(args[0]) as f:
            incident = json.load(f)

    with console.status("[bold green]Generating post-mortem...[/bold green]"):
        pm = generate_postmortem(incident)
    display(pm)

if __name__ == "__main__":
    main()
