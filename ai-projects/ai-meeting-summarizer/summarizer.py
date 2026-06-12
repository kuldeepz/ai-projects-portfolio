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
            "duration_estimate": {"type": "string", "description": "Estimated meeting duration based on transcript length"},
            "attendees": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Names or roles of people mentioned in the transcript"
            },
            "executive_summary": {
                "type": "string",
                "description": "3-4 sentence high-level summary of the meeting"
            },
            "key_topics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "discussion": {"type": "string", "description": "1-2 sentence summary of what was discussed"}
                    },
                    "required": ["topic", "discussion"]
                }
            },
            "decisions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Concrete decisions that were made during the meeting"
            },
            "action_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "owner": {"type": "string", "description": "Person/role responsible, or 'TBD'"},
                        "due": {"type": "string", "description": "Due date if mentioned, or 'Not specified'"}
                    },
                    "required": ["task", "owner", "due"]
                }
            },
            "blockers": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Issues, risks, or blockers raised during the meeting"
            },
            "follow_up_meetings": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Any follow-up meetings or check-ins mentioned"
            },
            "sentiment": {
                "type": "string",
                "enum": ["positive", "neutral", "tense", "mixed"],
                "description": "Overall tone/sentiment of the meeting"
            }
        },
        "required": [
            "title", "attendees", "executive_summary", "key_topics",
            "decisions", "action_items", "blockers", "sentiment"
        ]
    }
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
                )
            },
            {
                "role": "user",
                "content": f"Summarize this meeting transcript:\n\n{transcript}"
            }
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
    "mixed": "yellow"
}


def display_notes(notes: dict):
    sentiment_color = SENTIMENT_STYLE.get(notes.get("sentiment", "neutral"), "white")

    console.print()
    console.print(Panel.fit(
        f"[bold white]{notes['title']}[/bold white]\n"
        f"[dim]Attendees: {', '.join(notes['attendees']) or 'Not identified'}[/dim]\n"
        f"[dim]Duration: {notes.get('duration_estimate', 'Unknown')}[/dim]  "
        f"[{sentiment_color}]● {notes.get('sentiment', 'neutral').title()}[/{sentiment_color}]",
        title="[bold cyan]Meeting Notes[/bold cyan]",
        border_style="cyan"
    ))

    # Executive summary
    console.print(Panel(
        f"[italic]{notes['executive_summary']}[/italic]",
        title="[bold]Executive Summary[/bold]",
        border_style="dim"
    ))

    # Key topics
    if notes["key_topics"]:
        topics_text = "\n".join(
            f"  [cyan]▸[/cyan] [bold]{t['topic']}[/bold]\n    [dim]{t['discussion']}[/dim]"
            for t in notes["key_topics"]
        )
        console.print(Panel(topics_text, title="[bold]Key Topics[/bold]", border_style="blue"))

    # Decisions
    if notes["decisions"]:
        dec_text = "\n".join(f"  [green]✔[/green] {d}" for d in notes["decisions"])
        console.print(Panel(dec_text, title="[bold green]Decisions Made[/bold green]", border_style="green"))
    else:
        console.print(Panel("[dim]No explicit decisions recorded",
        title="[bold green]Decisions Made[/bold green]", border_style="green"))


def export_json(notes: dict, stem: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_file = f"notes_{stem}_{stamp}.json"
    out_path = Path(export_file)
    out_path.write_text(json.dumps(notes, indent=2), encoding="utf-8")
    return out_path
