"""
Sentiment Analysis Dashboard
Analyze sentiment of text inputs individually or in batch.
Supports CSV input, inline text, and produces a rich terminal dashboard.
"""

import os
import sys
import json
import csv
import io
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

load_dotenv()

console = Console()
CHAT_MODEL = "gpt-4o-mini"

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


SENTIMENT_SCHEMA = {
    "name": "sentiment_result",
    "description": "Sentiment analysis result for a piece of text",
    "parameters": {
        "type": "object",
        "properties": {
            "sentiment": {
                "type": "string",
                "enum": ["positive", "negative", "neutral", "mixed"],
                "description": "Overall sentiment"
            },
            "score": {
                "type": "number",
                "description": "Sentiment score from -1.0 (very negative) to 1.0 (very positive)"
            },
            "confidence": {
                "type": "integer",
                "description": "Confidence percentage 0-100"
            },
            "emotions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "emotion": {"type": "string"},
                        "intensity": {"type": "string", "enum": ["low", "medium", "high"]}
                    },
                    "required": ["emotion", "intensity"]
                },
                "description": "Specific emotions detected (e.g., joy, frustration, trust)"
            },
            "key_phrases": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Phrases that most influenced the sentiment"
            },
            "aspect_sentiments": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "aspect": {"type": "string"},
                        "sentiment": {"type": "string", "enum": ["positive", "negative", "neutral"]},
                        "reason": {"type": "string"}
                    },
                    "required": ["aspect", "sentiment"]
                },
                "description": "Sentiment broken down by topic/aspect mentioned in the text"
            },
            "summary": {"type": "string", "description": "One-sentence explanation of the sentiment"}
        },
        "required": ["sentiment", "score", "confidence", "emotions", "key_phrases", "summary"]
    }
}


def analyze_sentiment(text: str) -> dict:
    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert sentiment analyst with deep understanding of human emotion "
                    "in written text. Analyze not just polarity but nuanced emotions, tone, and "
                    "aspect-level sentiment. Be precise and calibrated in your scoring."
                )
            },
            {"role": "user", "content": f"Analyze the sentiment of this text:\n\n{text}"}
        ],
        tools=[{"type": "function", "function": SENTIMENT_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "sentiment_result"}},
        temperature=0.1,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)


SENTIMENT_COLORS = {
    "positive": "green",
    "negative": "red",
    "neutral": "blue",
    "mixed": "yellow"
}

SENTIMENT_ICONS = {
    "positive": "😊",
    "negative": "😞",
    "neutral": "😐",
    "mixed": "🤔"
}

INTENSITY_COLORS = {"low": "dim", "medium": "yellow", "high": "bold red"}


def score_bar(score: float) -> str:
    # score is -1 to 1, map to 0-20 bar
    normalized = int((score + 1) / 2 * 20)
    bar = "░" * normalized + "─" * (20 - normalized)
    color = "green" if score > 0.2 else "red" if score < -0.2 else "blue"
    return f"[{color}]{bar}[/{color}] [{color} bold]{score:+.2f}[/{color} bold]"


def display_single(result: dict, text: str):
    sentiment = result["sentiment"]
    color = SENTIMENT_COLORS[sentiment]
    icon = SENTIMENT_ICONS[sentiment]

    console.print()
    console.print(Panel.fit(
        f"[{color} bold]{icon} {sentiment.upper()}[/{color} bold]\n"
        f"Score: {score_bar(result['score'])}\n"
        f"[dim]Confidence: {result['confidence']}%[/dim]",
        title="[bold cyan]Sentiment Analysis[/bold cyan]",
        border_style="cyan"
    ))

    # Text preview
    preview = text[:200] + "..." if len(text) > 200 else text
    console.print(Panel(f"[dim italic]{preview}[/dim italic]", title="[bold]Input Text[/bold]", border_style="dim"))

    # Summary
    console.print(Panel(result["summary"], title="[bold]Analysis[/bold]", border_style="dim"))

    # Emotions
    if result["emotions"]:
        emo_table = Table(show_header=True, header_style="bold")
        emo_table.add_column("Emotion")
        emo_table.add_column("Intensity")
        for e in result["emotions"]:
            emo_table.add_row(
                e["emotion"].title(),
                f"[{INTENSITY_COLORS[e['intensity']]}]{e['intensity'].upper()}[/{INTENSITY_COLORS[e['intensity']]}]"
            )
        console.print(Panel(emo_table, title="[bold]Emotions Detected[/bold]", border_style="magenta"))

    # Key phrases
    if result["key_phrases"]:
        phrases = "  " + "  |  ".join(f"[yellow]\"{p}\"[/yellow]" for p in result["key_phrases"])
        console.print(Panel(phrases, title="[bold]Key Phrases[/bold]", border_style="yellow"))

    # Aspect sentiments
    if result.get("aspect_sentiments"):
        asp_table = Table(show_header=True, header_style="bold")
        asp_table.add_column("Aspect")
        asp_table.add_column("Sentiment")
        asp_table.add_column("Reason", style="dim")
        for asp in result["aspect_sentiments"]:
            c = SENTIMENT_COLORS[asp["sentiment"]]
            asp_table.add_row(
                asp["aspect"],
                f"[{c}]{asp['sentiment']}[/{c}]",
                asp.get("reason", "")
            )
        console.print(Panel(asp_table, title="[bold]Aspect-Level Sentiment[/bold]", border_style="blue"))

    console.print()


def display_batch_dashboard(results: list[dict], labels: list[str]):
    console.print()
    # Summary stats
    sentiments = [r["sentiment"] for r in results]
    scores = [r["score"] for r in results]
    avg_score = sum(scores) / len(scores)
    counts = {s: sentiments.count(s) for s in ("positive", "negative", "neutral", "mixed")}

    stats_table = Table(show_header=False, box=None, padding=(0, 3))
    stats_table.add_column(style="dim")
    stats_table.add_column()
    stats_table.add_row("Total analyzed", str(len(results)))
    stats_table.add_row("Average score", score_bar(avg_score))
    for sent, count in counts.items():
        if count:
            c = SENTIMENT_COLORS[sent]
            pct = int(count / len(results) * 100)
            stats_table.add_row(sent.title(), f"[{c}]{count} ({pct}%)[/{c}]")
    console.print(Panel(stats_table, title="[bold cyan]Batch Analysis Dashboard[/bold cyan]", border_style="cyan"))

    # Per-item table
    detail_table = Table(show_header=True, header_style="bold", show_lines=True)
    detail_table.add_column("#", width=4)
    detail_table.add_column("Label / Preview", ratio=3)
    detail_table.add_column("Sentiment", width=12)
    detail_table.add_column("Score", width=20)
    detail_table.add_column("Top Emotion", ratio=1)

    for i, (result, label) in enumerate(zip(results, labels), 1):
        s = result["sentiment"]
        c = SENTIMENT_COLORS[s]
        top_emo = result["emotions"][0]["emotion"].title() if result["emotions"] else "—"
        detail_table.add_row(
            str(i),
            label[:60] + ("..." if len(label) > 60 else ""),
            f"[{c}]{SENTIMENT_ICONS[s]} {s}[/{c}]",
            score_bar(result["score"]),
            top_emo
        )
    console.print(Panel(detail_table, title="[bold]Individual Results[/bold]", border_style="dim"))
    console.print()


def save_batch_csv(results: list[dict], labels: list[str], output_path: str):
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["index", "label", "sentiment", "score", "confidence", "top_emotion", "summary"])
        for i, (r, label) in enumerate(zip(results, labels), 1):
            top_emo = r["emotions"][0]["emotion"] if r["emotions"] else ""
            writer.writerow([i, label, r["sentiment"], r["score"], r["confidence"], top_emo, r["summary"]])


def process_batch_file(csv_path: str) -> tuple[list[str], list[str]]:
    """Read texts from a CSV. Expects columns: text (required), label (optional)."""
    texts, labels = [], []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = row.get("text") or row.get("review") or row.get("content") or list(row.values())[0]
            label = row.get("label") or row.get("id") or text[:40]
            texts.append(text.strip())
            labels.append(label.strip())
    return texts, labels


def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow]")
        console.print("  python dashboard.py \"<text to analyze>\"")
        console.print("  python dashboard.py --batch reviews.csv")
        console.print('[dim]Example: python dashboard.py "The product exceeded my expectations!"[/dim]')
        sys.exit(1)

    if sys.argv[1] == "--batch":
        if len(sys.argv) < 3:
            console.print("[red]Provide a CSV file path after --batch[/red]")
            sys.exit(1)

        csv_path = sys.argv[2]
        if not os.path.exists(csv_path):
            console.print(f"[red]File not found:[/red] {csv_path}")
            sys.exit(1)

        texts, labels = process_batch_file(csv_path)
        console.print(f"\n[cyan]Batch analyzing {len(texts)} items from:[/cyan] {csv_path}\n")

        results = []
        for text in track(texts, description="Analyzing..."):
            results.append(analyze_sentiment(text))

        display_batch_dashboard(results, labels)

        output = f"sentiment_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        save_batch_csv(results, labels, output)
        console.print(f"[green]Results saved to:[/green] {output}\n")

    else:
        text = sys.argv[1]
        with console.status("[bold green]Analyzing sentiment...[/bold green]"):
            result = analyze_sentiment(text)
        display_single(result, text)


if __name__ == "__main__":
    main()
