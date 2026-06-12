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
        console.print(Panel("[dim]No explicit decisions recorded[/dim]", title="[bold green]Decisions Made[/bold green]", border_style="green"))


def _run_cli_tests():
    import tempfile

    sample_notes = {
        "title": "Weekly Sync",
        "duration_estimate": "30m",
        "attendees": ["Alice", "Bob"],
        "executive_summary": "Quick status updates and next steps.",
        "key_topics": [{"topic": "Roadmap", "discussion": "Reviewed milestones."}],
        "decisions": ["Ship v1 Friday"],
        "action_items": [{"task": "Prepare release notes", "owner": "Alice", "due": "Friday"}],
        "blockers": [],
        "follow_up_meetings": [],
        "sentiment": "positive",
    }

    original_summarize = summarize_transcript
    original_display = display_notes
    original_argv = sys.argv[:]
    original_stdin = sys.stdin

    def fake_summarize(_):
        return sample_notes

    def fake_display(_):
        return None

    try:
        globals()["summarize_transcript"] = fake_summarize
        globals()["display_notes"] = fake_display

        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            transcript_file = td_path / "transcript.txt"
            transcript_file.write_text("Alice: update", encoding="utf-8")

            # (1) --export writes JSON
            export1 = td_path / "notes1.json"
            rc = main([str(transcript_file), "--export", str(export1)])
            assert rc == 0 and export1.exists()
            p1 = json.loads(export1.read_text(encoding="utf-8"))
            assert "generated_at" in p1 and p1["notes"] == sample_notes

            # (2) -e works equivalently
            export2 = td_path / "notes2.json"
            rc = main([str(transcript_file), "-e", str(export2)])
            assert rc == 0 and export2.exists()
            p2 = json.loads(export2.read_text(encoding="utf-8"))
            assert "generated_at" in p2 and p2["notes"] == sample_notes

            # (3) no export flag skips JSON write
            before = {p.name for p in td_path.glob("*.json")}
            rc = main([str(transcript_file)])
            after = {p.name for p in td_path.glob("*.json")}
            assert rc == 0 and before == after

            # (4) missing transcript arg after flag shows usage/exit 1
            rc = main(["--export", str(td_path / "oops.json")])
            assert rc == 1

            # (5) stdin mode - --export
            export3 = td_path / "notes3.json"
            sys.stdin = type("_S", (), {"read": lambda self: "stdin transcript"})()
            rc = main(["-", "--export", str(export3)])
            assert rc == 0 and export3.exists()

        return 0
    finally:
        globals()["summarize_transcript"] = original_summarize
        globals()["display_notes"] = original_display
        sys.argv = original_argv
        sys.stdin = original_stdin


def main(argv=None):
    args = list(argv if argv is not None else sys.argv[1:])

    if args and args[0] == "--run-cli-tests":
        return _run_cli_tests()

    export_path = None
    i = 0
    while i < len(args):
        if args[i] in ("--export", "-e"):
            if i + 1 >= len(args):
                print("Usage: summarizer.py <transcript_file|-> [--export|-e output.json]")
                return 1
            export_path = args[i + 1]
            del args[i:i + 2]
            continue
        i += 1

    if len(args) != 1:
        print("Usage: summarizer.py <transcript_file|-> [--export|-e output.json]")
        return 1

    source = args[0]
    if source == "-":
        transcript = sys.stdin.read()
    else:
        transcript = Path(source).read_text(encoding="utf-8")

    notes = summarize_transcript(transcript)
    display_notes(notes)

    if export_path:
        payload = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "notes": notes,
        }
        Path(export_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
