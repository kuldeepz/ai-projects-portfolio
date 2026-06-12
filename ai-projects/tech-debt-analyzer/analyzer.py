"""
Tech Debt Analyzer
Scans a codebase directory or single file for technical debt indicators,
prioritizes them by impact, and estimates remediation effort.
"""

import os, sys, json
import argparse
from pathlib import Path
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

SCHEMA = {
    "name": "tech_debt_report",
    "description": "Technical debt analysis report",
    "parameters": {
        "type": "object",
        "properties": {
            "overall_debt_score": {"type": "integer", "description": "0=clean, 100=severe debt"},
            "debt_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "enum": ["code_quality", "architecture", "security", "testing", "documentation", "dependencies", "performance"]},
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "description": {"type": "string"},
                        "location": {"type": "string"},
                        "effort_days": {"type": "number", "description": "Estimated remediation effort in dev-days"},
                        "business_impact": {"type": "string"},
                        "remediation": {"type": "string"}
                    },
                    "required": ["category", "severity", "description", "effort_days", "remediation"]
                }
            },
            "total_effort_days": {"type": "number"},
            "quick_wins": {"type": "array", "items": {"type": "string"}, "description": "Items that can be fixed in < 1 day"},
            "summary": {"type": "string"}
        },
        "required": ["overall_debt_score", "debt_items", "total_effort_days", "quick_wins", "summary"]
    }
}

def collect_code(target: str, max_chars: int = 8000) -> str:
    p = Path(target)
    if p.is_file():
        return p.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    snippets = []
    total = 0
    for f in sorted(p.rglob("*.py"))[:20]:
        if "__pycache__" in str(f) or ".venv" in str(f):
            continue
        content = f.read_text(encoding="utf-8", errors="ignore")
        header = f"\n\n# === {f.relative_to(p)} ===\n"
        snippets.append(header + content[:1000])
        total += len(content)
        if total > max_chars:
            break
    return "\n".join(snippets)[:max_chars]

def analyze(code: str, context: str = "") -> dict:
    ctx = f"\nContext: {context}" if context else ""
    with console.status("[bold green]Analyzing technical debt with AI..."):
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a senior software architect specializing in code quality and technical debt. "
                    "Identify all forms of technical debt: code smells, missing tests, poor architecture, "
                    "outdated dependencies, security vulnerabilities, and documentation gaps. "
                    "Provide realistic remediation effort estimates in dev-days."
                )},
                {"role": "user", "content": f"Analyze this code for technical debt:{ctx}\n\n```\n{code}\n```"}
            ],
            tools=[{"type": "function", "function": SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "tech_debt_report"}},
            temperature=0.2,
        )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

SEV_COLORS = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim"}
CAT_ICONS = {"code_quality": "📝", "architecture": "🏗", "security": "🔐", "testing": "🧪",
             "documentation": "📚", "dependencies": "📦", "performance": "⚡"}

def display(report: dict):
    score = report["overall_debt_score"]
    s_color = "green" if score < 30 else "yellow" if score < 60 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]Technical Debt Analysis[/bold]\n"
        f"Debt Score: [{s_color} bold]{score}/100[/{s_color} bold]  "
        f"[dim]Total Effort: {report['total_effort_days']} dev-days[/dim]",
        title="[bold cyan]Tech Debt Report[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{report['summary']}[/italic]", title="Summary", border_style="dim"))

    t = Table(show_header=True, header_style="bold", show_lines=True)
    t.add_column("Cat", width=6); t.add_column("Severity", width=10)
    t.add_column("Issue", ratio=3); t.add_column("Effort", width=7); t.add_column("Fix", ratio=2)
    for item in sorted(report["debt_items"], key=lambda x: ["critical","high","medium","low"].index(x["severity"])):
        c = SEV_COLORS.get(item["severity"], "white")
        icon = CAT_ICONS.get(item["category"], "•")
        t.add_row(icon, f"[{c}]{item['severity']}[/{c}]",
                  item["description"][:80], f"{item['effort_days']}d", item["remediation"][:60])
    console.print(Panel(t, title="[bold]Debt Items[/bold]", border_style="red"))

    if report["quick_wins"]:
        console.print(Panel(
            "\n".join(f"  [green]⚡[/green] {q}" for q in report["quick_wins"]),
            title="[bold green]Quick Wins (< 1 day)[/bold green]", border_style="green"
        ))
    console.print()

def validate_environment(argv):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Error:[/red] OPENAI_API_KEY is not set. Please configure it in your environment or .env file.")
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Analyze Python code for technical debt")
    parser.add_argument("target", help="Path to file or directory")
    parser.add_argument("--context", default="", help="Optional project context")
    parser.add_argument("--out", default=None, help="Optional output path for JSON report")
    return parser.parse_args(argv)

def main(argv=None):
    args = validate_environment(argv if argv is not None else sys.argv[1:])

    with console.status("[bold cyan]Collecting code..."):
        code = collect_code(args.target)

    report = analyze(code, args.context)
    display(report)

    out_path = Path(args.out) if args.out else Path(f"tech_debt_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    with console.status("[bold cyan]Writing report..."):
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    console.print(f"[green]Saved report to[/green] {out_path}")

if __name__ == "__main__":
    main()
