"""
AI Email Composer
Generate professional emails from bullet points.
Supports tone selection, length control, and follow-up suggestions.
"""

import os
import sys
import json
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

load_dotenv()

_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client
console: Console = Console()

CHAT_MODEL: str = "gpt-4o-mini"

TONES: dict[str, tuple[str, str]] = {
    "1": ("formal", "Professional and polished — suitable for executives, clients, formal requests"),
    "2": ("friendly", "Warm and approachable — for colleagues, collaborators, casual business"),
    "3": ("assertive", "Direct and confident — for negotiations, setting expectations, following up"),
    "4": ("empathetic", "Compassionate and understanding — for difficult conversations, apologies"),
    "5": ("persuasive", "Compelling and motivating — for pitches, proposals, calls to action"),
}

EMAIL_SCHEMA: dict[str, Any] = {
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


def compose_email(
    bullet_points: str,
    tone: str,
    length: str,
    sender_name: str,
    recipient_context: str,
    email_purpose: str,
) -> dict[str, Any]:
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

    response = get_client().chat.completions.create(
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


def display_result(result: dict[str, Any]) -> None:
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

    follow_text = "\n".join(f"  [cyan]→[/cyan] {s}" for s in result["follow_up_suggestions"])
    console.print(Panel(follow_text, title="[bold]Follow-up Suggestions[/bold]", border_style="blue"))

    meta_table = Table(show_header=False, box=None, padding=(0, 2))
    meta_table.add_column(style="dim")
    meta_table.add_column()
    meta_table.add_row("Word count", str(result["word_count"]))
    meta_table.add_row("Tone applied", result["tone_notes"])
    console.print(Panel(meta_table, title="[bold]Metadata[/bold]", border_style="dim"))
    console.print()


def interactive_mode() -> None:
    """Guided interactive input mode."""
    console.print(Panel.fit(
        "[bold cyan]AI Email Composer[/bold cyan]\n[dim]Turn bullet points into polished emails[/dim]",
        border_style="cyan"
    ))

    # Tone selection
    console.print("\n[bold]Select tone:[/bold]")
    for key, (name, desc) in TONES.items():
        console.print(f"  [cyan]{key}[/cyan] — [bold]{name}[/bold]: [dim]{desc}[/dim]")

    tone_key = Prompt.ask("\nTone", choices=list(TONES.keys()), default="1")
    tone = TONES[tone_key][0]

    length = Prompt.ask("Length", choices=["short", "medium", "long"], default="medium")
    email_purpose = Prompt.ask("Purpose (e.g. 'follow up on proposal', 'request meeting')")
    recipient_context = Prompt.ask("Recipient context (e.g. 'my manager', 'a new client')")


def _assert_email_result_contract(result: dict[str, Any]) -> None:
    """Runtime contract check for compose_email structured output."""
    required_keys = [
        "subject",
        "body",
        "alternative_subjects",
        "follow_up_suggestions",
        "word_count",
        "tone_notes",
    ]
    for key in required_keys:
        if key not in result:
            raise ValueError(f"Missing required key in email result: {key}")

    if not isinstance(result["subject"], str):
        raise TypeError("email result 'subject' must be str")
    if not isinstance(result["body"], str):
        raise TypeError("email result 'body' must be str")
    if not isinstance(result["word_count"], int):
        raise TypeError("email result 'word_count' must be int")
    if not isinstance(result["tone_notes"], str):
        raise TypeError("email result 'tone_notes' must be str")

    if not isinstance(result["alternative_subjects"], list) or not all(
        isinstance(item, str) for item in result["alternative_subjects"]
    ):
        raise TypeError("email result 'alternative_subjects' must be list[str]")

    if not isinstance(result["follow_up_suggestions"], list) or not all(
        isinstance(item, str) for item in result["follow_up_suggestions"]
    ):
        raise TypeError("email result 'follow_up_suggestions' must be list[str]")


def _run_contract_tests() -> None:
    """Lightweight tests for structured return contract."""
    sample = {
        "subject": "Project update",
        "body": "Hi team, here is the latest update...",
        "alternative_subjects": ["Weekly project update", "Status update"],
        "follow_up_suggestions": ["Schedule a sync", "Share timeline"],
        "word_count": 42,
        "tone_notes": "Professional and concise.",
    }
    _assert_email_result_contract(sample)

    parsed = json.loads(json.dumps(sample))
    _assert_email_result_contract(parsed)


if __name__ == "__main__" and "--self-test" in sys.argv:
    _run_contract_tests()
