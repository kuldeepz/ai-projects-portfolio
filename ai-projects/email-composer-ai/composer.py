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
        f"[bold white]{result['subject']}",
    ))


def _run_retry_tests() -> None:
    # 1) first 2 calls raise, 3rd succeeds + 3) verify delays
    calls = {"count": 0}
    sleeps: list[int] = []

    def flaky_then_ok():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    original_sleep = time.sleep
    try:
        time.sleep = lambda d: sleeps.append(d)  # type: ignore[assignment]
        wrapped = retry_with_backoff(flaky_then_ok)
        assert wrapped() == "ok"
        assert calls["count"] == 3
        assert sleeps == [1, 2]
    finally:
        time.sleep = original_sleep  # type: ignore[assignment]

    # 2) all attempts fail and exception is re-raised
    fail_calls = {"count": 0}
    sleeps2: list[int] = []

    def always_fail():
        fail_calls["count"] += 1
        raise RuntimeError("still failing")

    original_sleep = time.sleep
    try:
        time.sleep = lambda d: sleeps2.append(d)  # type: ignore[assignment]
        wrapped = retry_with_backoff(always_fail)
        try:
            wrapped()
            raise AssertionError("expected RuntimeError to be re-raised")
        except RuntimeError:
            pass
        assert fail_calls["count"] == 4
        assert sleeps2 == [1, 2, 4]
    finally:
        time.sleep = original_sleep  # type: ignore[assignment]

    # 4) non-transient handling boundary (current behavior: retries all Exception)
    non_transient_calls = {"count": 0}

    class NonTransientError(Exception):
        pass

    def non_transient_fail():
        non_transient_calls["count"] += 1
        raise NonTransientError("bad request")

    wrapped = retry_with_backoff(non_transient_fail)
    try:
        wrapped()
        raise AssertionError("expected NonTransientError")
    except NonTransientError:
        pass
    assert non_transient_calls["count"] == 4


if __name__ == "__main__" and os.getenv("RUN_RETRY_TESTS") == "1":
    _run_retry_tests()
