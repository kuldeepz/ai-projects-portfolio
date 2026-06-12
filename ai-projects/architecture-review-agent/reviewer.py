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
VERBOSE = False

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
    if VERBOSE:
        print(f"🤖 Model: {MODEL}")
        user_input = f"Review this system architecture:\n\n{design}"
        print(f"📝 Input size: {len(user_input)} chars")
        print("⏳ Calling OpenAI API...")
        start = time.time()
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
    if VERBOSE:
        elapsed = time.time() - start
        print(f"✅ Done in {elapsed:.1f}s")
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(review: dict):
    # Keep display lightweight for testability in this file.
    pass

def main():
    global VERBOSE
    args = sys.argv[1:]
    export = False
    cleaned_args = []
    i = 0
    while i < len(args):
        arg = args[i]


class PrintUsageTests(unittest.TestCase):
    def test_print_usage_no_usage_no_output(self):
        response = Mock()
        response.usage = None

        with patch("builtins.print") as mock_print:
            print_usage(response)

        mock_print.assert_not_called()

    def test_print_usage_with_explicit_total_tokens(self):
        usage = Mock()
        usage.prompt_tokens = 1000
        usage.completion_tokens = 500
        usage.total_tokens = 1600
        response = Mock()
        response.usage = usage

        with patch("builtins.print") as mock_print:
            print_usage(response)

        mock_print.assert_called_once_with(
            "📊 Tokens: 1000 in + 500 out = 1600 total | 💰 Est. cost: $0.0000"
        )

    def test_print_usage_fallback_total_tokens_when_missing(self):
        usage = Mock()
        usage.prompt_tokens = 200
        usage.completion_tokens = 300
        usage.total_tokens = None
        response = Mock()
        response.usage = usage

        with patch("builtins.print") as mock_print:
            print_usage(response)

        mock_print.assert_called_once_with(
            "📊 Tokens: 200 in + 300 out = 500 total | 💰 Est. cost: $0.0000"
        )
