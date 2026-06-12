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
import time
import random
from pathlib import Path
from datetime import datetime
from functools import wraps

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

load_dotenv()

console = Console()
CHAT_MODEL = "gpt-4o-mini"
VERBOSE = False

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[bold red]Setup error:[/bold red] OPENAI_API_KEY is not set. Please add it to your environment or .env file.")
        sys.exit(1)

    path_args = [arg for arg in sys.argv[1:] if arg and not arg.startswith("-")]
    for raw_arg in path_args:
        candidate = Path(raw_arg)
        if candidate.exists():
            if not candidate.is_file():
                console.print(f"[bold red]Setup error:[/bold red] Path is not a file: {candidate}")
                sys.exit(1)
            if not os.access(candidate, os.R_OK):
                console.print(f"[bold red]Setup error:[/bold red] File is not readable: {candidate}")
                sys.exit(1)

    console.print("[bold green]Setup OK ✓[/bold green]")


def retry_with_backoff(func=None, *, retries=3, base_delay=1.0, max_delay=8.0, jitter=0.2):
    def deco(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            for attempt in range(retries + 1):
                try:
                    return f(*args, **kwargs)
                except Exception:
                    if attempt == retries:
                        raise
                    delay = min(max_delay, base_delay * (2 ** attempt))
                    delay *= random.uniform(1 - jitter, 1 + jitter)
                    time.sleep(delay)
        return wrapper

    return deco(func) if func else deco


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


@retry_with_backoff
def analyze_sentiment(text: str) -> dict:
    if VERBOSE:
        console.print(f"[dim]Model: {CHAT_MODEL}[/dim]")
        console.print(f"[dim]Input size: {len(text)} chars, ~{max(1, len(text) // 4)} tokens[/dim]")
        console.print("⏳ Calling OpenAI API...")
        started = time.time()
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
    if VERBOSE:
        console.print(f"✅ Done in {time.time() - started:.1f}s")
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

INTENSITY_COLORS = {"low": "dim", "medium": "yellow", "high": "red"}
