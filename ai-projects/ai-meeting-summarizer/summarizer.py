from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Callable, ParamSpec, Protocol, TypeVar

from openai import OpenAI
from rich.console import Console

console = Console()
_client: OpenAI | None = None

P = ParamSpec("P")
R = TypeVar("R")


class PathConfigLike(Protocol):
    input_path: str | Path | None
    output_path: str | Path | None
    template_path: str | Path | None


def retry_with_backoff(func: Callable[P, R]) -> Callable[P, R]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
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


def validate_paths(config: PathConfigLike) -> list[Path]:
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


# ----------------------
# Unit tests for retries
# ----------------------


def test_retry_with_backoff_immediate_success(monkeypatch: Any) -> None:
    sleep_calls: list[int] = []

    def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    calls = {"count": 0}

    def fn() -> str:
        calls["count"] += 1
        return "ok"

    wrapped = retry_with_backoff(fn)
    assert wrapped() == "ok"
    assert calls["count"] == 1
    assert sleep_calls == []


def test_retry_with_backoff_fails_then_succeeds(monkeypatch: Any) -> None:
    sleep_calls: list[int] = []

    def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    calls = {"count": 0}

    def fn() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("transient")
        return "ok"

    wrapped = retry_with_backoff(fn)
    assert wrapped() == "ok"
    assert calls["count"] == 3
    assert sleep_calls == [1, 2]


def test_retry_with_backoff_raises_after_all_attempts(monkeypatch: Any) -> None:
    sleep_calls: list[int] = []

    def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    def fn() -> str:
        raise ValueError("always fails")

    wrapped = retry_with_backoff(fn)

    import pytest

    with pytest.raises(ValueError, match="always fails"):
        wrapped()

    assert sleep_calls == [1, 2, 4]


def test_get_client_wraps_chat_completions_create(monkeypatch: Any) -> None:
    global _client
    _client = None

    sleep_calls: list[int] = []

    def fake_sleep(seconds: int) -> None:
        sleep_calls.append(seconds)

    monkeypatch.setattr(time, "sleep", fake_sleep)

    class FakeCompletions:
        def __init__(self) -> None:
            self.calls = 0

        def create(self, *_args: Any, **_kwargs: Any) -> dict[str, bool]:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("temporary")
            return {"ok": True}

    class FakeChat:
        def __init__(self) -> None:
            self.completions = FakeCompletions()

    class FakeClient:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.chat = FakeChat()

    monkeypatch.setattr("summarizer.OpenAI", FakeClient)

    client = get_client()
    result = client.chat.completions.create()

    assert result == {"ok": True}
    assert client.chat.completions.calls == 2
    assert sleep_calls == [1]
