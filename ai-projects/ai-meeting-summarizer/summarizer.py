from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from openai import OpenAI
from rich.console import Console

console = Console()
_client: OpenAI | None = None


def retry_with_backoff(func: Any) -> Any:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        delays = [1, 2, 4]
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception:
                if attempt == len(delays):
                    raise
                time.sleep(delays[attempt])

    return wrapper


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        _client.chat.completions.create = retry_with_backoff(_client.chat.completions.create)
    return _client


def validate_paths(config: Any) -> list[Path]:
    paths_to_check: list[str | Path] = []

    for attr in ("input_path", "output_path", "template_path"):
        if hasattr(config, attr):
            value = getattr(config, attr)
            if value is None:
                continue
            if isinstance(value, (str, Path)):
                paths_to_check.append(value)
            else:
                console.print(f"❌ Invalid path type for {attr}: {type(value).__name__}")
                raise SystemExit(1)

    return [Path(raw_path) for raw_path in paths_to_check]
