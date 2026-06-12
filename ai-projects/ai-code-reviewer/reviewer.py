"""
AI Code Reviewer
Submit code via file or stdin — get a detailed review covering correctness,
security vulnerabilities, performance, and best practices.
"""

import os
import sys
import json
import time
import random
from functools import wraps
from pathlib import Path
from datetime import datetime
from typing import Any, Literal, TypedDict

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.text import Text

load_dotenv()

_client: OpenAI | None = None


class ReviewIssue(TypedDict):
    severity: Literal["critical", "high", "medium", "low"]
    issue: str
    fix: str


class PerformanceIssue(TypedDict):
    issue: str
    fix: str


class ReviewResult(TypedDict, total=False):
    language: str
    overall_score: int
    summary: str
    security_issues: list[ReviewIssue]
    bugs: list[ReviewIssue]
    performance_issues: list[PerformanceIssue]
    best_practice_violations: list[str]
    positive_aspects: list[str]
    refactored_snippet: str


class JsonSchemaObject(TypedDict, total=False):
    type: str
    description: str
    enum: list[str]
    properties: dict[str, "JsonSchemaObject"]
    items: "JsonSchemaObject"
    required: list[str]


class ReviewSchemaParameters(TypedDict):
    type: str
    properties: dict[str, JsonSchemaObject]
    required: list[str]


class ReviewSchema(TypedDict):
    name: str
    description: str
    parameters: ReviewSchemaParameters


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


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, retry_exceptions: tuple[type[Exception], ...] = (Exception,)):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions:
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (2 ** attempt)
                    jitter = random.uniform(0, delay * 0.2)
                    time.sleep(delay + jitter)
        return wrapper
    return deco


REVIEW_SCHEMA: ReviewSchema = {
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


@retry_with_backoff(max_retries=3, base_delay=1.0, retry_exceptions=(Exception,))
def review_code(code: str, language: str = "", context: str = "") -> ReviewResult:
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
                    "Be specific — point to the exact pattern or line causing each issue."
                ),
            },
            {
                "role": "user",
                "content": f"{lang_hint}{ctx_hint}\n```\n{code}\n```",
            },
        ],
        functions=[REVIEW_SCHEMA],
        function_call={"name": "code_review"},
    )

    print_usage(response)
    args = response.choices[0].message.function_call.arguments
    return json.loads(args)
