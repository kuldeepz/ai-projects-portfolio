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
