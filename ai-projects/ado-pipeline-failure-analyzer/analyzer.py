"""
ADO Pipeline Failure Analyzer
Reads a CI/CD pipeline log (text file or pasted), diagnoses the root cause,
and provides a step-by-step remediation plan.
"""

import os, sys, json
import time
import argparse
from functools import wraps
from datetime import datetime
from pathlib import Path
from typing import Any, TypedDict, NotRequired, Literal, Protocol, cast
from dotenv import load_dotenv
from openai import OpenAI, APIConnectionError, RateLimitError, APITimeoutError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

load_dotenv()
console: Console = Console()
MODEL: str = "gpt-4o-mini"
VERBOSE: bool = False


def parse_cli_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true", help="Show OpenAI call diagnostics")
    parser.add_argument("--export", "-e", nargs="?", const=True, default=False, help="Export diagnosis JSON (optionally provide output file path)")
    return parser.parse_args()


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        console.print("❌ Setup error: OPENAI_API_KEY is missing or empty.")
        console.print("Set it in your environment or .env file, then retry.")
        sys.exit(1)

    path_args = [arg for arg in sys.argv[1:] if arg and not arg.startswith("-")]
    for raw_path in path_args:
        path = Path(raw_path)
        if not path.exists():
            console.print(f"❌ Setup error: file path does not exist: {path}")
            sys.exit(1)
        if not path.is_file():
            console.print(f"❌ Setup error: path is not a file: {path}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"❌ Setup error: file is not readable: {path}")
            sys.exit(1)

    console.print("Setup OK ✓")


def retry_with_backoff(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exception = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except (APIConnectionError, RateLimitError, APITimeoutError) as e:
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


def export_diagnosis_json(diagnosis: dict[str, Any], export_arg: object) -> None:
    if not export_arg:
        return

    if isinstance(export_arg, str):
        out_file = Path(export_arg)
        out_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        out_dir = Path("exports")
        out_dir.mkdir(exist_ok=True)
        out_file = out_dir / f"diagnosis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

    out_file.write_text(json.dumps(diagnosis, indent=2), encoding="utf-8")
    console.print(f"[green]Exported JSON:[/green] {out_file}")
