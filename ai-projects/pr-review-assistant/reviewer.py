"""
PR Review Assistant
Takes a git diff (or two file versions) and generates detailed PR review comments
categorized by severity — ready to paste into GitHub/ADO PR.
"""

import os, sys, json, subprocess
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

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

SCHEMA = {
    "name": "pr_review",
    "description": "Structured PR review with categorized comments",
    "parameters": {
        "type": "object",
        "properties": {
            "overall_verdict": {"type": "string", "enum": ["approve", "approve_with_comments", "request_changes", "needs_discussion"]},
            "summary": {"type": "string", "description": "2-3 sentence PR overview"},
            "comments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["blocking", "major", "minor", "nit", "praise"]},
                        "category": {"type": "string", "enum": ["correctness", "security", "performance", "readability", "testing", "design", "docs"]},
                        "file": {"type": "string"},
                        "comment": {"type": "string"},
                        "suggestion": {"type": "string"}
                    },
                    "required": ["severity", "category", "comment"]
                }
            },
            "positives": {"type": "array", "items": {"type": "string"}},
            "checklist": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"item": {"type": "string"}, "status": {"type": "string", "enum": ["pass", "fail", "na"]}},
                          "required": ["item", "status"]}
            }
        },
        "required": ["overall_verdict", "summary", "comments", "positives", "checklist"]
    }
}

SAMPLE_DIFF = """
diff --git a/src/auth/login.py b/src/auth/login.py
--- a/src/auth/login.py
+++ b/src/auth/login.py
@@ -12,8 +12,21 @@
 from db import get_connection

-def authenticate(username, password):
-    conn = get_connection()
-    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
-    result = conn.execute(query)
-    return result.fetchone()
+def authenticate(username: str, password: str) -> dict | None:
+    conn = get_connection()
+    # TODO: remove debug line before merge
+    print(f"Login attempt: {username} / {password}")
+    query = f"SELECT * FROM users WHERE username='{username}'"
+    result = conn.execute(query)
+    user = result.fetchone()
+    if user and user['password'] == password:
+        return user
+    return None

+def reset_password(email):
+    user = get_user_by_email(email)
+    new_password = "temp1234"
+    update_password(user['id'], new_password)
+    send_email(email, f"Your new password is: {new_password}")
"""

VERDICT_COLORS = {
    "approve": "green", "approve_with_comments": "yellow",
    "request_changes": "red", "needs_discussion": "magenta"
}
VERDICT_ICONS = {
    "approve": "✅", "approve_with_comments": "💬",
    "request_changes": "🚫", "needs_discussion": "❓"
}
SEV_COLORS = {"blocking": "bold red", "major": "red", "minor": "yellow", "nit": "dim", "praise": "green"}

def review_diff(diff: str, context: str = "") -> dict:
    ctx = f"\nContext: {context}" if context else ""
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are a senior software engineer doing a thorough PR review. "
                "Check for correctness, security vulnerabilities, performance issues, "
                "readability, test coverage, and design problems. "
                "Write comments as you would in a real PR — specific, constructive, and actionable."
            )},
            {"role": "user", "content": f"Review this PR diff:{ctx}\n\n```diff\n{diff}\n```"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "pr_review"}},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(review: dict):
    verdict = review["overall_verdict"]
    v_color = VERDICT_COLORS[verdict]
    v_icon = VERDICT_ICONS[verdict]
    console.print()
    console.print(Panel.fit(
        f"[{v_color} bold]{v_icon} {verdict.replace('_',' ').title()}[/{v_color} bold]\n"
        f"[dim]{review['summary']}[/dim]",
        title="[bold cyan]PR Review[/bold cyan]", border_style="cyan"
    ))

    for comment in review["comments"]:
        s = comment["severity"]
        color = SEV_COLORS.get(s, "white")
        file_hint = f"[dim]{comment.get('file','')}[/dim]  " if comment.get("file") else ""
        body = f"{file_hint}[{color}]{s.upper()}[/{color}] [{comment['category']}]\n\n{comment['comment']}"
        if comment.get("suggestion"):
            body += f"\n\n[dim]Suggestion:[/dim] [green]{comment['suggestion']}[/green]"
        console.print(Panel(body, border_style=s if s in ("blocking", "major") else "dim"))

    if review["positives"]:
        console.print(Panel("\n".join(f"  [green]✔[/green] {p}" for p in review["positives"]),
                            title="[bold green]What's Good[/bold green]", border_style="green"))

    if review["checklist"]:
        t = Table(show_header=False, box=None, padding=(0, 2))
        t.add_column(width=3); t.add_column()
        for item in review["checklist"]:
            icon = {"pass": "[green]✔[/green]", "fail": "[red]✘[/red]", "na": "[dim]—[/dim]"}[item["status"]]
            t.add_row(icon, item["item"])
        console.print(Panel(t, title="[bold]Review Checklist[/bold]", border_style="dim"))
    console.print()

def main():
    if len(sys.argv) < 2:
        console.print("[dim]No diff provided — reviewing sample diff...[/dim]\n")
        diff = SAMPLE_DIFF
        context = "Authentication module refactor"
    elif sys.argv[1] == "-":
        diff = sys.stdin.read()
        context = sys.argv[2] if len(sys.argv) > 2 else ""
    else:
        with open(sys.argv[1]) as f:
            diff = f.read()
        context = sys.argv[2] if len(sys.argv) > 2 else ""

    with console.status("[bold green]Reviewing PR...[/bold green]"):
        review = review_diff(diff, context)
    display(review)

if __name__ == "__main__":
    main()
