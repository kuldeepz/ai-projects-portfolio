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
VERBOSE: bool = False


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
    if VERBOSE:
        model = kwargs.get("model", MODEL)
        messages = kwargs.get("messages", [])
        input_text = "\n".join(
            m.get("content", "") if isinstance(m.get("content", ""), str) else str(m.get("content", ""))
            for m in messages
            if isinstance(m, dict)
        )
        chars = len(input_text)
        approx_tokens = max(1, chars // 4) if chars > 0 else 0
        console.print(f"[dim]Model:[/dim] {model}")
        console.print(f"[dim]Input size:[/dim] {chars} chars (~{approx_tokens} tokens)")
        console.print("⏳ Calling OpenAI API...")
        start = time.perf_counter()
        response = get_client().chat.completions.create(**kwargs)
        elapsed = time.perf_counter() - start
        console.print(f"✅ Done in {elapsed:.1f}s")
        return response
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

===========================
"""


def _run_self_tests() -> None:
    from types import SimpleNamespace

    class _FakeCreate:
        def __init__(self):
            self.calls = []
            self.side_effects = []

        def create(self, **kwargs):
            self.calls.append(kwargs)
            if self.side_effects:
                effect = self.side_effects.pop(0)
                if isinstance(effect, Exception):
                    raise effect
                return effect
            return {"ok": True}

    class _FakeClient:
        def __init__(self):
            self.chat = SimpleNamespace(completions=_FakeCreate())

    global VERBOSE

    original_verbose = VERBOSE
    original_get_client = globals()["get_client"]
    original_console_print = console.print
    original_sleep = time.sleep
    original_perf_counter = time.perf_counter

    try:
        # (1) VERBOSE=False -> one API call, no diagnostics
        fake_client = _FakeClient()
        globals()["get_client"] = lambda: fake_client
        VERBOSE = False
        printed = []
        console.print = lambda *args, **kwargs: printed.append((args, kwargs))
        result = create_chat_completion(model="m1", messages=[{"content": "hello"}])
        assert result == {"ok": True}
        assert len(fake_client.chat.completions.calls) == 1
        assert printed == []

        # (2) VERBOSE=True -> diagnostics printed, API still called once
        fake_client = _FakeClient()
        globals()["get_client"] = lambda: fake_client
        VERBOSE = True
        printed = []
        ticks = iter([100.0, 100.5])
        time.perf_counter = lambda: next(ticks)
        console.print = lambda *args, **kwargs: printed.append(args[0] if args else "")
        result = create_chat_completion(model="m2", messages=[{"content": "abcd"}, {"content": "efgh"}])
        assert result == {"ok": True}
        assert len(fake_client.chat.completions.calls) == 1
        out = "\n".join(str(x) for x in printed)
        assert "Model:" in out
        assert "Input size:" in out
        assert "Calling OpenAI API" in out
        assert "Done in" in out

        # (3) retry logic -> retries transient errors then succeeds
        fake_client = _FakeClient()
        fake_client.chat.completions.side_effects = [RuntimeError("t1"), RuntimeError("t2"), {"ok": "final"}]
        globals()["get_client"] = lambda: fake_client
        VERBOSE = False
        sleeps = []
        time.sleep = lambda d: sleeps.append(d)
        result = create_chat_completion(model="m3", messages=[{"content": "x"}])
        assert result == {"ok": "final"}
        assert len(fake_client.chat.completions.calls) == 3
        assert sleeps == [1, 2]

    finally:
        VERBOSE = original_verbose
        globals()["get_client"] = original_get_client
        console.print = original_console_print
        time.sleep = original_sleep
        time.perf_counter = original_perf_counter


if __name__ == "__main__" and "--self-test" in sys.argv:
    _run_self_tests()
    print("self-tests passed")
