"""
AI Code Reviewer
Submit code via file or stdin — get a detailed review covering correctness,
security vulnerabilities, performance, and best practices.
"""

import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text

load_dotenv()

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client
console = Console()

CHAT_MODEL = "gpt-4o-mini"

REVIEW_SCHEMA = {
    "name": "code_review",
    "description": "Structured code review with findings across multiple categories",
    "parameters": {
        "type": "object",
        "properties": {
            "language": {"type": "string", "description": "Detected programming language"},
            "overall_score": {"type": "integer", "description": "Code quality score 1-100"},
            "summary": {"type": "string", "description": "2-3 sentence high-level assessment"},
            "security_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "issue": {"type": "string"},
                        "fix": {"type": "string"}
                    },
                    "required": ["severity", "issue", "fix"]
                }
            },
            "bugs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "issue": {"type": "string"},
                        "fix": {"type": "string"}
                    },
                    "required": ["severity", "issue", "fix"]
                }
            },
            "performance_issues": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "fix": {"type": "string"}
                    },
                    "required": ["issue", "fix"]
                }
            },
            "best_practice_violations": {
                "type": "array",
                "items": {"type": "string"}
            },
            "positive_aspects": {
                "type": "array",
                "items": {"type": "string"}
            },
            "refactored_snippet": {
                "type": "string",
                "description": "If there are critical issues, provide a corrected version of the most problematic section"
            }
        },
        "required": [
            "language", "overall_score", "summary",
            "security_issues", "bugs", "performance_issues",
            "best_practice_violations", "positive_aspects"
        ]
    }
}

SEVERITY_COLORS = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim yellow"
}

SEVERITY_ICONS = {
    "critical": "🔴",
    "high": "🟠",
    "medium": "🟡",
    "low": "🔵"
}


def detect_language(file_path: str) -> str:
    ext_map = {
        ".py": "python", ".js": "javascript", ".ts": "typescript",
        ".go": "go", ".java": "java", ".rs": "rust", ".cpp": "cpp",
        ".c": "c", ".rb": "ruby", ".php": "php", ".cs": "csharp",
        ".sh": "bash", ".sql": "sql",
    }
    if file_path:
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, "")
    return ""


def review_code(code: str, language: str = "", context: str = "") -> dict:
    lang_hint = f"Language: {language}\n" if language else ""
    ctx_hint = f"Context: {context}\n" if context else ""

    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a senior software engineer conducting a thorough code review. "
                    "Review for: security vulnerabilities (SQL injection, XSS, secrets in code, etc.), "
                    "logic bugs, performance inefficiencies, and best practice violations. "
                    "Be specific — point to the exact pattern or line causing each issue. "
                    "For refactored_snippet, only include it if there are critical/high severity issues."
                )
            },
            {
                "role": "user",
                "content": f"{lang_hint}{ctx_hint}\nCode to review:\n```\n{code}\n```"
            }
        ],
        tools=[{"type": "function", "function": REVIEW_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "code_review"}},
        temperature=0.2,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)


def severity_label(severity: str) -> Text:
    icon = SEVERITY_ICONS.get(severity, "")
    text = Text(f"{icon} {severity.upper()}")
    text.stylize(SEVERITY_COLORS.get(severity, "white"))
    return text


def display_review(review: dict, code: str, language: str):
    detected_lang = review.get("language", language or "unknown")
    score = review["overall_score"]
    score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"

    console.print()
    console.print(Panel.fit(
        f"[bold white]Code Review Report[/bold white]\n"
        f"[dim]Language: {detected_lang}[/dim]\n"
        f"Score: [{score_color} bold]{score}/100[/{score_color} bold]",
        border_style="cyan"
    ))

    # Summary
    console.print(Panel(
        f"[italic]{review['summary']}[/italic]",
        title="[bold]Summary[/bold]", border_style="dim"
    ))

    # Security issues
    if review["security_issues"]:
        table = Table(show_header=True, header_style="bold red")
        table.add_column("Severity", width=10)
        table.add_column("Issue")
        table.add_column("Fix", style="green")
        for item in review["security_issues"]:
            table.add_row(severity_label(item["severity"]), item["issue"], item["fix"])
        console.print(Panel(table, title="[bold red]Security Issues[/bold red]", border_style="red"))
    else:
        console.print(Panel("[green]No security issues found.[/green]", title="[bold]Security[/bold]", border_style="green"))

    # Bugs
    if review["bugs"]:
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Severity", width=10)
        table.add_column("Bug")
        table.add_column("Fix", style="green")
        for item in review["bugs"]:
            table.add_row(severity_label(item["severity"]), item["issue"], item["fix"])
        console.print(Panel(table, title="[bold yellow]Bugs[/bold yellow]", border_style="yellow"))

    # Performance
    if review["performance_issues"]:
        perf_text = "\n".join(
            f"  [yellow]⚡[/yellow] {p['issue']}\n    [dim]→ {p['fix']}[/dim]"
            for p in review["performance_issues"]
        )
        console.print(Panel(perf_text, title="[bold]Performance[/bold]", border_style="yellow"))

    # Best practices
    if review["best_practice_violations"]:
        bp_text = "\n".join(f"  [dim]•[/dim] {v}" for v in review["best_practice_violations"])
        console.print(Panel(bp_text, title="[bold]Best Practice Violations[/bold]", border_style="dim"))

    # Positives
    if review["positive_aspects"]:
        pos_text = "\n".join(f"  [green]✔[/green] {p}" for p in review["positive_aspects"])
        console.print(Panel(pos_text, title="[bold green]What's Good[/bold green]", border_style="green"))

    # Refactored snippet
    if review.get("refactored_snippet"):
        console.print(Panel(
            Syntax(review["refactored_snippet"], detected_lang.lower(), theme="monokai", line_numbers=True),
            title="[bold cyan]Suggested Fix[/bold cyan]",
            border_style="cyan"
        ))

    console.print()


def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow]")
        console.print("  python reviewer.py <code_file> [context]")
        console.print("  echo 'code' | python reviewer.py - [context]")
        console.print('\n[dim]Example: python reviewer.py app.py "Django REST API view"[/dim]')
        sys.exit(1)

    file_arg = sys.argv[1]
    context = sys.argv[2] if len(sys.argv) > 2 else ""

    if file_arg == "-":
        code = sys.stdin.read()
        language = ""
        display_path = "stdin"
    else:
        if not os.path.exists(file_arg):
            console.print(f"[red]File not found:[/red] {file_arg}")
            sys.exit(1)
        with open(file_arg, "r", encoding="utf-8") as f:
            code = f.read()
        language = detect_language(file_arg)
        display_path = file_arg

    if not code.strip():
        console.print("[red]No code provided.[/red]")
        sys.exit(1)

    if len(code) > 8000:
        console.print("[yellow]Note: Code truncated to 8000 chars for review.[/yellow]")
        code = code[:8000]

    console.print(f"\n[cyan]Reviewing:[/cyan] {display_path}")
    if context:
        console.print(f"[cyan]Context:[/cyan] {context}")

    with console.status("[bold green]Reviewing code with GPT-4o-mini...[/bold green]"):
        review = review_code(code, language, context)

    display_review(review, code, language)


if __name__ == "__main__":
    main()
