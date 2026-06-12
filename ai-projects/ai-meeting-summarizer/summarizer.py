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
    console.print(
        Panel.fit(
            f"[bold white]{notes['title']}[/bold white]\n"
            f"[dim]Attendees: {', '.join(notes['attendees']) or 'Not identified'}[/dim]\n"
            f"[dim]Duration: {notes.get('duration_estimate', 'Unknown')}[/dim]  "
            f"[{sentiment_color}]● {notes.get('sentiment', 'neutral').title()}[/{sentiment_color}]",
            title="[bold cyan]Meeting Notes[/bold cyan]",
            border_style="cyan",
        )
    )

    console.print(
        Panel(
            f"[italic]{notes['executive_summary']}[/italic]",
            title="[bold]Executive Summary[/bold]",
            border_style="dim",
        )
    )


def _usage() -> str:
    return "Usage: python summarizer.py [--export|-e] <transcript_file|->"


def _parse_args(argv: list[str]) -> tuple[bool, str]:
    export = False
    args = list(argv)
    if args and args[0] in {"--export", "-e"}:
        export = True
        args = args[1:]
    if len(args) != 1:
        raise ValueError(_usage())
    return export, args[0]


def main() -> int:
    export, source = _parse_args(sys.argv[1:])

    if source == "-":
        transcript = sys.stdin.read().strip()
        source_path = Path("stdin")
    else:
        source_path = Path(source)
        transcript = source_path.read_text(encoding="utf-8").strip()

    notes = summarize_transcript(transcript)
    display_notes(notes)

    if export:
        now = datetime.now()
        stamp = now.strftime("%Y%m%d_%H%M%S")
        stem = source_path.stem if source_path.stem else "meeting"

        notes_file = Path(f"notes_{stem}_{stamp}.md")
        notes_md = f"# {notes.get('title', 'Meeting Notes')}\n\n{notes.get('executive_summary', '')}\n"
        notes_file.write_text(notes_md, encoding="utf-8")

        export_file = Path(f"output_{stamp}.json")
        export_payload = {**notes, "generated_at": now.isoformat()}
        export_file.write_text(json.dumps(export_payload, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
