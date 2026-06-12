"""
PR Review Assistant
Takes a git diff (or two file versions) and generates detailed PR review comments
categorized by severity — ready to paste into GitHub/ADO PR.
"""

import os, sys, json, subprocess, time
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

def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exception = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if i < len(delays) - 1:
                    time.sleep(delay)
        raise last_exception
    return wrapper

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

@retry_with_backoff
def review_diff(diff: str, context: str = "") -> dict:
    ctx = f"\nContext: {context}" if context else ""
    with console.status("[bold green]Processing..."):
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


def _run_retry_with_backoff_tests():
    from unittest import mock

    # 1) succeeds first try (no sleep calls)
    success = mock.Mock(return_value="ok")
    wrapped = retry_with_backoff(success)
    with mock.patch("time.sleep") as sleep_mock:
        assert wrapped() == "ok"
        assert success.call_count == 1
        sleep_mock.assert_not_called()

    # 2) fails once then succeeds (one sleep with 1)
    fail_once_then_ok = mock.Mock(side_effect=[Exception("e1"), "ok"])
    wrapped = retry_with_backoff(fail_once_then_ok)
    with mock.patch("time.sleep") as sleep_mock:
        assert wrapped() == "ok"
        assert fail_once_then_ok.call_count == 2
        sleep_mock.assert_called_once_with(1)

    # 3) fails twice then succeeds (sleeps 1,2)
    fail_twice_then_ok = mock.Mock(side_effect=[Exception("e1"), Exception("e2"), "ok"])
    wrapped = retry_with_backoff(fail_twice_then_ok)
    with mock.patch("time.sleep") as sleep_mock:
        assert wrapped() == "ok"
        assert fail_twice_then_ok.call_count == 3
        assert sleep_mock.call_args_list == [mock.call(1), mock.call(2)]

    # 4) fails all attempts (raises last exception, sleeps 1,2)
    last_exc = RuntimeError("final")
    fail_all = mock.Mock(side_effect=[Exception("e1"), Exception("e2"), last_exc])
    wrapped = retry_with_backoff(fail_all)
    with mock.patch("time.sleep") as sleep_mock:
        try:
            wrapped()
            raise AssertionError("Expected RuntimeError was not raised")
        except RuntimeError as e:
            assert e is last_exc
        assert fail_all.call_count == 3
        assert sleep_mock.call_args_list == [mock.call(1), mock.call(2)]

if __name__ == "__main__" and "--test-retry" in sys.argv:
    _run_retry_with_backoff_tests()
