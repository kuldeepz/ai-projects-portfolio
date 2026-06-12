import argparse
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
            last_exc = None
            for attempt in range(len(delays) + 1):
                try:
                    return target(*args, **kwargs)
                except retry_exceptions as exc:
                    last_exc = exc
                    if attempt == len(delays):
                        raise
                    time.sleep(delays[attempt])
            raise last_exc

        return wrapper

    if func is None:
        return decorator
    return decorator(func)


def _extract_model_name(args, kwargs):
    if "model" in kwargs:
        return kwargs["model"]
    for arg in args:
        if isinstance(arg, str):
            return arg
    return "unknown"


def _extract_input_text(args, kwargs):
    for key in ("input", "prompt", "messages"):
        if key in kwargs:
            return kwargs[key]
    if args:
        return args[0]
    return ""


def _estimate_token_count(value):
    if isinstance(value, str):
        return max(1, len(value) // 4) if value else 0
    return max(1, len(str(value)) // 4) if value else 0


def print_usage(response):
    usage = getattr(response, "usage", None)
    if usage is None and isinstance(response, dict):
        usage = response.get("usage")
    if not usage:
        return

    if isinstance(usage, dict):
        prompt_tokens = usage.get("prompt_tokens")
        completion_tokens = usage.get("completion_tokens")
        total_tokens = usage.get("total_tokens")
    else:
        prompt_tokens = getattr(usage, "prompt_tokens", None)
        completion_tokens = getattr(usage, "completion_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)

    if prompt_tokens is None or completion_tokens is None:
        return
    if total_tokens is None:
        total_tokens = prompt_tokens + completion_tokens

    cost = (prompt_tokens / 1000.0) * 0.000015 + (completion_tokens / 1000.0) * 0.00006
    print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")


def parse_args(argv=None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--debug-sensitive", action="store_true")
    return parser.parse_known_args(argv)


def configure_verbose(argv=None):
    global VERBOSE, DEBUG_SENSITIVE
    args, _ = parse_args(argv)
    VERBOSE = args.verbose
    DEBUG_SENSITIVE = args.verbose and args.debug_sensitive


@retry_with_backoff
def call_openai(*args, **kwargs):
    """Production OpenAI call path wrapped with retry/backoff.

    Replace the body with the real OpenAI invocation in this project.
    """
    if VERBOSE:
        model = _extract_model_name(args, kwargs)
        print("⏳ Calling OpenAI API...")
        print(f"Request model: {model}")
        if DEBUG_SENSITIVE:
            input_value = _extract_input_text(args, kwargs)
            char_count = len(input_value) if isinstance(input_value, str) else len(str(input_value))
            token_count = _estimate_token_count(input_value)
            print(f"Input chars: {char_count}, tokens: {token_count}")
        started = time.time()
    try:
        raise NotImplementedError("Implement OpenAI API invocation here")
    finally:
        if VERBOSE:
            elapsed = time.time() - started
            print(f"✅ Done in {elapsed:.1f}s")


def _reset_verbose_for_tests(value=False, debug_sensitive=False):
    """Test helper: reset global verbose flags deterministically."""
    global VERBOSE, DEBUG_SENSITIVE
    VERBOSE = value
    DEBUG_SENSITIVE = debug_sensitive


if __name__ == "__main__":
    import io
    import contextlib
    import unittest

    class _UsageObj:
        def __init__(self, prompt_tokens=None, completion_tokens=None, total_tokens=None):
            self.prompt_tokens = prompt_tokens
            self.completion_tokens = completion_tokens
            self.total_tokens = total_tokens

    class _ResponseObj:
        def __init__(self, usage=None):
            self.usage = usage

    class TestEvaluatorCLIAndVerbose(unittest.TestCase):
        def setUp(self):
            _reset_verbose_for_tests(False)

        def tearDown(self):
            _reset_verbose_for_tests(False)

        def test_parse_args_verbose_flag(self):
            args, unknown = parse_args(["--verbose"])
            self.assertTrue(args.verbose)
            self.assertFalse(args.debug_sensitive)
            self.assertEqual(unknown, [])

        def test_parse_args_debug_sensitive_flag(self):
            args, unknown = parse_args(["--verbose", "--debug-sensitive"])
            self.assertTrue(args.verbose)
            self.assertTrue(args.debug_sensitive)
            self.assertEqual(unknown, [])

        def test_configure_verbose_mutates_global_state(self):
            self.assertFalse(VERBOSE)
            self.assertFalse(DEBUG_SENSITIVE)
            configure_verbose(["--verbose"])
            self.assertTrue(VERBOSE)
            self.assertFalse(DEBUG_SENSITIVE)
            configure_verbose(["--verbose", "--debug-sensitive"])
            self.assertTrue(VERBOSE)
            self.assertTrue(DEBUG_SENSITIVE)
            configure_verbose([])
            self.assertFalse(VERBOSE)
            self.assertFalse(DEBUG_SENSITIVE)

        def test_print_usage_with_object_usage(self):
            response = _ResponseObj(_UsageObj(prompt_tokens=100, completion_tokens=50, total_tokens=150))
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                print_usage(response)
                out = buf.getvalue().strip()
            self.assertIn("100 in + 50 out = 150 total", out)

        def test_print_usage_with_dict_response(self):
            response = {
                "usage": {
                    "prompt_tokens": 40,
                    "completion_tokens": 10,
                    "total_tokens": 50,
                }
            }
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                print_usage(response)
                out = buf.getvalue().strip()
            self.assertIn("40 in + 10 out = 50 total", out)

        def test_print_usage_missing_usage_no_output(self):
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                print_usage({})
                out = buf.getvalue()
            self.assertEqual(out, "")

        def test_print_usage_missing_total_tokens_computed(self):
            response = _ResponseObj(_UsageObj(prompt_tokens=30, completion_tokens=20, total_tokens=None))
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                print_usage(response)
                out = buf.getvalue().strip()
            self.assertIn("30 in + 20 out = 50 total", out)

        def test_print_usage_missing_prompt_or_completion_early_return(self):
            response_missing_prompt = {"usage": {"completion_tokens": 10, "total_tokens": 10}}
            response_missing_completion = {"usage": {"prompt_tokens": 10, "total_tokens": 10}}

            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                print_usage(response_missing_prompt)
                print_usage(response_missing_completion)
                out = buf.getvalue()
            self.assertEqual(out, "")

        def test_print_usage_expected_cost_formatting(self):
            response = _ResponseObj(_UsageObj(prompt_tokens=1000, completion_tokens=1000, total_tokens=2000))
            with io.StringIO() as buf, contextlib.redirect_stdout(buf):
                print_usage(response)
                out = buf.getvalue().strip()
            self.assertTrue(out.endswith("Est. cost: $0.0001"))

    unittest.main()
