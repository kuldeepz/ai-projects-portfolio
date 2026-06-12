"""
AI Code Reviewer
Submit code via file or stdin — get a detailed review covering correctness,
security vulnerabilities, performance, and best practices.
"""

import os
import sys
import json
import time
from functools import wraps
from pathlib import Path
from datetime import datetime
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text

load_dotenv()

_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


console: Console = Console()

CHAT_MODEL = "gpt-4o-mini"


def print_usage(response: Any) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", 0) or 0
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")


def retry_with_backoff(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exception = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if attempt < len(delays):
                    time.sleep(delays[attempt])
                else:
                    raise last_exception
    return wrapper


REVIEW_SCHEMA: dict[str, Any] = {
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

SEVERITY_COLORS: dict[str, str] = {
    "critical": "bold red",
    "high": "red",
    "medium": "yellow",
    "low": "dim yellow"
}

SEVERITY_ICONS: dict[str, str] = {
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


@retry_with_backoff
def review_code(code: str, language: str = "", context: str = "") -> dict[str, Any]:
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
            },
        ],
    )
