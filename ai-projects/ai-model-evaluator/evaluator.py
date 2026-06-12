import argparse
import sys
import time
from functools import wraps


VERBOSE = False
DEBUG_SENSITIVE = False


def retry_with_backoff(func=None, *, delays=(1, 2, 4), retry_exceptions=(TimeoutError, ConnectionError)):
    """Retry wrapper for transient OpenAI/runtime call failures.

    Can be used as:
      @retry_with_backoff
      def fn(...): ...

    or:
      @retry_with_backoff(delays=(1, 2), retry_exceptions=(TimeoutError,))
      def fn(...): ...
    """

    def decorator(target):
        @wraps(target)
        def wrapper(*args, **kwargs):
            started = time.time() if VERBOSE else None
            if VERBOSE:
                model = _extract_model_name(args, kwargs)
                print(f"Model: {model}")
                if DEBUG_SENSITIVE:
                    input_value = _extract_input_text(args, kwargs)
                    char_count = len(input_value) if isinstance(input_value, str) else len(str(input_value))
                    token_count = _estimate_token_count(input_value)
                    print(f"Input chars: {char_count}, tokens: {token_count}")
                print("⏳ Calling OpenAI API...")

            last_exc = None
            attempt_count = 0
            try:
                for attempt in range(len(delays) + 1):
                    attempt_count = attempt + 1
                    try:
                        return target(*args, **kwargs)
                    except retry_exceptions as exc:
                        last_exc = exc
                        if attempt == len(delays):
                            raise
                        time.sleep(delays[attempt])
                raise last_exc
            finally:
                if VERBOSE:
                    elapsed = time.time() - started
                    print(f"✅ Done in {elapsed:.1f}s (attempts: {attempt_count})")

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def _extract_model_name(args, kwargs):
    if "model" in kwargs:
        return kwargs["model"]
    if args and isinstance(args[0], str):
        return args[0]
    return "unknown"


def _extract_input_text(args, kwargs):
    for key in ("input", "prompt", "messages"):
        if key in kwargs:
            return kwargs[key]
    if len(args) > 1:
        return args[1]
    return ""


def _estimate_token_count(value):
    if isinstance(value, str):
        return max(1, len(value) // 4) if value else 0
    return max(1, len(str(value)) // 4) if value else 0


def parse_args(argv=None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--debug-sensitive", action="store_true")
    return parser.parse_known_args(argv)


def configure_verbose(argv=None):
    global VERBOSE, DEBUG_SENSITIVE
    args, _ = parse_args(argv)
    VERBOSE = args.verbose
    DEBUG_SENSITIVE = args.debug_sensitive


def main(argv=None):
    configure_verbose(argv)


@retry_with_backoff
def call_openai(*args, **kwargs):
    """Production OpenAI call path wrapped with retry/backoff.

    Replace the body with the real OpenAI invocation in this project.
    """
    raise NotImplementedError("Implement OpenAI API invocation here")


# ----------------------
# Unit tests (pytest)
# ----------------------

def test_parse_args_verbose_true():
    args, unknown = parse_args(["--verbose"])
    assert args.verbose is True
    assert args.debug_sensitive is False
    assert unknown == []


def test_configure_verbose_mutates_global_state():
    global VERBOSE, DEBUG_SENSITIVE
    VERBOSE = False
    DEBUG_SENSITIVE = False
    configure_verbose(["--verbose", "--debug-sensitive"])
    assert VERBOSE is True
    assert DEBUG_SENSITIVE is True
    configure_verbose([])
    assert VERBOSE is False
    assert DEBUG_SENSITIVE is False


def test_helper_extraction_behavior():
    assert _extract_model_name(("gpt-4o-mini",), {}) == "gpt-4o-mini"
    assert _extract_model_name((), {"model": "gpt-4.1"}) == "gpt-4.1"
    assert _extract_model_name((1, 2), {}) == "unknown"

    assert _extract_input_text((), {"input": "hello"}) == "hello"
    assert _extract_input_text((), {"prompt": "hi"}) == "hi"
    assert _extract_input_text((), {"messages": [{"role": "user", "content": "x"}]}) == [{"role": "user", "content": "x"}]
    assert _extract_input_text(("model", "fallback"), {}) == "fallback"
    assert _extract_input_text(("fallback",), {}) == ""
    assert _extract_input_text((), {}) == ""

    assert _estimate_token_count("") == 0
    assert _estimate_token_count("abcd") == 1
    assert _estimate_token_count("abcdefgh") == 2
    assert _estimate_token_count([1, 2, 3]) >= 1


def test_call_openai_verbose_logging_emitted(capsys):
    global VERBOSE, DEBUG_SENSITIVE
    VERBOSE = True
    DEBUG_SENSITIVE = False
    try:
        call_openai("gpt-4o-mini", input="hello world")
    except NotImplementedError:
        pass
    out = capsys.readouterr().out
    assert "Model:" in out
    assert "Input chars:" not in out
    assert "Calling OpenAI API" in out
    assert "Done in" in out


def test_call_openai_verbose_sensitive_logging_emitted(capsys):
    global VERBOSE, DEBUG_SENSITIVE
    VERBOSE = True
    DEBUG_SENSITIVE = True
    try:
        call_openai("gpt-4o-mini", input="hello world")
    except NotImplementedError:
        pass
    out = capsys.readouterr().out
    assert "Model:" in out
    assert "Input chars:" in out
    assert "Calling OpenAI API" in out
    assert "Done in" in out


def test_call_openai_verbose_logging_suppressed(capsys):
    global VERBOSE, DEBUG_SENSITIVE
    VERBOSE = False
    DEBUG_SENSITIVE = False
    try:
        call_openai("gpt-4o-mini", input="hello world")
    except NotImplementedError:
        pass
    out = capsys.readouterr().out
    assert out == ""


if __name__ == "__main__":
    main(sys.argv[1:])
