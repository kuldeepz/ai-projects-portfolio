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
        console.print(Panel("[dim]No explicit decisions recorded.[/dim]", title="[bold]Decisions[/bold]", border_style="dim"))

    # Action items
    if notes["action_items"]:
        table = Table(show_header=True, header_style="bold yellow")
        table.add_column("Action Item", ratio=3)
        table.add_column("Owner", ratio=1)
        table.add_column("Due", ratio=1)
        for item in notes["action_items"]:
            table.add_row(item["task"], item["owner"], item["due"])
        console.print(Panel(table, title="[bold yellow]Action Items[/bold yellow]", border_style="yellow"))
    else:
        console.print(Panel("[dim]No action items identified.[/dim]", title="[bold]Action Items[/bold]", border_style="dim"))

    # Blockers
    if notes["blockers"]:
        blockers_text = "\n".join(f"  [red]⚠[/red] {b}" for b in notes["blockers"])
        console.print(Panel(blockers_text, title="[bold red]Blockers & Risks[/bold red]", border_style="red"))

    # Follow-ups
    if notes.get("follow_up_meetings"):
        fu_text = "\n".join(f"  [dim]→[/dim] {f}" for f in notes["follow_up_meetings"])
        console.print(Panel(fu_text, title="[bold]Follow-up Meetings[/bold]", border_style="dim"))

    console.print()


def save_notes(notes: dict, output_path: str):
    lines = [
        f"# {notes['title']}",
        f"",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d')}",
        f"**Attendees:** {', '.join(notes['attendees'])}",
        f"**Sentiment:** {notes.get('sentiment', 'neutral').title()}",
        f"",
        f"## Executive Summary",
        f"",
        notes["executive_summary"],
        f"",
        f"## Key Topics",
        f"",
    ]
    for t in notes["key_topics"]:
        lines += [f"### {t['topic']}", f"", t["discussion"], f""]

    lines += [f"## Decisions Made", f""]
    for d in notes["decisions"]:
        lines.append(f"- {d}")

    lines += [f"", f"## Action Items", f"", "| Task | Owner | Due |", "| --- | --- | --- |"]
    for item in notes["action_items"]:
        lines.append(f"| {item['task']} | {item['owner']} | {item['due']} |")

    if notes["blockers"]:
        lines += [f"", f"## Blockers & Risks", f""]
        for b in notes["blockers"]:
            lines.append(f"- {b}")

    with open(output_path, "w") as f:
        f.write("\n".join(lines))


def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] python summarizer.py <transcript.txt> [--export|-e]")
        console.print("[dim]Example: python summarizer.py sprint_meeting.txt --export[/dim]")
        console.print("\n[dim]Tip: You can also pipe text: cat transcript.txt | python summarizer.py - --export[/dim]")
        sys.exit(1)

    args = sys.argv[1:]
    export_json = False
    if "--export" in args:
        export_json = True
        args.remove("--export")
    if "-e" in args:
        export_json = True
        args.remove("-e")

    if len(args) < 1:
        console.print("[yellow]Usage:[/yellow] python summarizer.py <transcript.txt> [--export|-e]")
        sys.exit(1)

    file_arg = args[0]

    if file_arg == "-":
        transcript = sys.stdin.read()
        stem = "meeting"
    else:
        if not os.path.exists(file_arg):
            console.print(f"[red]File not found:[/red] {file_arg}")
            sys.exit(1)
        with open(file_arg, "r", encoding="utf-8") as f:
            transcript = f.read()
        stem = Path(file_arg).stem

    if not transcript.strip():
        console.print("[red]Empty transcript.[/red]")
        sys.exit(1)

    # Truncate very long transcripts
    if len(transcript) > 12000:
        console.print("[yellow]Transcript truncated to 12,000 characters for processing.[/yellow]")
        transcript = transcript[:12000]

    console.print(f"\n[cyan]Processing transcript:[/cyan] {file_arg}")

    with console.status("[bold green]Extracting meeting notes...[/bold green]"):
        notes = summarize_transcript(transcript)

    display_notes(notes)

    output_file = f"notes_{stem}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    save_notes(notes, output_file)
    console.print(f"[green]Notes saved to:[/green] {output_file}")

    if export_json:
        export_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        export_file = f"output_{export_timestamp}.json"
        export_payload = {**notes, "generated_at": datetime.now().isoformat()}
        with open(export_file, "w", encoding="utf-8") as f:
            json.dump(export_payload, f, indent=2, ensure_ascii=False)
        console.print(f"[green]JSON export saved to:[/green] {export_file}")

    console.print()


if __name__ == "__main__":
    main()
