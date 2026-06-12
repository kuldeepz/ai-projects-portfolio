"""
Document Comparison Agent
Compares two documents (text or PDF) and identifies differences,
similarities, conflicts, and produces a structured diff report.
"""

import argparse
import os
import sys
import json
import time
from functools import wraps
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
VERBOSE = False

MODEL_PRICING = {
    "gpt-4o-mini": {"in_per_1m": 0.15, "out_per_1m": 0.60},
}

_client = None


class StartupValidationError(Exception):
    pass


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
                    delay = delays[attempt]
                    with console.status(f"[yellow]Retrying in {delay}s (attempt {attempt + 1})..."):
                        time.sleep(delay)
                else:
                    raise last_exception
    return wrapper


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def print_usage(response) -> None:
    if not VERBOSE:
        return
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0

    pricing = MODEL_PRICING.get(CHAT_MODEL)
    if pricing:
        cost = (prompt_tokens / 1_000_000) * pricing["in_per_1m"] + (
            completion_tokens / 1_000_000
        ) * pricing["out_per_1m"]
        cost_text = f"${cost:.4f}"
    else:
        cost_text = "N/A (unknown model pricing)"

    console.print(
        f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: {cost_text}"
    )


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        raise StartupValidationError("Missing OPENAI_API_KEY. Set it in your environment or .env file.")

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("doc1")
    parser.add_argument("doc2")
    parser.add_argument("-v", "--verbose", action="store_true")
    args, _ = parser.parse_known_args(sys.argv[1:])

    global VERBOSE
    VERBOSE = args.verbose

    for file_path in (args.doc1, args.doc2):
        path = Path(file_path)
        if not path.exists():
            raise StartupValidationError(f"File not found: {file_path}")
        if not path.is_file():
            raise StartupValidationError(f"Not a file: {file_path}")
        if not os.access(path, os.R_OK):
            raise StartupValidationError(f"File is not readable: {file_path}")

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
        with console.status("[cyan]Reading PDF..."):
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return
