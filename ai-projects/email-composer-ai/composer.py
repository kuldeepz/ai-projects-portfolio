"""
AI Email Composer
Generate professional emails from bullet points.
Supports tone selection, length control, and follow-up suggestions.
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import TypedDict

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

load_dotenv()

_client: OpenAI | None = None


class EmailOutput(TypedDict):
    subject: str
    body: str
    alternative_subjects: list[str]
    follow_up_suggestions: list[str]
    word_count: int
    tone_notes: str


JSONValue = str | int | float | bool | None | dict[str, "JSONValue"] | list["JSONValue"]


def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception:
                if attempt == len(delays):
                    raise
                time.sleep(delays[attempt])
    return wrapper


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


console: Console = Console()

CHAT_MODEL: str = "gpt-4o-mini"

# USD pricing per 1M tokens by model
PRICING_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
}

TONES: dict[str, tuple[str, str]] = {
    "1": ("formal", "Professional and polished — suitable for executives, clients, formal requests"),
    "2": ("friendly", "Warm and approachable — for colleagues, collaborators, casual business"),
    "3": ("assertive", "Direct and confident — for negotiations, setting expectations, following up"),
    "4": ("empathetic", "Compassionate and understanding — for difficult conversations, apologies"),
    "5": ("persuasive", "Compelling and motivating — for pitches, proposals, calls to action"),
}

EMAIL_SCHEMA: dict[str, JSONValue] = {
    "name": "email_output",
    "description": "Generated email with metadata",
    "parameters": {
        "type": "object",
        "properties": {
            "subject": {"type": "string", "description": "Email subject line"},
            "body": {"type": "string", "description": "Full email body including greeting and sign-off"},
            "alternative_subjects": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2 alternative subject line options"
            },
            "follow_up_suggestions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "2-3 suggested follow-up actions or emails"
            },
            "word_count": {"type": "integer", "description": "Approximate word count of the body"},
            "tone_notes": {"type": "string", "description": "Brief note on how the tone was applied"}
        },
        "required": ["subject", "body", "alternative_subjects", "follow_up_suggestions", "word_count", "tone_notes"]
    }
}

LENGTH_PROMPTS: dict[str, str] = {
    "short": "Keep it brief — under 100 words. Get to the point fast.",
    "medium": "Aim for 100-200 words. Clear and complete without being verbose.",
    "long": "Write a thorough email of 200-350 words with full context and detail.",
}


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Setup error:[/red] OPENAI_API_KEY is missing or empty.")
        console.print("[yellow]Set OPENAI_API_KEY in your environment or .env file and try again.[/yellow]")
        sys.exit(1)

    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            continue
        if os.path.sep not in arg and not arg.startswith("."):
            continue
        if not os.path.exists(arg):
            console.print(f"[red]Setup error:[/red] File path does not exist: {arg}")
            sys.exit(1)
        if not os.path.isfile(arg):
            console.print(f"[red]Setup error:[/red] Path is not a file: {arg}")
            sys.exit(1)
        if not os.access(arg, os.R_OK):
            console.print(f"[red]Setup error:[/red] File is not readable: {arg}")
            sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")


@retry_with_backoff
def _create_chat_completion(**kwargs):
    return get_client().chat.completions.create(**kwargs)


def compose_email(
    bullet_points: str,
    tone: str,
    length: str,
    sender_name: str,
    recipient_context: str,
    email_purpose: str,
) -> EmailOutput:
    length_instruction = LENGTH_PROMPTS.get(length, LENGTH_PROMPTS["medium"])

    system_prompt = (
        f"You are an expert business communication writer. "
        f"Write emails that are clear, purposeful, and professionally crafted.\n\n"
        f"Tone: {tone}\n"
        f"Length: {length_instruction}"
    )

    user_prompt = (
        f"Compose a professional email from these bullet points:\n\n"
        f"Points to cover:\n{bullet_points}\n\n"
        f"Email purpose: {email_purpose}\n"
        f"Sender name: {sender_name}\n"
        f"Recipient context: {recipient_context}\n\n"
        f"Generate the subject line, full email body, 2 alternative subject lines, "
        f"and 2-3 follow-up suggestions."
    )

    with console.status("[bold green]Processing..."):
        response = _create_chat_completion(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            tools=[{"type": "function", "function": EMAIL_SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "email_output"}},
            temperature=0.7,
        )

    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)


def print_usage(prompt_tokens: int, completion_tokens: int) -> None:
    rates = PRICING_PER_1M.get(CHAT_MODEL)
    if rates is None:
        console.print(
            f"[dim]Usage: prompt={prompt_tokens}, completion={completion_tokens}, total={prompt_tokens + completion_tokens} tokens[/dim]"
        )
        console.print(
            f"[yellow]Cost estimate unavailable: no pricing configured for model '{CHAT_MODEL}'.[/yellow]"
        )
        return

    cost = (
        (prompt_tokens / 1_000_000) * rates["input"]
        + (completion_tokens / 1_000_000) * rates["output"]
    )
    console.print(
        f"[dim]Usage: prompt={prompt_tokens}, completion={completion_tokens}, total={prompt_tokens + completion_tokens} tokens | "
        f"Estimated cost (${rates['input']}/1M in, ${rates['output']}/1M out): ${cost:.6f}[/dim]"
    )


def display_result(result: EmailOutput) -> None:
    console.print()
    console.print(Panel(
        f"[bold white]{result['subject']}[/bold white]",
        title="[bold cyan]Subject Line[/bold cyan]",
        border_style="cyan"
    ))

    console.print(Panel(
        result["body"],
        title="[bold green]Email Body[/bold green]",
        border_style="green",
        padding=(1, 2)
    ))

    alt_text = "\n".join(f"  [dim]{i+1}.[/dim] {s}" for i, s in enumerate(result["alternative_subjects"]))
    console.print(Panel(alt_text, title="[bold]Alternative Subject Lines[/bold]", border_style="dim"))


def main() -> None:
    validate_environment()


class _StatusSpy:
    def __init__(self) -> None:
        self.messages: list[str] = []
        self.entered: int = 0

    def __call__(self, message: str):
        self.messages.append(message)
        return self

    def __enter__(self):
        self.entered += 1
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_compose_email_enters_status_and_returns_output():
    spy = _StatusSpy()

    class _FakeResponse:
        class _Choice:
            class _Message:
                class _ToolCall:
                    class _Function:
                        arguments = json.dumps({
                            "subject": "s",
                            "body": "b",
                            "alternative_subjects": ["a1", "a2"],
                            "follow_up_suggestions": ["f1", "f2"],
                            "word_count": 2,
                            "tone_notes": "t",
                        })
                    function = _Function()
                tool_calls = [_ToolCall()]
            message = _Message()
        choices = [_Choice()]

    class _FakeClient:
        class _Chat:
            class _Completions:
                @staticmethod
                def create(**kwargs):
                    return _FakeResponse()
            completions = _Completions()
        chat = _Chat()

    original_status = console.status
    original_get_client = globals()["get_client"]
    try:
        console.status = spy
        globals()["get_client"] = lambda: _FakeClient()
        result = compose_email("pts", "formal", "short", "me", "ctx", "purpose")
    finally:
        console.status = original_status
        globals()["get_client"] = original_get_client

    assert spy.entered == 1
    assert spy.messages == ["[bold green]Processing..."]
    assert result["subject"] == "s"


def test_compose_email_status_does_not_swallow_exceptions():
    spy = _StatusSpy()

    class _FakeClient:
        class _Chat:
            class _Completions:
                @staticmethod
                def create(**kwargs):
                    raise RuntimeError("boom")
            completions = _Completions()
        chat = _Chat()

    original_status = console.status
    original_get_client = globals()["get_client"]
    try:
        console.status = spy
        globals()["get_client"] = lambda: _FakeClient()
        try:
            compose_email("pts", "formal", "short", "me", "ctx", "purpose")
            assert False, "Expected RuntimeError"
        except RuntimeError as exc:
            assert str(exc) == "boom"
    finally:
        console.status = original_status
        globals()["get_client"] = original_get_client

    assert spy.entered == 1
    assert spy.messages == ["[bold green]Processing..."]
