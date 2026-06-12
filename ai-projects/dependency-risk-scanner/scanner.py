"""
Dependency Risk Scanner
Audits requirements.txt / package.json / pyproject.toml for outdated,
deprecated, or vulnerable packages and recommends upgrades.
"""

import os, sys, json, re, time
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

def print_usage(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if i == len(delays) - 1:
                    break
                time.sleep(delay)
        raise last_exc
    return wrapper

SCHEMA = {
    "name": "dependency_report",
    "description": "Dependency risk assessment",
    "parameters": {
        "type": "object",
        "properties": {
            "ecosystem": {"type": "string", "description": "Python/Node.js/etc."},
            "total_packages": {"type": "integer"},
            "risk_summary": {"type": "string"},
            "packages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "current_version": {"type": "string"},
                        "risk": {"type": "string", "enum": ["critical", "high", "medium", "low", "ok"]},
                        "issue": {"type": "string"},
                        "recommendation": {"type": "string"},
                        "upgrade_to": {"type": "string"}
                    },
                    "required": ["name", "current_version", "risk", "issue", "recommendation"]
                }
            },
            "critical_action_required": {"type": "array", "items": {"type": "string"}},
            "upgrade_command": {"type": "string", "description": "Single command to upgrade all recommended packages"}
        },
        "required": ["ecosystem", "total_packages", "risk_summary", "packages", "critical_action_required"]
    }
}

def parse_requirements(content: str, filename: str) -> str:
    return f"File: {filename}\n\n{content}"

@retry_with_backoff
def scan(dep_content: str) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are a security engineer specializing in supply chain security. "
                "Analyze dependency files for: known vulnerabilities (CVEs), deprecated packages, "
                "packages with no recent maintenance, overly broad version pins, and security-sensitive "
                "packages that need careful version management. Use your knowledge of package ecosystems "
                "up to your training cutoff."
            )},
            {"role": "user", "content": f"Scan these dependencies for risks:\n\n{dep_content}"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "dependency_report"}},
        temperature=0.1,
    )
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

RISK_COLORS = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim yellow", "ok": "green"}
RISK_ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🔵", "ok": "✅"}

def display(report: dict):
    counts = {r: sum(1 for p in report["packages"] if p["risk"] == r) for r in ("critical","high","medium","low","ok")}
    console.print()
    console.print(Panel.fit(
        f"[bold]Dependency Risk Scan — {report['ecosystem']}[/bold]\n"
        f"[dim]{report['total_packages']} packages scanned[/dim]  "
        f"[bold red]{counts['critical']} critical[/bold red]  "
        f"[red]{counts['high']} high[/red]  "
        f"[yellow]{counts['medium']} medium[/yellow]  "
        f"[green]{counts['ok']} ok[/green]",
        title="[bold cyan]Dependency Risk Scanner[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{report['risk_summary']}[/italic]", title="Summary", border_style="dim"))

    if report["critical_action_required"]:
        console.print(Panel(
            "\n".join(f"  [bold red]‼[/bold red] {a}" for a in report["critical_action_required"]),
            title="[bold red]Immediate Action Required[/bold red]", border_style="red"
        ))

    filtered = [p for p in report["packages"] if p["risk"] != "ok"]
    if filtered:
        t = Table(show_header=True, header_style="bold")
        t.add_column("Risk", width=10); t.add_column("Package", ratio=1)
        t.add_column("Version", width=12); t.add_column("Issue", ratio=2); t.add_column("Fix", ratio=2)
        for p in sorted(filtered, key=lambda x: ["critical","high","medium","low"].index(x["risk"])):
            c = RISK_COLORS.get(p["risk"], "white")
            icon = RISK_ICONS.get(p["risk"], "")
            upgrade = f"→ {p['upgrade_to']}" if p.get("upgrade_to") else ""
            t.add_row(f"[{c}]{icon} {p['risk']}[/{c}]", p["name"],
                      f"{p['current_version']} {upgrade}", p["issue"][:60], p["recommendation"][:60])
        console.print(Panel(t, title="[bold]Packages Requiring Attention[/bold]", border_style="yellow"))

    if report.get("upgrade_command"):
        console.print(Panel(f"[cyan]{report['upgrade_command']}[/cyan]",
                            title="[bold]Recommended Upgrade Command[/bold]", border_style="dim"))
    console.print()

def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] python scanner.py <requirements.txt|package.json|pyproject.toml>")
        sys.exit(1)
    path = sys.argv[1]
    if not os.path.exists(path):
        console.print(f"[red]Not found:[/red] {path}"); sys.exit(1)
    content = Path(path).read_text(encoding="utf-8")
    dep_content = parse_requirements(content, Path(path).name)

    with console.status("[bold green]Scanning dependencies...[/bold green]"):
        report = scan(dep_content)
    display(report)

if __name__ == "__main__":
    main()
