"""
Dependency Risk Scanner
Audits requirements.txt / package.json / pyproject.toml for outdated,
deprecated, or vulnerable packages and recommends upgrades.
"""

import os, sys, json, re, time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import (
    OpenAI,
    APIConnectionError,
    APITimeoutError,
    RateLimitError,
    APIError,
    BadRequestError,
    AuthenticationError,
)
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"
VERBOSE = False


def print_usage(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")


_client = None


def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("Error: OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
        sys.exit(1)

    args = sys.argv[1:]
    file_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--export", "-e"):
            i += 1
            continue
        if arg in ("--verbose", "-v"):
            i += 1
            continue
        if arg.startswith("-"):
            i += 1
            continue
        file_args.append(arg)
        i += 1
    for file_arg in file_args:
        p = Path(file_arg)
        if not p.exists():
            console.print(f"Error: File does not exist: {file_arg}")
            sys.exit(1)
        if not p.is_file():
            console.print(f"Error: Path is not a file: {file_arg}")
            sys.exit(1)
        if not os.access(p, os.R_OK):
            console.print(f"Error: File is not readable: {file_arg}")
            sys.exit(1)

    console.print("Setup OK ✓")


RETRYABLE_EXCEPTIONS = (APIConnectionError, APITimeoutError, RateLimitError, APIError)
NON_RETRYABLE_EXCEPTIONS = (BadRequestError, AuthenticationError)


def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except NON_RETRYABLE_EXCEPTIONS:
                raise
            except RETRYABLE_EXCEPTIONS as e:
                last_exc = e
                if i == len(delays) - 1:
                    break
                if VERBOSE:
                    console.print(f"🔁 Retry {i + 1}/{len(delays)} failed ({type(e).__name__}); waiting {delay}s...")
                with console.status("[bold green]Processing..."):
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
def _create_scan_response(dep_content: str):
    if VERBOSE:
        console.print(f"🔧 Model: {MODEL}")
        console.print(f"📝 Input size: {len(dep_content)} chars")
        console.print("⏳ Calling OpenAI API...")
        started = time.time()
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
        elapsed = time.time() - started
        console.print(f"✅ Done in {elapsed:.1f}s")
