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
    score = review["overall_score"]
    s_color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]Architecture: {review['architecture_type']}[/bold]\n"
        f"Score: [{s_color} bold]{score}/100[/{s_color} bold]",
        title="[bold cyan]Architecture Review[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{review['summary']}[/italic]", title="Summary", border_style="dim"))

    if review["strengths"]:
        console.print(Panel("\n".join(f"  [green]✔[/green] {s}" for s in review["strengths"]),
                            title="[bold green]Strengths[/bold green]"))


def main():
    args = sys.argv[1:]
    export = False
    if "--export" in args or "-e" in args:
        export = True
        args = [a for a in args if a not in ("--export", "-e")]

    if args and Path(args[0]).exists():
        design = Path(args[0]).read_text(encoding="utf-8")
    elif args:
        design = " ".join(args)
    else:
        design = SAMPLE_DESIGN

    review = review_architecture(design)
    display(review)

    if export:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{ts}.json"
        payload = dict(review)
        payload["generated_at"] = datetime.now().isoformat()
        Path(filename).write_text(json.dumps(payload, indent=2), encoding="utf-8")


class TestRetryWithBackoff(unittest.TestCase):
    def test_success_first_try_no_sleep(self):
        fn = Mock(return_value="ok")
        wrapped = retry_with_backoff(fn)

        with patch("time.sleep") as sleep_mock:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 1)
        sleep_mock.assert_not_called()

    def test_fail_then_success_retries_and_sleeps(self):
        fn = Mock(side_effect=[Exception("e1"), Exception("e2"), "ok"])
        wrapped = retry_with_backoff(fn)

        with patch("time.sleep") as sleep_mock:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(fn.call_count, 3)
        self.assertEqual(sleep_mock.call_count, 2)
        sleep_mock.assert_any_call(1)
        sleep_mock.assert_any_call(2)

    def test_retries_exhausted_raises_and_sleep_count(self):
        err = Exception("always fail")
        fn = Mock(side_effect=err)
        wrapped = retry_with_backoff(fn)

        with patch("time.sleep") as sleep_mock:
            with self.assertRaises(Exception) as ctx:
                wrapped()

        self.assertIs(ctx.exception, err)
        self.assertEqual(fn.call_count, 4)
        self.assertEqual(sleep_mock.call_count, 3)
        sleep_mock.assert_any_call(1)
        sleep_mock.assert_any_call(2)
        sleep_mock.assert_any_call(4)


if __name__ == "__main__":
    main()
