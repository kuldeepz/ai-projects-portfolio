"""
Document Comparison Agent
Compares two documents (text or PDF) and identifies differences,
similarities, conflicts, and produces a structured diff report.
"""

import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text

load_dotenv()

console = Console()
CHAT_MODEL = "gpt-4o-mini"

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


COMPARE_SCHEMA = {
    "name": "comparison_report",
    "description": "Structured comparison between two documents",
    "parameters": {
        "type": "object",
        "properties": {
            "doc1_summary": {"type": "string", "description": "2-3 sentence summary of document 1"},
            "doc2_summary": {"type": "string", "description": "2-3 sentence summary of document 2"},
            "overall_similarity": {
                "type": "integer",
                "description": "Similarity score 0-100 (100 = identical content)"
            },
            "common_themes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topics or points present in both documents"
            },
            "unique_to_doc1": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key points or information only in document 1"
            },
            "unique_to_doc2": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key points or information only in document 2"
            },
            "conflicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "doc1_position": {"type": "string"},
                        "doc2_position": {"type": "string"}
                    },
                    "required": ["topic", "doc1_position", "doc2_position"]
                },
                "description": "Areas where the two documents contradict or disagree"
            },
            "tone_comparison": {
                "type": "string",
                "description": "How the writing tone/style differs between documents"
            },
            "recommendation": {
                "type": "string",
                "description": "Suggested next steps or which document to prefer for a given purpose"
            }
        },
        "required": [
            "doc1_summary", "doc2_summary", "overall_similarity",
            "common_themes", "unique_to_doc1", "unique_to_doc2",
            "conflicts", "recommendation"
        ]
    }
}


def read_document(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        with open(path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(p.extract_text() or "" for p in reader.pages)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def compare_documents(text1: str, text2: str, doc1_name: str, doc2_name: str, context: str = "") -> dict:
    ctx = f"\nComparison context: {context}" if context else ""
    max_chars = 5000

    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert document analyst. Compare two documents thoroughly. "
                    "Identify what they agree on, where they differ, and where they directly conflict. "
                    "Be specific — quote or paraphrase actual content when identifying differences."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Compare these two documents:{ctx}\n\n"
                    f"--- {doc1_name} ---\n{text1[:max_chars]}\n\n"
                    f"--- {doc2_name} ---\n{text2[:max_chars]}"
                )
            }
        ],
        tools=[{"type": "function", "function": COMPARE_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "comparison_report"}},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)


def similarity_bar(score: int) -> str:
    filled = score // 5
    bar = "█" * filled + "░" * (20 - filled)
    color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
    return f"[{color}]{bar}[/{color}] [bold]{score}%[/bold]"


def display_report(report: dict, doc1_name: str, doc2_name: str):
    console.print()
    console.print(Panel.fit(
        f"[bold white]Document Comparison Report[/bold white]\n"
        f"[dim]{doc1_name}[/dim] [white]vs[/white] [dim]{doc2_name}[/dim]\n"
        f"Similarity: {similarity_bar(report['overall_similarity'])}",
        title="[bold cyan]Comparison Results[/bold cyan]",
        border_style="cyan"
    ))

    # Summaries side by side
    summary_table = Table(show_header=True, header_style="bold")
    summary_table.add_column(f"[cyan]{doc1_name}[/cyan]", ratio=1)
    summary_table.add_column(f"[magenta]{doc2_name}[/magenta]", ratio=1)
    summary_table.add_row(
        f"[dim]{report['doc1_summary']}[/dim]",
        f"[dim]{report['doc2_summary']}[/dim]"
    )
    console.print(Panel(summary_table, title="[bold]Document Summaries[/bold]", border_style="dim"))

    # Common themes
    if report["common_themes"]:
        common_text = "\n".join(f"  [green]◆[/green] {t}" for t in report["common_themes"])
        console.print(Panel(common_text, title="[bold green]Common Themes[/bold green]", border_style="green"))

    # Unique content side by side
    unique_table = Table(show_header=True, header_style="bold")
    unique_table.add_column(f"[cyan]Only in {doc1_name}[/cyan]", ratio=1)
    unique_table.add_column(f"[magenta]Only in {doc2_name}[/magenta]", ratio=1)

    u1 = report["unique_to_doc1"]
    u2 = report["unique_to_doc2"]
    max_rows = max(len(u1), len(u2))
    for i in range(max_rows):
        cell1 = f"[cyan]•[/cyan] {u1[i]}" if i < len(u1) else ""
        cell2 = f"[magenta]•[/magenta] {u2[i]}" if i < len(u2) else ""
        unique_table.add_row(cell1, cell2)
    console.print(Panel(unique_table, title="[bold]Unique Content[/bold]", border_style="blue"))

    # Conflicts
    if report["conflicts"]:
        conflict_table = Table(show_header=True, header_style="bold red")
        conflict_table.add_column("Topic", style="bold", ratio=1)
        conflict_table.add_column(f"[cyan]{doc1_name}[/cyan]", ratio=2)
        conflict_table.add_column(f"[magenta]{doc2_name}[/magenta]", ratio=2)
        for c in report["conflicts"]:
            conflict_table.add_row(c["topic"], c["doc1_position"], c["doc2_position"])
        console.print(Panel(conflict_table, title="[bold red]Conflicts & Disagreements[/bold red]", border_style="red"))
    else:
        console.print(Panel("[green]No direct conflicts found.[/green]", title="[bold]Conflicts[/bold]", border_style="green"))

    # Tone comparison
    if report.get("tone_comparison"):
        console.print(Panel(report["tone_comparison"], title="[bold]Tone & Style[/bold]", border_style="dim"))

    # Recommendation
    console.print(Panel(
        f"[italic]{report['recommendation']}[/italic]",
        title="[bold yellow]Recommendation[/bold yellow]",
        border_style="yellow"
    ))
    console.print()


def main():
    if len(sys.argv) < 3:
        console.print("[yellow]Usage:[/yellow] python compare.py <doc1> <doc2> [context]")
        console.print("[dim]Example: python compare.py contract_v1.pdf contract_v2.pdf 'software license agreement'[/dim]")
        sys.exit(1)

    path1, path2 = sys.argv[1], sys.argv[2]
    context = sys.argv[3] if len(sys.argv) > 3 else ""

    for p in (path1, path2):
        if not os.path.exists(p):
            console.print(f"[red]File not found:[/red] {p}")
            sys.exit(1)

    doc1_name = Path(path1).name
    doc2_name = Path(path2).name

    console.print(f"\n[cyan]Comparing:[/cyan]")
    console.print(f"  [cyan]Doc 1:[/cyan] {doc1_name}")
    console.print(f"  [cyan]Doc 2:[/cyan] {doc2_name}")
    if context:
        console.print(f"  [cyan]Context:[/cyan] {context}")

    with console.status("[bold green]Reading documents...[/bold green]"):
        text1 = read_document(path1)
        text2 = read_document(path2)

    if not text1.strip() or not text2.strip():
        console.print("[red]Could not extract text from one or both documents.[/red]")
        sys.exit(1)

    with console.status("[bold green]Comparing documents...[/bold green]"):
        report = compare_documents(text1, text2, doc1_name, doc2_name, context)

    display_report(report, doc1_name, doc2_name)


if __name__ == "__main__":
    main()
