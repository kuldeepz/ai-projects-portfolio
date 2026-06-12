"""
Architecture Review Agent
Reviews system architecture documents or design descriptions and flags risks,
single points of failure, scalability concerns, and security gaps.
"""

import os, sys, json
import time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def print_usage(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for i in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if i < len(delays):
                    time.sleep(delays[i])
                else:
                    raise last_exc
    return wrapper

SCHEMA = {
    "name": "architecture_review",
    "description": "Structured architecture review",
    "parameters": {
        "type": "object",
        "properties": {
            "architecture_type": {"type": "string", "description": "Detected pattern (microservices, monolith, event-driven, etc.)"},
            "overall_score": {"type": "integer", "description": "Architecture quality score 0-100"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk": {"type": "string"},
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "mitigation": {"type": "string"},
                        "category": {"type": "string", "enum": ["scalability", "security", "reliability", "performance", "maintainability", "cost"]}
                    },
                    "required": ["risk", "severity", "mitigation", "category"]
                }
            },
            "single_points_of_failure": {"type": "array", "items": {"type": "string"}},
            "well_architected_gaps": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"pillar": {"type": "string"}, "gap": {"type": "string"}, "recommendation": {"type": "string"}},
                          "required": ["pillar", "gap", "recommendation"]}
            },
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"}
        },
        "required": ["architecture_type", "overall_score", "strengths", "risks",
                     "single_points_of_failure", "well_architected_gaps", "recommendations", "summary"]
    }
}

SAMPLE_DESIGN = """
# System Architecture: E-Commerce Platform

## Overview
A monolithic Django application deployed on a single EC2 instance (t3.medium).
MySQL database hosted on the same server.

## Components
- Django app: handles web, API, background jobs (Celery), and admin
- MySQL 5.7: primary database (no replication, no backups configured)
- Redis: session store and Celery broker (same EC2 instance)
- Nginx: reverse proxy on same server
- File storage: local disk /var/uploads

## Deployment
- Single EC2 t3.medium in us-east-1a only
- Manual deployments via SSH
- No staging environment
- Secrets stored in .env file on server

## Scale
- Current: 500 daily active users
- Target: 50,000 daily active users in 12 months
"""

SEV_COLORS = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim"}

@retry_with_backoff
def review_architecture(design: str) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are a Principal Solutions Architect and AWS/Azure expert. "
                "Review system architectures against the Well-Architected Framework (reliability, security, "
                "performance efficiency, cost optimization, operational excellence, sustainability). "
                "Be specific about risks and provide concrete mitigation strategies."
            )},
            {"role": "user", "content": f"Review this system architecture:\n\n{design}"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "architecture_review"}},
        temperature=0.2,
    )
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(review: dict):
    score = review["overall_score"]
    s_color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]Architecture: {review['architecture_type']}[/bold]\n"
        f"Score: [{s_color} bold]{score}/100[/{s_color} bold]",
        title="[bold cyan]Architecture Review[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{review['summary']}[/italic]", title="Summary", border_style="dim"))

    if review["strengths"]:
        console.print(Panel("\n".join(f"  [green]✔[/green] {s}" for s in review["strengths"]),
                            title="[bold green]Strengths[/bold green]", border_style="green"))

    if review["single_points_of_failure"]:
        console.print(Panel("\n".join(f"  [bold red]⚡ SPOF:[/bold red] {s}" for s in review["single_points_of_failure"]),
                            title="[bold red]Single Points of Failure[/bold red]", border_style="red"))

    t = Table(show_header=True, header_style="bold")
    t.add_column("Severity", width=10); t.add_column("Category", width=15)
    t.add_column("Risk", ratio=2); t.add_column("Mitigation", ratio=2)
    for r in review["risks"]:
        c = SEV_COLORS.get(r["severity"], "white")
        t.add_row(f"[{c}]{r['severity'].upper()}[/{c}]", r["category"], r["risk"], r["mitigation"])
    console.print(Panel(t, title="[bold red]Risks[/bold red]", border_style="red"))

    if review["well_architected_gaps"]:
        wt = Table(show_header=True, header_style="bold magenta")
        wt.add_column("Pillar"); wt.add_column("Gap", ratio=2); wt.add_column("Recommendation", ratio=2)
        for g in review["well_architected_gaps"]:
            wt.add_row(g["pillar"], g["gap"], g["recommendation"])
        console.print(Panel(wt, title="[bold]Well-Architected Framework Gaps[/bold]", border_style="magenta"))

    console.print(Panel("\n".join(f"  [cyan]→[/cyan] {r}" for r in review["recommendations"]),
                        title="[bold]Recommendations[/bold]", border_style="blue"))
    console.print()

def main():
    if len(sys.argv) < 2:
        console.print("[dim]No file provided — reviewing sample architecture...[/dim]\n")
        design = SAMPLE_DESIGN
    else:
        with open(sys.argv[1]) as f:
            design = f.read()

    with console.status("[bold green]Reviewing architecture...[/bold green]"):
        review = review_architecture(design)
    display(review)

if __name__ == "__main__":
    main()
