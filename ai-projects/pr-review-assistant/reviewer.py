"""
PR Review Assistant
Takes a git diff (or two file versions) and generates detailed PR review comments
categorized by severity — ready to paste into GitHub/ADO PR.
"""

import os, sys, json, subprocess, time, random
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

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

def retry_with_backoff(func=None, *, retries=3, base_delay=1.0, max_delay=8.0, jitter=0.2):
    def deco(f):
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(retries):
                try:
                    return f(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == retries - 1:
                        break
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    delay *= 1 + random.uniform(-jitter, jitter)
                    time.sleep(max(0, delay))
            raise last_exception
        return wrapper
    return deco(func) if func else deco

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
    prompt = f"Review this PR diff:{ctx}\n\n```diff\n{diff}\n```"
    if VERBOSE:
        console.print(f"[dim]Model:[/dim] {MODEL}")
        console.print(f"[dim]Input size:[/dim] {len(prompt)} chars")
    with console.status("[bold green]Processing..."):
        if VERBOSE:
            console.print("⏳ Calling OpenAI API...")
        started = time.time()
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a senior software engineer doing a thorough PR review. "
                    "Check for correctness, security vulnerabilities, performance issues, "
                    "readability, test coverage, and design problems. "
                    "Write comments as you would in a real PR — specific, constructive, and actionable."
                )},
                {"role": "user", "content": prompt}
            ],
            tools=[{"type": "function", "function": SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "pr_review"}},
            temperature=0.2,
        )
        if VERBOSE:
            console.print(f"✅ Done in {time.time() - started:.1f}s")
            if hasattr(response, "model"):
                console.print(f"[dim]Response model:[/dim] {response.model}")
            if hasattr(response, "usage") and response.usage is not None:
                console.print(f"[dim]Usage:[/dim] {response.usage}")

    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None) or []
    if VERBOSE:
        console.print(f"[dim]Tool calls:[/dim] {len(tool_calls)}")
    if not tool_calls:
        raise ValueError("Model response did not include any tool calls")

    return json.loads(tool_calls[0].function.arguments)

def display(review: dict):
    verdict = review["overall_verdict"]
    v_color = VERDICT_COLORS[verdict]
    v_icon = VERDICT_ICONS[verdict]
    console.print()
    console
