"""
Document Comparison Agent
Compares two documents (text or PDF) and identifies differences,
similarities, conflicts, and produces a structured diff report.
"""

import os
import sys
import json
import time
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
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)


class RetryWithBackoffTests(unittest.TestCase):
    class _RetryableError(Exception):
        def __init__(self, status_code=429):
            super().__init__("retryable")
            self.status_code = status_code

    @patch("time.sleep")
    def test_retry_success_first_try_no_sleep(self, sleep_mock):
        fn = Mock(return_value="ok")
        wrapped = retry_with_backoff(fn)

        result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 1)
        sleep_mock.assert_not_called()

    @patch("time.sleep")
    def test_retry_success_after_retries_uses_backoff_sequence(self, sleep_mock):
        fn = Mock(side_effect=[self._RetryableError(429), self._RetryableError(500), "ok"])
        wrapped = retry_with_backoff(fn)

        result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)
        sleep_mock.assert_any_call(1)
        sleep_mock.assert_any_call(2)

    @patch("time.sleep")
    def test_retry_exhausted_retries_propagates_final_exception(self, sleep_mock):
        err = self._RetryableError(503)
        fn = Mock(side_effect=[err, err, err, err])
        wrapped = retry_with_backoff(fn)

        with self.assertRaises(self._RetryableError):
            wrapped()

        self.assertEqual(fn.call_count, 4)
        self.assertEqual([c.args[0] for c in sleep_mock.call_args_list], [1, 2, 4])


class CompareDocumentsRetryIntegrationTests(unittest.TestCase):
    class _RetryableError(Exception):
        def __init__(self, status_code=429):
            super().__init__("retryable")
            self.status_code = status_code

    @patch("time.sleep")
    @patch(__name__ + ".get_client")
    def test_compare_documents_retries_then_succeeds(self, get_client_mock, sleep_mock):
        final_payload = {"doc1_summary": "a", "doc2_summary": "b", "overall_similarity": 90,
                         "common_themes": [], "unique_to_doc1": [], "unique_to_doc2": [],
                         "conflicts": [], "recommendation": "ok"}

        response_mock = Mock()
        response_mock.choices = [
            Mock(message=Mock(tool_calls=[Mock(function=Mock(arguments=json.dumps(final_payload)))]))
        ]

        create_mock = Mock(side_effect=[self._RetryableError(429), response_mock])
        get_client_mock.return_value = Mock(
            chat=Mock(completions=Mock(create=create_mock))
        )

        result = compare_documents("t1", "t2", "d1", "d2")

        self.assertEqual(result, final_payload)
        self.assertEqual(create_mock.call_count, 2)
        sleep_mock.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
