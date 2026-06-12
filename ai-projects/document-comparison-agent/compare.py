"""
Document Comparison Agent
Compares two documents (text or PDF) and identifies differences,
similarities, conflicts, and produces a structured diff report.
"""

import os
import sys
import json
import time
from functools import wraps
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

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


def _is_retryable_openai_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in (429, 500, 502, 503, 504):
        return True

    exc_name = exc.__class__.__name__
    retryable_names = {
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
    }
    return exc_name in retryable_names


def retry_with_backoff(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exception = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not _is_retryable_openai_error(e):
                    raise
                last_exception = e
                if attempt < len(delays):
                    time.sleep(delays[attempt])
                else:
                    raise last_exception
    return wrapper


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


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("❌ Missing OPENAI_API_KEY. Set it in your environment or .env file.")
        sys.exit(1)

    file_args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    for file_path in file_args:
        path = Path(file_path)
        if not path.exists():
            console.print(f"❌ File not found: {file_path}")
            sys.exit(1)
        if not path.is_file():
            console.print(f"❌ Not a file: {file_path}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"❌ File is not readable: {file_path}")
            sys.exit(1)

    console.print("Setup OK ✓")


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


@retry_with_backoff
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
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)


def main():
    validate_environment()


class RetryWithBackoffTests(unittest.TestCase):
    class _RetryableError(Exception):
        def __init__(self, status_code=429):
            super().__init__("retryable")
            self.status_code = status_code

    @patch("time.sleep")
    def test_retry_success_first_try_no_sleep(self, sleep_mock):
        fn = Mock(return_value="ok")
        wrapped = retry_with_backoff(fn)
