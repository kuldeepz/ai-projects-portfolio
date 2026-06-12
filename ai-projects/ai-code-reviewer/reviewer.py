import io
import random
import sys
import time
from contextlib import redirect_stdout
from functools import wraps
from typing import Any

CHAT_MODEL = "gpt-4o-mini"
VERBOSE = False

MODEL_PRICING_PER_1K: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"input": 0.000015, "output": 0.000060},
}


def print_usage(response: Any) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", 0) or 0

    pricing = MODEL_PRICING_PER_1K.get(CHAT_MODEL)
    if pricing:
        cost = (prompt_tokens / 1000) * pricing["input"] + (completion_tokens / 1000) * pricing["output"]
        print(
            f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | "
            f"💰 Est. cost (approx): ${cost:.4f}"
        )
    else:
        print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total")


def retry_with_backoff(max_retries: int = 3, base_delay: float = 1.0, retry_exceptions: tuple[type[Exception], ...] = (Exception,)):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except retry_exceptions:
                    if attempt == max_retries:
                        raise
                    delay = base_delay * (2 ** attempt)
                    jitter = random.uniform(0, delay * 0.2)
                    time.sleep(delay + jitter)
        return wrapper
    return deco


# --- minimal CLI and review flow used by tests ---
def _extract_verbose_flag(argv: list[str]) -> tuple[list[str], bool]:
    verbose = False
    cleaned: list[str] = []
    for arg in argv:
        if arg in ("--verbose", "-v"):
            verbose = True
            continue
        cleaned.append(arg)
    return cleaned, verbose


def review_code(api_call, payload: Any) -> Any:
    if VERBOSE:
        print("[verbose] preparing API call")
    response = api_call(payload)
    if VERBOSE:
        print("[verbose] API call completed")
    return response


def main(argv: list[str] | None = None) -> int:
    global VERBOSE
    argv = list(sys.argv[1:] if argv is None else argv)
    argv, verbose = _extract_verbose_flag(argv)
    VERBOSE = verbose
    # Existing behavior would continue using argv
    return 0


# --- tests for verbose branches and CLI arg stripping ---
def test_review_code_verbose_prints_diagnostics():
    global VERBOSE
    VERBOSE = True

    def fake_api(payload):
        return {"ok": True, "payload": payload}

    buf = io.StringIO()
    with redirect_stdout(buf):
        result = review_code(fake_api, {"x": 1})

    out = buf.getvalue()
    assert "[verbose] preparing API call" in out
    assert "[verbose] API call completed" in out
    assert result["ok"] is True


def test_review_code_non_verbose_unchanged_no_diagnostics():
    global VERBOSE
    VERBOSE = False

    def fake_api(payload):
        return {"ok": True, "payload": payload}

    buf = io.StringIO()
    with redirect_stdout(buf):
        result = review_code(fake_api, {"x": 1})

    out = buf.getvalue()
    assert "[verbose]" not in out
    assert result["ok"] is True


def test_cli_verbose_flags_recognized_and_removed():
    args, verbose = _extract_verbose_flag(["--verbose", "file.py", "--flag", "value"])
    assert verbose is True
    assert args == ["file.py", "--flag", "value"]

    args, verbose = _extract_verbose_flag(["-v", "file.py", "positional"])
    assert verbose is True
    assert args == ["file.py", "positional"]

    args, verbose = _extract_verbose_flag(["file.py", "--flag", "value"])
    assert verbose is False
    assert args == ["file.py", "--flag", "value"]
