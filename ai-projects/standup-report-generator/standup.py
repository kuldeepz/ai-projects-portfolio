"""
Standup Report Generator
Converts raw bullet notes into polished standup / status reports
for daily standups, weekly syncs, or executive status updates.
"""

import os, sys, json, argparse, time, random, functools
from datetime import date, datetime
from typing import Any, Callable
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console: Console = Console()
MODEL: str = "gpt-4o-mini"

PRICING_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"in": 0.00015, "out": 0.00060},
}

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

    rates = PRICING_PER_1K.get(MODEL)
    if rates:
        cost = (prompt_tokens / 1000) * rates["in"] + (completion_tokens / 1000) * rates["out"]
        cost_display = f"${cost:.4f}"
    else:
        cost_display = "N/A"

    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: {cost_display}")

def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 8.0, jitter: float = 0.25) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            for attempt in range(max_retries + 1):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    if attempt == max_retries:
                        raise
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    delay *= random.uniform(1 - jitter, 1 + jitter)
                    time.sleep(delay)
        return wrapper
    return deco

def validate_environment(parsed: Any) -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("❌ OPENAI_API_KEY is not set. Please set it in your environment or .env file.")
        sys.exit(1)

    paths_to_check: list[str] = []
    if getattr(parsed, "input_file", None):
        paths_to_check.append(parsed.input_file)
    if getattr(parsed, "export_out", None):
        paths_to_check.append(parsed.export_out)

    for path in paths_to_check:
        if not os.path.exists(path):
            console.print(f"❌ File path does not exist: {path}")
            sys.exit(1)
        if not os.path.isfile(path):
            console.print(f"❌ Path is not a file: {path}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"❌ File is not readable: {path}")
            sys.exit(1)

    if getattr(parsed, "verbose", False):
        console.print("Setup OK ✓")

FORMATS: dict[str, tuple[str, str]] = {
    "1": ("standup", "Daily standup (Yesterday / Today / Blockers)"),
    "2": ("weekly", "Weekly status report (Accomplishments / Plan / Risks)"),
    "3": ("executive", "Executive summary (Business impact, concise, non-technical)"),
    "4": ("slack", "Slack-style update (short, emoji-friendly, bullet points)"),
}

SCHEMA: dict[str, Any] = {
    "name": "report_output",
    "description": "Generated status report",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "formatted_report": {"type": "string", "description": "The complete formatted report in markdown"},
            "key_highlights": {"type": "array", "items": {"type": "string"}, "description": "Top 2-3 highlights for quick skim"},
            "blockers_summary": {"type": "string"},
            "tone_notes": {"type": "string"}
        },
        "required": ["title", "formatted_report", "key_highlights"]
    }
}

SAMPLE_NOTES: dict[str, Any] = {
    "name": "Kuldeep Rao",
    "role": "AI Lead",
    "date": str(date.today()),
    "format": "standup",
    "raw_notes": [
        "finished the prompt library POC",
        "reviewed 3 PRs for the ML team",
        "fixed the embedding cache bug in prod",
        "today: working on ADO integration for sprint planner",
        "today: meeting with stakeholders at 2pm to demo the AI code reviewer",
        "blocker: waiting on infra team to provision GPU quota for fine-tuning job",
        "risk: sprint planner needs ADO API access — ticket with IT raised"
    ]
}

@retry_with_backoff(max_retries=3)
def _create_chat_completion(**kwargs: Any) -> Any:
    return get_client().chat.completions.create(**kwargs)

def generate_report(data: dict[str, Any], verbose: bool = False) -> dict[str, Any]:
    fmt = data.get("format", "standup")
    fmt_desc = next((v[1] for v in FORMATS.values() if v[0] == fmt), fmt)
    messages = [
        {"role": "system", "content": (
            f"You are a professional technical writer. Transform raw bullet notes into a polished "
            f"{fmt_desc}. Keep it concise, professional, and well-structured in markdown. "
            f"For standup: use Yesterday / Today / Blockers sections. "
            f"For executive: focus on business impact, skip technical jargon. "
            f"For Slack: use emojis sparingly, keep it scannable."
        )},
        {"role": "user", "content": (
            f"Name: {data.get('name','')}, Role: {data.get('role','')}, Date: {data.get('date','')}\n"
            f"Raw notes:\n" + "\n".join(f"- {n}" for n in data.get("raw_notes", []))
        )}
    ]
    if verbose:
        total_chars = sum(len(m["content"]) for m in messages)
        est_tokens = int(total_chars / 4)
        console.print(f"[dim]Model:[/dim] {MODEL}")
        console.print(f"[dim]Input size:[/dim] {total_chars} chars (~{est_tokens} tokens)")
        console.print("⏳ Calling OpenAI API...")
        start = time.perf_counter()
    response = _create_chat_completion(
        model=MODEL,
        messages=messages,
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "report_output"}},
    )
