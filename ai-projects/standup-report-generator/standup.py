"""
Standup Report Generator
Converts raw bullet notes into polished standup / status reports
for daily standups, weekly syncs, or executive status updates.
"""

import os, sys, json, argparse, time, random, functools
from datetime import date, datetime
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def print_usage(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

def retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=8.0, jitter=0.25):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
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

FORMATS = {
    "1": ("standup", "Daily standup (Yesterday / Today / Blockers)"),
    "2": ("weekly", "Weekly status report (Accomplishments / Plan / Risks)"),
    "3": ("executive", "Executive summary (Business impact, concise, non-technical)"),
    "4": ("slack", "Slack-style update (short, emoji-friendly, bullet points)"),
}

SCHEMA = {
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

SAMPLE_NOTES = {
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
def _create_chat_completion(**kwargs):
    return get_client().chat.completions.create(**kwargs)

def generate_report(data: dict, verbose: bool = False) -> dict:
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
        temperature=0.4,
    )
    print_usage(response)
    if verbose:
        elapsed = time.perf_counter() - start
        console.print(f"✅ Done in {elapsed:.1f}s")
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", nargs="?")
    parser.add_argument("--export", "-e", choices=["json"])
    parser.add_argument("--export-out", default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    parsed = parser.parse_args()

    if not parsed.input_file:
        console.print("[dim]No file provided — using sample notes...[/dim]\n")
        data = SAMPLE_NOTES
    else:
        with open(parsed.input_file) as f:
            data = json.load(f)

    with console.status("[bold green]Generating report...[/bold green]"):
        report = generate_report(data, verbose=parsed.verbose)

    console.print()
    console.print(Panel(Markdown(report["formatted_report"]),
                        title=report.get("title", "Standup Report"),
                        border_style="cyan"))


# -------------------------
# Unit tests (pytest)
# -------------------------

def test_print_usage_no_usage(monkeypatch):
    calls = []
    monkeypatch.setattr(console, "print", lambda *args, **kwargs: calls.append((args, kwargs)))

    class Response:
        usage = None

    print_usage(Response())
    assert calls == []


def test_print_usage_token_fallback_and_format(monkeypatch):
    captured = []
    monkeypatch.setattr(console, "print", lambda msg, *args, **kwargs: captured.append(msg))

    class Usage:
        prompt_tokens = None
        completion_tokens = 10
        total_tokens = None

    class Response:
        usage = Usage()

    print_usage(Response())

    assert len(captured) == 1
    line = captured[0]
    assert "📊 Tokens: 0 in + 10 out = 10 total" in line
    assert "💰 Est. cost: $0.0000" in line


def test_retry_with_backoff_retries_and_sleeps(monkeypatch):
    sleeps = []
    monkeypatch.setattr(time, "sleep", lambda d: sleeps.append(d))
    monkeypatch.setattr(random, "uniform", lambda a, b: 1.0)

    state = {"n": 0}

    @retry_with_backoff(max_retries=3, base_delay=0.1, max_delay=1.0, jitter=0.25)
    def flaky():
        state["n"] += 1
        if state["n"] < 3:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert state["n"] == 3
    assert sleeps == [0.1, 0.2]


def test_retry_with_backoff_reraises_after_boundary(monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda d: None)
    monkeypatch.setattr(random, "uniform", lambda a, b: 1.0)

    state = {"n": 0}

    @retry_with_backoff(max_retries=2, base_delay=0.1, max_delay=1.0, jitter=0.25)
    def always_fail():
        state["n"] += 1
        raise RuntimeError("fatal")

    try:
        always_fail()
        assert False, "Expected RuntimeError"
    except RuntimeError as e:
        assert str(e) == "fatal"
    assert state["n"] == 3
