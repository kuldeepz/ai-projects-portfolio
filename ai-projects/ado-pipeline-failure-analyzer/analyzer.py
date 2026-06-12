"""
ADO Pipeline Failure Analyzer
Reads a CI/CD pipeline log (text file or pasted), diagnoses the root cause,
and provides a step-by-step remediation plan.
"""

import os, sys, json
import time
from pathlib import Path
from typing import Any, TypedDict, NotRequired, Literal, Protocol, cast
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

load_dotenv()
console: Console = Console()
MODEL: str = "gpt-4o-mini"


def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exception = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if i == len(delays) - 1:
                    raise
                time.sleep(delay)
        if last_exception is not None:
            raise last_exception
    return wrapper


class UsageLike(Protocol):
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ResponseLike(Protocol):
    usage: UsageLike | None


class FixStep(TypedDict):
    step: int
    action: str
    command: NotRequired[str]


class Diagnosis(TypedDict):
    failure_stage: str
    root_cause: str
    error_type: Literal[
        "compilation_error",
        "test_failure",
        "dependency_error",
        "config_error",
        "permission_error",
        "timeout",
        "network_error",
        "resource_error",
        "unknown",
    ]
    severity: Literal["blocking", "warning", "flaky"]
    affected_files: NotRequired[list[str]]
    fix_steps: list[FixStep]
    prevention_tips: list[str]
    estimated_fix_time: NotRequired[str]


class JsonSchema(TypedDict):
    name: str
    description: str
    parameters: dict[str, object]


_client: OpenAI | None = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


@retry_with_backoff
def create_chat_completion(**kwargs):
    return get_client().chat.completions.create(**kwargs)


def print_usage(response: ResponseLike) -> None:
    usage = response.usage
    if not usage:
        return
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")


SCHEMA: JsonSchema = {
    "name": "pipeline_diagnosis",
    "description": "Root cause analysis of a failed CI/CD pipeline",
    "parameters": {
        "type": "object",
        "properties": {
            "failure_stage": {"type": "string", "description": "Which stage/step failed (build, test, lint, deploy, etc.)"},
            "root_cause": {"type": "string", "description": "Clear explanation of why the pipeline failed"},
            "error_type": {
                "type": "string",
                "enum": ["compilation_error", "test_failure", "dependency_error", "config_error",
                         "permission_error", "timeout", "network_error", "resource_error", "unknown"]
            },
            "severity": {"type": "string", "enum": ["blocking", "warning", "flaky"]},
            "affected_files": {"type": "array", "items": {"type": "string"}},
            "fix_steps": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"step": {"type": "integer"}, "action": {"type": "string"}, "command": {"type": "string"}},
                          "required": ["step", "action"]}
            },
            "prevention_tips": {"type": "array", "items": {"type": "string"}},
            "estimated_fix_time": {"type": "string"}
        },
        "required": ["failure_stage", "root_cause", "error_type", "severity", "fix_steps", "prevention_tips"]
    }
}

SAMPLE_LOG: str = """
##[section]Starting: Run tests
==============================================================================
Task         : Bash
Description  : Run a Bash script on macOS, Linux, or Windows
==============================================================================
/usr/bin/bash /home/vsts/work/1/s/run_tests.sh
+ pytest tests/ --cov=src --cov-report=xml
============================= test session starts ==============================
platform linux -- Python 3.11.4
collected 142 items

tests/test_auth.py::test_login_valid PASSED
tests/test_auth.py::test_login_invalid PASSED
tests/test_api.py::test_create_user PASSED
tests/test_api.py::test_delete_user FAILED

FAILED tests/test_api.py::test_delete_user - AssertionError: assert 404 == 200
Expected: 200 (user deleted successfully)
Actual:   404 (user not found)

ImportError while collecting tests/test_payments.py
  tests/test_payments.py:3: in <module>
    from src.payments import StripeClient
ModuleNotFoundError: No module named 'stripe'

=============================== 2 failed, 140 passed ==============================
##[error]Bash exited with code '1'.
##[section]Finishing: Run tests
"""

def analyze_log(log: str) -> Diagnosis:
    with console.status("[bold green]Processing..."):
        response = create_chat_completion(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a DevOps expert and CI/CD specialist. Analyze pipeline logs to identify "
                    "root causes of failures. Provide specific, actionable fix steps with exact commands where possible."
                )},
                {"role": "user", "content": f"Analyze this pipeline failure log:\n\n{log}"}
            ],
            tools=[{"type": "function", "function": SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "pipeline_diagnosis"}},
            temperature=0.1,
        )
    print_usage(cast(ResponseLike, response))
    return cast(Diagnosis, json.loads(response.choices[0].message.tool_calls[0].function.arguments))

def display(diagnosis: Diagnosis) -> None:
    sev_color = {"blocking": "red", "warning": "yellow", "flaky": "blue"}.get(diagnosis["severity"], "white")
    console.print()
    console.print(Panel.fit(
        f"[bold red]✘ Pipeline Failed[/bold red]\n"
        f"Stage: [bold]{diagnosis['failure_stage']}[/bold]  |  "
        f"Type: [yellow]{diagnosis['error_type']}[/yellow]  |  "
        f"Severity: [{sev_color} bold]{diagnosis['severity'].upper()}[/{sev_color} bold]",
        title="[bold cyan]Pipeline Failure Analysis[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(diagnosis["root_cause"], title="[bold red]Root Cause[/bold red]", border_style="red"))

    t = Table(show_header=True, header_style="bold green")
    t.add_column("Step", width=5); t.add_column("Action", ratio=2); t.add_column("Command", ratio=2)
    for s in diagnosis["fix_steps"]:
        cmd = s.get("command", "—")
        t.add_row(str(s["step"]), s["action"],
                  f"[cyan]{cmd}[/cyan]" if cmd != "—" else "[dim]—[/dim]")
    console.print(Panel(t, title="[bold green]Fix Steps[/bold green]", border_style="green"))

    if diagnosis.get("affected_files"):
        console.print(Panel("\n".join(f"  [yellow]•[/yellow] {f}" for f in diagnosis["affected_files"]),
                            title="[bold]Affected Files[/bold]", border_style="yellow"))

    console.print(Panel("\n".join(f"  [dim]→[/dim] {p}" for p in diagnosis["prevention_tips"]),
                        title="[bold blue]Prevention Tips[/bold blue]", border_style="blue"))
