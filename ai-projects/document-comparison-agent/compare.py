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
from unittest.mock import patch, Mock, mock_open

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
                    with console.status("[bold green]Processing..."):
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
        with console.status("[bold green]Processing..."):
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(p.extract_text() or "" for p in reader.pages)
    with console.status("[bold green]Processing..."):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


@retry_with_backoff
def compare_documents(text1: str, text2: str, doc1_name: str, doc2_name: str, context: str = ""):
    with console.status("[bold green]Processing..."):
        client = get_client()
        prompt = f"Compare {doc1_name} and {doc2_name}.\n\n{text1}\n\n{text2}\n\n{context}".strip()
        return client.responses.create(
            model=CHAT_MODEL,
            input=prompt,
        )


class TestSpinnerStatusBehavior(unittest.TestCase):
    def _status_cm(self):
        cm = Mock()
        cm.__enter__ = Mock(return_value=None)
        cm.__exit__ = Mock(return_value=None)
        return cm

    @patch("compare.time.sleep", return_value=None)
    @patch("compare.console.status")
    def test_retry_with_backoff_enters_status_on_retry(self, mock_status, _mock_sleep):
        mock_status.return_value = self._status_cm()

        class RetryableError(Exception):
            status_code = 429

        calls = {"count": 0}

        @retry_with_backoff
        def flaky():
            calls["count"] += 1
            if calls["count"] == 1:
                raise RetryableError("rate limited")
            return "ok"

        result = flaky()
        self.assertEqual(result, "ok")
        mock_status.assert_called_once_with("[bold green]Processing...")

    @patch("compare.PyPDF2.PdfReader")
    @patch("compare.open", new_callable=mock_open)
    @patch("compare.console.status")
    def test_read_document_pdf_enters_status_once(self, mock_status, _mock_file, mock_reader):
        mock_status.return_value = self._status_cm()
        page = Mock()
        page.extract_text.return_value = "hello"
        mock_reader.return_value.pages = [page]

        text = read_document("doc.pdf")
        self.assertEqual(text, "hello")
        mock_status.assert_called_once_with("[bold green]Processing...")

    @patch("compare.open", new_callable=mock_open, read_data="plain text")
    @patch("compare.console.status")
    def test_read_document_text_enters_status_once(self, mock_status, _mock_file):
        mock_status.return_value = self._status_cm()

        text = read_document("doc.txt")
        self.assertEqual(text, "plain text")
        mock_status.assert_called_once_with("[bold green]Processing...")

    @patch("compare.get_client")
    @patch("compare.console.status")
    def test_compare_documents_enters_status_once(self, mock_status, mock_get_client):
        mock_status.return_value = self._status_cm()
        mock_client = Mock()
        mock_client.responses.create.return_value = {"ok": True}
        mock_get_client.return_value = mock_client

        result = compare_documents("a", "b", "doc1", "doc2")
        self.assertEqual(result, {"ok": True})
        mock_status.assert_called_once_with("[bold green]Processing...")


if __name__ == "__main__":
    unittest.main()
