"""
ADO Work Item Analyzer
Reads Azure DevOps work items (from JSON export or typed input) and:
- Flags missing/incomplete acceptance criteria
- Scores definition-of-ready completeness
- Suggests improvements to the work item
"""

import os, sys, json
from datetime import datetime
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
    usage = response.usage
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

SCHEMA = {
    "name": "workitem_analysis",
    "description": "Analysis of an ADO work item for completeness and quality",
    "parameters": {
        "type": "object",
        "properties": {
            "ready_score": {"type": "integer", "description": "Definition-of-Ready score 0-100"},
            "missing_fields": {"type": "array", "items": {"type": "string"}, "description": "Fields that are absent or empty"},
            "acceptance_criteria_issues": {"type": "array", "items": {"type": "string"}, "description": "Problems with acceptance criteria"},
            "improved_acceptance_criteria": {"type": "string", "description": "Rewritten acceptance criteria in Given/When/Then BDD format"},
            "story_point_suggestion": {"type": "integer", "description": "Suggested story point estimate (Fibonacci: 1,2,3,5,8,13)"},
            "risks": {"type": "array", "items": {"type": "string"}, "description": "Risks or dependencies flagged"},
            "suggestions": {"type": "array", "items": {"type": "string"}, "description": "Actionable improvements to the work item"},
            "summary": {"type": "string"}
        },
        "required": ["ready_score", "missing_fields", "acceptance_criteria_issues",
                     "improved_acceptance_criteria", "story_point_suggestion", "risks", "suggestions", "summary"]
    }
}

SAMPLE_WORK_ITEM = {
    "id": "WI-1042",
    "type": "User Story",
    "title": "As a user I want to login",
    "description": "User should be able to login to the application",
    "acceptance_criteria": "Login works",
    "story_points": None,
    "priority": "Medium",
    "assigned_to": "",
    "sprint": "Sprint 14",
    "tags": []
}

def analyze_workitem(item: dict) -> dict:
    with console.status("[bold green]Calling OpenAI for analysis...[/bold green]"):
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a senior Agile coach and BA reviewing Azure DevOps work items. "
                    "Evaluate completeness, flag issues with acceptance criteria, and rewrite "
                    "acceptance criteria in Given/When/Then BDD format. Be specific and actionable."
                )},
                {"role": "user", "content": f"Analyze this work item:\n\n{json.dumps(item, indent=2)}"}
            ],
            tools=[{"type": "function", "function": SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "workitem_analysis"}},
            temperature=0.2,
        )
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(item: dict, analysis: dict):
    score = analysis["ready_score"]
    color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]{item.get('id','?')} — {item.get('title','?')}[/bold]\n"
        f"[dim]{item.get('type','?')} · {item.get('sprint','')}[/dim]\n"
        f"Ready Score: [{color} bold]{score}/100[/{color} bold]",
        title="[bold cyan]ADO Work Item Analysis[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{analysis['summary']}[/italic]", title="Summary", border_style="dim"))

    if analysis["missing_fields"]:
        console.print(Panel("\n".join(f"  [red]✘[/red] {f}" for f in analysis["missing_fields"]),
                            title="[bold red]Missing Fields[/bold red]", border_style="red"))

    if analysis["acceptance_criteria_issues"]:
        console.print(Panel("\n".join(f"  [yellow]⚠[/yellow] {i}" for i in analysis["acceptance_criteria_issues"]),
                            title="[bold yellow]AC Issues[/bold yellow]", border_style="yellow"))

    console.print(Panel(
        f"[green]{analysis['improved_acceptance_criteria']}[/green]",
        title="[bold green]Improved Acceptance Criteria (BDD)[/bold green]", border_style="green"
    ))

    t = Table(show_header=False, box=None, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    t.add_row("Suggested Story Points", f"[bold]{analysis['story_point_suggestion']}[/bold]")
    console.print(Panel(t, title="Estimation", border_style="dim"))

    if analysis["risks"]:
        console.print(Panel("\n".join(f"  [red]⚡[/red] {r}" for r in analysis["risks"]),
                            title="[bold]Risks & Dependencies[/bold]", border_style="red"))

    console.print(Panel("\n".join(f"  [cyan]→[/cyan] {s}" for s in analysis["suggestions"]),
                        title="[bold]Improvement Suggestions[/bold]", border_style="blue"))
    console.print()

def main():
    export = False
    args = sys.argv[1:]
    if "--export" in args:
        export = True
        args.remove("--export")
    if "-e" in args:
        export = True
        args.remove("-e")

    if len(args) < 1:
        console.print("[yellow]Usage:[/yellow] python analyzer.py [--export|-e] '<work item json>' OR path/to/workitem.json")
        console.print("[dim]No input provided; using sample work item.[/dim]")
        item = SAMPLE_WORK_ITEM
    else:
        raw = args[0]
        if os.path.exists(raw):
            with open(raw, "r", encoding="utf-8") as f:
                item = json.load(f)
        else:
            item = json.loads(raw)

    analysis = analyze_workitem(item)
    display(item, analysis)

    if export:
        payload = {
            "work_item": item,
            "analysis": analysis,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }
        out_file = f"workitem-analysis-{item.get('id', 'unknown')}.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        console.print(f"[green]Exported analysis to {out_file}[/green]")

if __name__ == "__main__":
    main()
