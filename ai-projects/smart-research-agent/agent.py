import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import pytest
from openai import APIError, APITimeoutError, RateLimitError
from types import SimpleNamespace
from unittest.mock import Mock, call

import agent


RETRY_EXC = (RateLimitError, APITimeoutError, APIError)
VERBOSE = False


def retry_with_backoff(func, delays=(1, 2, 4), sleeper=time.sleep):
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except RETRY_EXC as exc:
                last_exception = exc
                if attempt == len(delays):
                    break
                sleeper(delays[attempt])
        raise last_exception

    return wrapper


def validate_environment(argv: list[str] | None = None) -> bool:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Error: OPENAI_API_KEY is not set or is empty.")

    args = list(sys.argv[1:] if argv is None else argv)
    verbose = any(arg in ("-v", "--verbose") for arg in args)

    skip_next = False
    for i, arg in enumerate(args):
        if skip_next:
            skip_next = False
            continue
        if arg in ("-v", "--verbose"):
            continue
        if arg in ("-e", "--export"):
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                skip_next = True
            continue
        if arg.startswith("-"):
            continue
        path = Path(arg)
        if verbose:
            print(f"[verbose] Validating path: {arg}")
        if not path.exists():
            raise SystemExit(f"Error: File path does not exist: {arg}")
        if not path.is_file():
            raise SystemExit(f"Error: Path is not a file: {arg}")
        if not os.access(path, os.R_OK):
            raise SystemExit(f"Error: File is not readable: {arg}")

    print("Setup OK ✓")
    return verbose


def main() -> None:
    global VERBOSE
    VERBOSE = validate_environment()


def export_results(results: dict, export_enabled: bool, export_path: str | None = None) -> str | None:
    if not export_enabled:
        return None
    now = datetime.now()
    filename = export_path or f"output_{now:%Y%m%d_%H%M%S}.json"
    payload = dict(results)
    payload["generated_at"] = now.isoformat()
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return filename


def _make_response_with_usage(
    prompt_tokens: int | None = None,
    completion_tokens: int | None = None,
    total_tokens: int | None = None,
) -> SimpleNamespace:
    usage = SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
    return SimpleNamespace(usage=usage)


def test_retry_succeeds_after_failures_and_uses_delay_sequence() -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RateLimitError("temp", response=Mock(), body=None)
        return "ok"

    sleep_mock = Mock()
    wrapped = retry_with_backoff(flaky, sleeper=sleep_mock)

    assert wrapped() == "ok"
    assert calls["n"] == 3
    assert sleep_mock.call_args_list == [call(1), call(2)]


def test_retry_raises_after_max_attempts() -> None:
    def always_fail() -> None:
        raise APITimeoutError(request=Mock())

    sleep_mock = Mock()
    wrapped = retry_with_backoff(always_fail, sleeper=sleep_mock)

    with pytest.raises(APITimeoutError):
        wrapped()

    assert sleep_mock.call_args_list == [call(1), call(2), call(4)]


def test_print_usage_no_usage_does_not_print(capsys: pytest.CaptureFixture[str]) -> None:
    response = SimpleNamespace(usage=None)

    agent.print_usage(response)

    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_usage_with_token_fields_prints_expected_totals(capsys: pytest.CaptureFixture[str]) -> None:
    response = _make_response_with_usage(prompt_tokens=1000, completion_tokens=500, total_tokens=1500)

    agent.print_usage(response)

    captured = capsys.readouterr()
    assert "📊 Tokens: 1000 in + 500 out = 1500 total" in captured.out
    assert "💰 Est. cost: $0.0000" in captured.out


def test_print_usage_missing_fields_defaults_to_zero_without_errors(capsys: pytest.CaptureFixture[str]) -> None:
    usage = SimpleNamespace()
    response = SimpleNamespace(usage=usage)

    agent.print_usage(response)

    captured = capsys.readouterr()
    assert "📊 Tokens: 0 in + 0 out = 0 total" in captured.out


def test_summarize_text_calls_print_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_response = SimpleNamespace(
        usage=SimpleNamespace(prompt_tokens=1, completion_tokens=1, total_tokens=2),
        choices=[SimpleNamespace(message=SimpleNamespace(content="summary"))],
    )

    mock_create = Mock(return_value=mock_response)
    mock_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=mock_create)
        )
    )

    monkeypatch.setattr(agent, "get_client", lambda: mock_client)
    print_usage_mock = Mock()
    monkeypatch.setattr(agent, "print_usage", print_usage_mock)

    result = agent.summarize_text("some text", "focus")

    assert result == "summary"
    print_usage_mock.assert_called_once_with(mock_response)


def test_validate_environment_accepts_long_verbose_flag_and_sets_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    result = agent.validate_environment(["--verbose"])

    assert result is True


def test_export_results_disabled_returns_none_and_writes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    open_mock = Mock()
    monkeypatch.setattr("builtins.open", open_mock)

    result = agent.export_results({"x": 1}, export_enabled=False)

    assert result is None
    open_mock.assert_not_
