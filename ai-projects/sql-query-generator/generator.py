import json
import os
import sys
import time
from pathlib import Path

from rich.console import Console

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None


console = Console()

PRICING_PER_1M = {
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}


def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
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
def _create_response(client, **kwargs):
    return client.responses.create(**kwargs)


def print_usage(response, model):
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "input_tokens", 0) or 0
    completion_tokens = getattr(usage, "output_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0

    rates = PRICING_PER_1M.get(model)
    if rates:
        cost = (prompt_tokens / 1_000_000) * rates["input"] + (completion_tokens / 1_000_000) * rates["output"]
        cost_part = f" | 💰 Est. cost: ${cost:.4f} (USD @ per-1M token rates)"
    else:
        cost_part = " | 💰 Est. cost: unavailable (unknown model pricing)"

    console.print(
        f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total{cost_part}"
    )


def get_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


def validate_environment(schema_paths=None, require_api_key=True):
    if require_api_key and not os.environ.get("OPENAI_API_KEY"):
        console.print("[red]OPENAI_API_KEY is not set[/red]")
        raise SystemExit(1)

    if schema_paths:
        for path in schema_paths:
            if not Path(path).exists():
                console.print(f"[red]Schema file not found: {path}[/red]")
                raise SystemExit(1)


def load_schema(schema_paths):
    with console.status("Loading schema..."):
        parts = []
        for path in schema_paths:
            p = Path(path)
            if not p.exists():
                console.print(f"[red]Schema file not found: {path}[/red]")
                raise SystemExit(1)
            parts.append(p.read_text())
        return "\n\n".join(parts)


def generate_sql(prompt, schema_paths):
    client = get_client()
    model = "gpt-4.1-mini"

    with console.status("Generating SQL..."):
        response = _create_response(
            client,
            model=model,
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
    print_usage(response, model)

    for item in getattr(response, "output", []):
        if getattr(item, "type", None) == "function_call" and getattr(item, "name", None) == "emit_sql":
            return json.loads(item.arguments)

    return {"sql": ""}


def interactive_mode(schema_paths=None):
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
        console.print(result.get("sql", ""))


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", action="append", default=[])
    args = parser.parse_args()

    validate_environment(schema_paths=args.schema, require_api_key=True)
    interactive_mode(schema_paths=args.schema)


if __name__ == "__main__":
    main()


# ---------------------------
# Unit tests for print_usage
# ---------------------------

import unittest
from types import SimpleNamespace
from unittest.mock import patch


class TestPrintUsage(unittest.TestCase):
    def test_print_usage_no_usage_prints_nothing(self):
        response = SimpleNamespace(usage=None)
        with patch.object(console, "print") as mock_print:
            print_usage(response, "gpt-4.1-mini")
        mock_print.assert_not_called()

    def test_print_usage_fallback_total_tokens_when_missing(self):
        usage = SimpleNamespace(input_tokens=100, output_tokens=50)
        response = SimpleNamespace(usage=usage)
        with patch.object(console, "print") as mock_print:
            print_usage(response, "gpt-4.1-mini")
        mock_print.assert_called_once()
        message = mock_print.call_args[0][0]
        self.assertIn("100 in + 50 out = 150 total", message)

    def test_print_usage_uses_provided_total_tokens(self):
        usage = SimpleNamespace(input_tokens=100, output_tokens=50, total_tokens=999)
        response = SimpleNamespace(usage=usage)
        with patch.object(console, "print") as mock_print:
            print_usage(response, "gpt-4.1-mini")
        mock_print.assert_called_once()
        message = mock_print.call_args[0][0]
        self.assertIn("100 in + 50 out = 999 total", message)

    def test_print_usage_contains_expected_counts_and_cost_format(self):
        usage = SimpleNamespace(input_tokens=1000, output_tokens=500, total_tokens=1500)
        response = SimpleNamespace(usage=usage)
        with patch.object(console, "print") as mock_print:
            print_usage(response, "gpt-4.1-mini")
        mock_print.assert_called_once()
        message = mock_print.call_args[0][0]
        self.assertIn("📊 Tokens: 1000 in + 500 out = 1500 total", message)
        self.assertIn("💰 Est. cost: $0.0012", message)


if __name__ == "__main__":  # pragma: no cover
    if "unittest" in sys.modules:
        pass
