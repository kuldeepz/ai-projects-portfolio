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


def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if attempt == len(delays):
                    raise
                time.sleep(delays[attempt])
        raise last_exc
    return wrapper


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
            )


if __name__ == "__main__" and os.getenv("PYTEST_CURRENT_TEST"):
    import unittest
    from unittest.mock import patch, MagicMock

    class RetryWithBackoffTests(unittest.TestCase):
        def test_retry_succeeds_immediately(self):
            calls = {"n": 0}

            def fn():
                calls["n"] += 1
                return "ok"

            wrapped = retry_with_backoff(fn)
            with patch("time.sleep") as sleep_mock:
                self.assertEqual(wrapped(), "ok")
                self.assertEqual(calls["n"], 1)
                sleep_mock.assert_not_called()

        def test_retry_fails_twice_then_succeeds(self):
            calls = {"n": 0}

            def fn():
                calls["n"] += 1
                if calls["n"] < 3:
                    raise RuntimeError("transient")
                return "ok"

            wrapped = retry_with_backoff(fn)
            with patch("time.sleep") as sleep_mock:
                self.assertEqual(wrapped(), "ok")
                self.assertEqual(calls["n"], 3)
                self.assertEqual([c.args[0] for c in sleep_mock.call_args_list], [1, 2])

        def test_retry_exhausted_raises_original(self):
            calls = {"n": 0}
            exc = ValueError("boom")

            def fn():
                calls["n"] += 1
                raise exc

            wrapped = retry_with_backoff(fn)
            with patch("time.sleep") as sleep_mock:
                with self.assertRaises(ValueError) as ctx:
                    wrapped()
                self.assertIs(ctx.exception, exc)
                self.assertEqual(calls["n"], 4)
                self.assertEqual([c.args[0] for c in sleep_mock.call_args_list], [1, 2, 4])

    class AnalyzeSentimentRetryIntegrationTests(unittest.TestCase):
        def _mock_response(self):
            response = MagicMock()
            response.choices = [MagicMock()]
            response.choices[0].message.tool_calls = [MagicMock()]
            response.choices[0].message.tool_calls[0].function.arguments = json.dumps({
                "sentiment": "positive",
                "score": 0.8,
                "confidence": 92,
                "emotions": [{"emotion": "joy", "intensity": "high"}],
                "key_phrases": ["great experience"],
                "summary": "Overall positive sentiment."
            })
            return response

        def test_analyze_sentiment_retries_on_transient_client_errors(self):
            create_mock = MagicMock(side_effect=[RuntimeError("t1"), RuntimeError("t2"), self._mock_response()])
            client = MagicMock()
            client.chat.completions.create = create_mock

            with patch(__name__ + ".get_client", return_value=client), patch("time.sleep") as sleep_mock:
                result = analyze_sentiment("text")

            self.assertEqual(create_mock.call_count, 3)
            self.assertEqual([c.args[0] for c in sleep_mock.call_args_list], [1, 2])
            self.assertEqual(result["sentiment"], "positive")

    unittest.main()
