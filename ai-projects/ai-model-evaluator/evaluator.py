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

        def test_helper_extractors_and_token_estimator(self):
            self.assertEqual(_extract_model_name(("gpt-4",), {}), "gpt-4")
            self.assertEqual(_extract_model_name((), {"model": "gpt-4o"}), "gpt-4o")
            self.assertEqual(_extract_model_name((123, object()), {}), "unknown")

            self.assertEqual(_extract_input_text((), {"input": "abc"}), "abc")
            self.assertEqual(_extract_input_text((), {"prompt": "p"}), "p")
            self.assertEqual(_extract_input_text((), {"messages": [{"role": "user", "content": "x"}]}), [{"role": "user", "content": "x"}])
            self.assertEqual(_extract_input_text(("fallback",), {}), "fallback")
            self.assertEqual(_extract_input_text((), {}), "")

            self.assertEqual(_estimate_token_count(""), 0)
            self.assertEqual(_estimate_token_count("abcd"), 1)
            self.assertEqual(_estimate_token_count("abcdefgh"), 2)
            self.assertEqual(_estimate_token_count(None), 0)
            self.assertGreaterEqual(_estimate_token_count({"k": "v"}), 1)

        def test_verbose_logging_emitted_without_sensitive_metrics(self):
            configure_verbose(["--verbose"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(NotImplementedError):
                    call_openai(model="gpt-4o", input="hello world")
            output = buf.getvalue()
            self.assertIn("Request model: gpt-4o", output)
            self.assertNotIn("Input chars:", output)
            self.assertIn("⏳ Calling OpenAI API...", output)
            self.assertIn("✅ Done in", output)

        def test_verbose_logging_emitted_with_sensitive_metrics_when_enabled(self):
            configure_verbose(["--verbose", "--debug-sensitive"])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(NotImplementedError):
                    call_openai(model="gpt-4o", input="hello world")
            output = buf.getvalue()
            self.assertIn("Request model: gpt-4o", output)
            self.assertIn("Input chars:", output)
            self.assertIn("⏳ Calling OpenAI API...", output)
            self.assertIn("✅ Done in", output)

        def test_verbose_logging_suppressed(self):
            configure_verbose([])
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                with self.assertRaises(NotImplementedError):
                    call_openai(model="gpt-4o", input="hello world")
            self.assertEqual(buf.getvalue(), "")

    unittest.main()
