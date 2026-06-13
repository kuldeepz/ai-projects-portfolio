"""
Tech Debt Analyzer
Scans a codebase directory or single file for technical debt indicators,
prioritizes them by impact, and estimates remediation effort.
"""

import os, sys, json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Any
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console: Console = Console()
MODEL: str = "gpt-4o-mini"
VERBOSE: bool = False

_client: OpenAI | None = None
def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def print_usage(response: Any) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

SCHEMA: dict[str, Any] = {
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
    snippets: list[str] = []
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

def analyze(code: str, context: str = "") -> dict[str, Any]:
    ctx = f"\nContext: {context}" if context else ""
    user_content = f"Analyze this code for technical debt:{ctx}\n\n```\n{code}\n```"
    if VERBOSE:
        console.print(f"[dim]Model:[/dim] {MODEL}")
        console.print(f"[dim]Input chars:[/dim] {len(user_content)}")
        console.print(f"[dim]Estimated input tokens:[/dim] {max(1, len(user_content) // 4)}")
        console.print("⏳ Calling OpenAI API...")
    start = datetime.now()
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
                {"role": "user", "content": user_content}
            ],
            tools=[{"type": "function", "function": SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "tech_debt_report"}},
            temperature=0.2,
        )
    print_usage(response)
    if VERBOSE:
        elapsed = (datetime.now() - start).total_seconds()
        console.print(f"✅ Done in {elapsed:.1f}s")
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

SEV_COLORS: dict[str, str] = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim"}
CAT_ICONS: dict[str, str] = {"code_quality": "📝", "architecture": "🏗", "security": "🔐", "testing": "🧪",
             "documentation": "📚", "dependencies": "📦", "performance": "⚡"}

def display(report: dict[str, Any]) -> None:
    score = report["overall_debt_score"]
    s_color = "green" if score < 30 else "yellow" if score < 60 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]Technical Debt Analysis[/bold]\n"
        f"Debt Score: [{s_color} bold]{score}/100[/{s_color} bold]  "
        f"[dim]Total Effort: {report['total_effort_days']} dev-days[/dim]",
        title="[bold cyan]Tech Debt Report[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{report['summary']}[/italic]", title="Summary", border_style="blue"))


def _build_fake_response() -> Any:
    class _Fn:
        arguments = json.dumps({
            "overall_debt_score": 10,
            "debt_items": [],
            "total_effort_days": 0,
            "quick_wins": [],
            "summary": "ok"
        })

    class _ToolCall:
        function = _Fn()

    class _Message:
        tool_calls = [_ToolCall()]

    class _Choice:
        message = _Message()

    class _Usage:
        prompt_tokens = 1
        completion_tokens = 1
        total_tokens = 2

    class _Response:
        choices = [_Choice()]
        usage = _Usage()

    return _Response()


def _test_analyze_verbose_toggle() -> None:
    global VERBOSE

    class _FakeCompletions:
        @staticmethod
        def create(**kwargs: Any) -> Any:
            return _build_fake_response()

    class _FakeChat:
        completions = _FakeCompletions()

    class _FakeClient:
        chat = _FakeChat()

    class _Status:
        def __enter__(self) -> None:
            return None

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    class _FakeConsole:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def print(self, *args: Any, **kwargs: Any) -> None:
            self.calls.append(" ".join(str(a) for a in args))

        def status(self, *args: Any, **kwargs: Any) -> _Status:
            return _Status()

    old_console = console
    old_client = _client

    try:
        fake_console = _FakeConsole()
        globals()["console"] = fake_console
        globals()["_client"] = _FakeClient()

        VERBOSE = False
        analyze("print('x')")
        assert not any("Model:" in c or "Input chars:" in c or "Estimated input tokens:" in c or "Calling OpenAI API" in c or "✅ Done" in c for c in fake_console.calls)

        fake_console.calls.clear()
        VERBOSE = True
        analyze("print('x')")
        assert any("Model:" in c for c in fake_console.calls)
        assert any("Input chars:" in c for c in fake_console.calls)
        assert any("Estimated input tokens:" in c for c in fake_console.calls)
        assert any("Calling OpenAI API" in c for c in fake_console.calls)
        assert any("✅ Done" in c for c in fake_console.calls)
    finally:
        globals()["console"] = old_console
        globals()["_client"] = old_client
        VERBOSE = False


if __name__ == "__main__" and os.getenv("TECH_DEBT_ANALYZER_RUN_TESTS") == "1":
    _test_analyze_verbose_toggle()
