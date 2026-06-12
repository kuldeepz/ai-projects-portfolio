import json
import os
import sys
import time
from pathlib import Path
from contextlib import nullcontext

from rich.console import Console

console = Console()


def get_client():
    from openai import OpenAI

    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


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


def generate_sql(prompt, schema_paths=None):
    client = get_client()
    with console.status("Generating SQL...") if hasattr(console, "status") else nullcontext():
        response = _create_response(
            client,
            model="gpt-4.1-mini",
            input=prompt,
            tools=[
                {
                    "type": "function",
                    "name": "emit_sql",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "sql": {"type": "string"},
                        },
                        "required": ["sql"],
                        "additionalProperties": False,
                    },
                }
            ],
        )

    for item in getattr(response, "output", []):
        if getattr(item, "type", None) == "function_call" and getattr(item, "name", None) == "emit_sql":
            return json.loads(item.arguments)
    return {"sql": ""}


def load_schema(schema_paths):
    for p in schema_paths or []:
        if not Path(p).exists():
            raise SystemExit(1)
    return "\n".join(Path(p).read_text() for p in (schema_paths or []))


def validate_environment(schema_paths=None, require_api_key=True):
    if require_api_key and not os.getenv("OPENAI_API_KEY"):
        raise SystemExit(1)
    load_schema(schema_paths or [])


def interactive_mode(schema_paths=None):
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--schema", action="append", default=[])
    args = parser.parse_args()

    validate_environment(schema_paths=args.schema, require_api_key=True)
    interactive_mode(schema_paths=args.schema)


if __name__ == "__main__":
    main()
