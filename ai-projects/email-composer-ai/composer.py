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
VERBOSE: bool = False


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


@retry_with_backoff
def _create_chat_completion(**kwargs):
    if VERBOSE:
        model = kwargs.get("model", CHAT_MODEL)
        messages = kwargs.get("messages", [])
        input_chars = sum(len(str(message.get("content", ""))) for message in messages)
        console.print(f"[dim]Model: {model}[/dim]")
        console.print(f"[dim]Input size: {input_chars} chars[/dim]")
        console.print("⏳ Calling OpenAI API...")
        start = time.time()
        response = get_client().chat.completions.create(**kwargs)
        elapsed = time.time() - start
        console.print(f"✅ Done in {elapsed:.1f}s")
        return response
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
            f"[yellow]Cost estimate unavailable: no pricing"
        )


# -----------------------------
# Tests for verbose diagnostics
# -----------------------------

def test_create_chat_completion_non_verbose(monkeypatch):
    class DummyCompletions:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return {"ok": True, "kwargs": kwargs}

    class DummyChat:
        def __init__(self):
            self.completions = DummyCompletions()

    class DummyClient:
        def __init__(self):
            self.chat = DummyChat()

    dummy_client = DummyClient()

    printed = []

    def fake_print(msg):
        printed.append(msg)

    monkeypatch.setattr(sys.modules[__name__], "VERBOSE", False)
    monkeypatch.setattr(sys.modules[__name__], "get_client", lambda: dummy_client)
    monkeypatch.setattr(console, "print", fake_print)

    response = _create_chat_completion(model="m", messages=[{"content": "hello"}])

    assert response["ok"] is True
    assert dummy_client.chat.completions.calls == 1
    assert printed == []


def test_create_chat_completion_verbose(monkeypatch):
    class DummyCompletions:
        def __init__(self):
            self.calls = 0

        def create(self, **kwargs):
            self.calls += 1
            return {"ok": True, "kwargs": kwargs}

    class DummyChat:
        def __init__(self):
            self.completions = DummyCompletions()

    class DummyClient:
        def __init__(self):
            self.chat = DummyChat()

    dummy_client = DummyClient()
    printed = []

    def fake_print(msg):
        printed.append(msg)

    monkeypatch.setattr(sys.modules[__name__], "VERBOSE", True)
    monkeypatch.setattr(sys.modules[__name__], "get_client", lambda: dummy_client)
    monkeypatch.setattr(console, "print", fake_print)

    response = _create_chat_completion(
        model="gpt-test",
        messages=[{"content": "abc"}, {"content": "defg"}],
    )

    assert response["ok"] is True
    assert dummy_client.chat.completions.calls == 1
    assert any("Model: gpt-test" in m for m in printed)
    assert any("Input size: 7 chars" in m for m in printed)
    assert any("⏳ Calling OpenAI API..." in m for m in printed)
    assert any("✅ Done in" in m for m in printed)
