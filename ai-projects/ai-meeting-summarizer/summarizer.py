"""
AI Meeting Notes Summarizer
Takes a raw meeting transcript (text file or pasted text) and produces
structured meeting notes: summary, action items, decisions, key topics, attendees.
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown

load_dotenv()

console = Console()
CHAT_MODEL = "gpt-4o-mini"

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def print_usage(response) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(
        f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}"
    )


NOTES_SCHEMA = {
    "name": "meeting_notes",
    "description": "Structured meeting notes extracted from a transcript",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short descriptive meeting title"},
            "duration_estimate": {
                "type": "string",
                "description": "Estimated meeting duration based on transcript length",
            },
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names or roles of people mentioned in the transcript",
            },
            "executive_summary": {
                "type": "string",
                "description": "3-4 sentence high-level summary of the meeting",
            },
            "key_topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "discussion": {
                            "type": "string",
                            "description": "1-2 sentence summary of what was discussed",
                        },
                    },
                    "required": ["topic", "discussion"],
                },
            },
            "decisions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete decisions that were made during the meeting",
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "owner": {
                            "type": "string",
                            "description": "Person/role responsible, or 'TBD'",
                        },
                        "due": {
                            "type": "string",
                            "description": "Due date if mentioned, or 'Not specified'",
                        },
                    },
                    "required": ["task", "owner", "due"],
                },
            },
            "blockers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Issues, risks, or blockers raised during the meeting",
            },
            "follow_up_meetings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Any follow-up meetings or check-ins mentioned",
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "tense", "mixed"],
                "description": "Overall tone/sentiment of the meeting",
            },
        },
        "required": [
            "title",
            "attendees",
            "executive_summary",
            "key_topics",
            "decisions",
            "action_items",
            "blockers",
            "sentiment",
        ],
    },
}


def summarize_transcript(transcript: str) -> dict:
    with console.status("[bold green]Processing..."):
        response = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are an expert meeting facilitator and note-taker. "
                        "Extract structured meeting notes from the provided transcript. "
                        "Be precise — only include action items, decisions, and blockers that are "
                        "explicitly stated or clearly implied in the transcript."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Summarize this meeting transcript:\n\n{transcript}",
                },
            ],
            tools=[{"type": "function", "function": NOTES_SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "meeting_notes"}},
            temperature=0.2,
        )
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)


SENTIMENT_STYLE = {
    "positive": "green",
    "neutral": "blue",
    "tense": "red",
    "mixed": "yellow",
}


def display_notes(notes: dict):
    sentiment_color = SENTIMENT_STYLE.get(notes.get("sentiment", "neutral"), "white")

    console.print()
    console.print(Panel.fit("[bold]Meeting Notes[/bold]"))
    console.print(f"Title: {notes.get('title', 'Untitled')}")
    console.print(f"Sentiment: [{sentiment_color}]{notes.get('sentiment', 'neutral')}[/{sentiment_color}]")


if __name__ == "__main__" and os.getenv("PYTEST_CURRENT_TEST"):
    pass


def _run_print_usage_tests():
    import io
    from types import SimpleNamespace

    # usage missing branch
    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=False, color_system=None)
    original_console = globals()["console"]
    try:
        globals()["console"] = test_console
        print_usage(SimpleNamespace(usage=None))
        assert buf.getvalue() == ""

        # usage present branch + cost formatting
        buf2 = io.StringIO()
        globals()["console"] = Console(file=buf2, force_terminal=False, color_system=None)
        usage = SimpleNamespace(prompt_tokens=1000, completion_tokens=500)
        print_usage(SimpleNamespace(usage=usage))
        out = buf2.getvalue()
        assert "📊 Tokens: 1000 in + 500 out = 1500 total" in out
        assert "💰 Est. cost: $0.0000" in out
    finally:
        globals()["console"] = original_console


if __name__ == "__main__" and "--test-print-usage" in sys.argv:
    _run_print_usage_tests()
