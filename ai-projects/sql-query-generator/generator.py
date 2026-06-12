import json
import os
import sys
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Protocol, TypedDict

from rich.console import Console

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


console: Console = Console()


class UsageLike(Protocol):
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None


class ResponseOutputItemLike(Protocol):
    type: str | None
    name: str | None
    arguments: str


class ResponseLike(Protocol):
    usage: UsageLike | None
    output: list[ResponseOutputItemLike]


class ResponsesAPI(Protocol):
    def create(self, **kwargs: Any) -> ResponseLike: ...


class OpenAIClientLike(Protocol):
    responses: ResponsesAPI


class SQLResult(TypedDict):
    sql: str


def retry_with_backoff(func: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        delays: list[int] = [1, 2, 4]
        last_exc: TimeoutError | ConnectionError | None = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except (TimeoutError, ConnectionError) as exc:
                last_exc = exc
                if attempt < len(delays):
                    time.sleep(delays[attempt])
                else:
                    raise last_exc

    return wrapper


@retry_with_backoff
def _create_response(client: OpenAIClientLike, **kwargs: Any) -> ResponseLike:
    return client.responses.create(**kwargs)


def print_usage(response: ResponseLike) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "input_tokens", 0) or 0
    completion_tokens = getattr(usage, "output_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(
        f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}"
    )


def get_client() -> OpenAIClientLike:
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def validate_environment(schema_paths: list[str] | None = None, require_api_key: bool = True) -> None:
    if require_api_key and not os.environ.get("OPENAI_API_KEY"):
        console.print("[red]OPENAI_API_KEY is not set[/red]")
        raise SystemExit(1)

    if schema_paths:
        for path in schema_paths:
            if not Path(path).exists():
                console.print(f"[red]Schema file not found: {path}[/red]")
                raise SystemExit(1)


def load_schema(schema_paths: list[str]) -> str:
    with console.status("Loading schema..."):
        parts: list[str] = []
        for path in schema_paths:
            p = Path(path)
            if not p.exists():
                console.print(f"[red]Schema file not found: {path}[/red]")
                raise SystemExit(1)
            parts.append(p.read_text())
        return "\n\n".join(parts)


def generate_sql(prompt: str, schema_paths: list[str]) -> SQLResult:
    client = get_client()

    with console.status("Generating SQL..."):
        response = _create_response(
            client,
            model="gpt-4.1-mini",
            input=prompt,
            tools=[
                {
                    "type": "function",
                    "name": "emit_sql",
                    "description": "Emit generated SQL",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string"},
                        },
                        "required": ["sql"],
                    },
                }
            ],
        )
    print_usage(response)

    for item in getattr(response, "output", []):
        if getattr(item, "type", None) == "function_call" and getattr(item, "name", None) == "emit_sql":
            return json.loads(item.arguments)

    return {"sql": ""}


def interactive_mode(schema_paths: list[str] | None = None, export: bool = False) -> None:
    all_results: list[dict[str, Any]] = []
    while True:
        try:
            prompt = input("sql> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break

        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            break

        result = generate_sql(prompt, schema_paths or [])
        all_results.append({"prompt": prompt, "result": result})
        console.print(result.get("sql", ""))

    if export:
        generated_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
        output_path = Path(f"output_{timestamp}.json")
        payload = {
            "generated_at": generated_at,
            "results": all_results,
        }
        output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", action="append", default=[])
    parser.add_argument("-e", "--export", action="store_true")
    args = parser.parse_args()

    validate_environment(schema_paths=args.schema, require_api_key=True)
    interactive_mode(schema_paths=args.schema, export=args.export)


if __name__ == "__main__":
    main()


# ---------------------------
# Unit tests
# ---------------------------

import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestPrintUsage(unittest.TestCase):
    def test_print_usage_no_usage_prints_nothing(self) -> None:
        response = SimpleNamespace(usage=None)
        with patch.object(console, "print") as mock_print:
            print_usage(response)
        mock_print.assert_not_called()

    def test_print_usage_fallback_total_tokens_when_missing(self) -> None:
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        response = SimpleNamespace(usage=usage)
        with patch.object(console, "print") as mock_print:
            print_usage(response)
        mock_print.assert_called_once()
        message = mock_print.call_args[0][0]
        self.assertIn("100 in + 50 out = 150 total", message)

    def test_print_usage_uses_provided_total_tokens(self) -> None:
        usage = SimpleNamespace(input_tokens=100, output_tokens=50, total_tokens=999)
        
