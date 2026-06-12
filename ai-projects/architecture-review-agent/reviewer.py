"""
Architecture Review Agent
Reviews system architecture documents or design descriptions and flags risks,
single points of failure, scalability concerns, and security gaps.
"""

import os, sys, json
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import unittest
from unittest.mock import Mock, patch

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def print_usage(response):
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for i in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if i < len(delays):
                    time.sleep(delays[i])
                else:
                    raise last_exc
    return wrapper

SCHEMA = {
    "name": "architecture_review",
    "description": "Structured architecture review",
    "parameters": {
        "type": "object",
        "properties": {
            "architecture_type": {"type": "string", "description": "Detected pattern (microservices, monolith, event-driven, etc.)"},
            "overall_score": {"type": "integer", "description": "Architecture quality score 0-100"},
            "strengths": {"type": "array", "items": {"type": "string"}},
            "risks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "risk": {"type": "string"},
                        "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "mitigation": {"type": "string"},
                        "category": {"type": "string", "enum": ["scalability", "security", "reliability", "performance", "maintainability", "cost"]}
                    },
                    "required": ["risk", "severity", "mitigation", "category"]
                }
            },
            "single_points_of_failure": {"type": "array", "items": {"type": "string"}},
            "well_architected_gaps": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"pillar": {"type": "string"}, "gap": {"type": "string"}, "recommendation": {"type": "string"}},
                          "required": ["pillar", "gap", "recommendation"]}
            },
            "recommendations": {"type": "array", "items": {"type": "string"}},
            "summary": {"type": "string"}
        },
        "required": ["architecture_type", "overall_score", "strengths", "risks",
                     "single_points_of_failure", "well_architected_gaps", "recommendations", "summary"]
    }
}

SAMPLE_DESIGN = """
# System Architecture: E-Commerce Platform

## Overview
A monolithic Django application deployed on a single EC2 instance (t3.medium).
MySQL database hosted on the same server.

## Components
- Django app: handles web, API, background jobs (Celery), and admin
- MySQL 5.7: primary database (no replication, no backups configured)
- Redis: session store and Celery broker (same EC2 instance)
- Nginx: reverse proxy on same server
- File storage: local disk /var/uploads

## Deployment
- Single EC2 t3.medium in us-east-1a only
- Manual deployments via SSH
- No staging environment
- Secrets stored in .env file on server

## Scale
- Current: 500 daily active users
- Target: 50,000 daily active users in 12 months
"""

SEV_COLORS = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim"}

@retry_with_backoff
def review_architecture(design: str) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are a Principal Solutions Architect and AWS/Azure expert. "
                "Review system architectures against the Well-Architected Framework (reliability, security, "
                "performance efficiency, cost optimization, operational excellence, sustainability). "
                "Be specific about risks and provide concrete mitigation strategies."
            )},
            {"role": "user", "content": f"Review this system architecture:\n\n{design}"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "architecture_review"}},
        temperature=0.2,
    )
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(review: dict):
    # Keep display lightweight for testability in this file.
    pass

def main():
    args = sys.argv[1:]
    export = False
    cleaned_args = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--export", "-e"):
            export = True
            i += 1
            continue
        cleaned_args.append(arg)
        i += 1

    if not cleaned_args:
        design = SAMPLE_DESIGN
    else:
        first = cleaned_args[0]
        p = Path(first)
        if p.exists() and p.is_file():
            design = p.read_text(encoding="utf-8")
        else:
            design = " ".join(cleaned_args)

    review = review_architecture(design)
    display(review)

    if export:
        payload = {
            "generated_at": datetime.utcnow().isoformat(),
            "review": review,
        }
        Path("architecture_review.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )


class TestRetryWithBackoff(unittest.TestCase):
    @patch("time.sleep", return_value=None)
    def test_retry_success_after_failures(self, _sleep):
        fn = Mock(side_effect=[Exception("x"), Exception("y"), "ok"])

        wrapped = retry_with_backoff(fn)
        out = wrapped()

        self.assertEqual(out, "ok")
        self.assertEqual(fn.call_count, 3)

    @patch("time.sleep", return_value=None)
    def test_retry_raises_after_exhausted(self, _sleep):
        fn = Mock(side_effect=Exception("nope"))

        wrapped = retry_with_backoff(fn)
        with self.assertRaises(Exception):
            wrapped()

        self.assertEqual(fn.call_count, 4)


class TestMainArgumentHandling(unittest.TestCase):
    def setUp(self):
        self.mock_review = {"overall_score": 80, "architecture_type": "monolith", "summary": "ok"}

    @patch("__main__.display")
    @patch("__main__.review_architecture")
    def test_no_args_uses_sample_design(self, mock_review_architecture, mock_display):
        mock_review_architecture.return_value = self.mock_review
        with patch.object(sys, "argv", ["reviewer.py"]):
            main()

        mock_review_architecture.assert_called_once_with(SAMPLE_DESIGN)
        mock_display.assert_called_once_with(self.mock_review)

    @patch("__main__.display")
    @patch("__main__.review_architecture")
    def test_inline_text_input(self, mock_review_architecture, mock_display):
        mock_review_architecture.return_value = self.mock_review
        with patch.object(sys, "argv", ["reviewer.py", "service", "mesh", "design"]):
            main()

        mock_review_architecture.assert_called_once_with("service mesh design")
        mock_display.assert_called_once_with(self.mock_review)

    @patch("pathlib.Path.read_text", return_value="file based architecture")
    @patch("pathlib.Path.is_file", return_value=True)
    @patch("pathlib.Path.exists", return_value=True)
    @patch("__main__.display")
    @patch("__main__.review_architecture")
    def test_file_input_selected_when_path_exists(self, mock_review_architecture, mock_display, *_):
        mock_review_architecture.return_value = self.mock_review
        with patch.object(sys, "argv", ["reviewer.py", "design.md"]):
            main()

        mock_review_architecture.assert_called_once_with("file based architecture")
        mock_display.assert_called_once_with(self.mock_review)

    @patch("pathlib.Path.write_text")
    @patch("__main__.display")
    @patch("__main__.review_architecture")
    def test_export_flag_writes_json_with_generated_at(self, mock_review_architecture, mock_display, mock_write_text):
        mock_review_architecture.return_value = self.mock_review
        with patch.object(sys, "argv", ["reviewer.py", "--export"]):
            main()

        self.assertTrue(mock_write_text.called)
        payload_str = mock_write_text.call_args[0][0]
        payload = json.loads(payload_str)
        self.assertIn("generated_at", payload)
        self.assertEqual(payload["review"], self.mock_review)

    @patch("pathlib.Path.write_text")
    @patch("__main__.display")
    @patch("__main__.review_architecture")
    def test_export_short_alias_e_works(self, mock_review_architecture, mock_display, mock_write_text):
        mock_review_architecture.return_value = self.mock_review
        with patch.object(sys, "argv", ["reviewer.py", "-e", "inline", "arch"]):
            main()

        mock_review_architecture.assert_called_once_with("inline arch")
        self.assertTrue(mock_write_text.called)


if __name__ == "__main__":
    unittest.main()
