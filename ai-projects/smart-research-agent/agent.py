import argparse
import json
import os
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from openai import APIError, APITimeoutError, RateLimitError
from rich.console import Console


RETRY_EXC = (RateLimitError, APITimeoutError, APIError)
VERBOSE = False
console = Console()


def retry_with_backoff(func, delays=(1, 2, 4), sleeper=time.sleep):
    def wrapper(*args, **kwargs):
        last_exception = None
        with console.status("[bold green]Processing..."):
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
    with console.status("[bold green]Processing..."):
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
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-e", "--export", nargs="?", const="auto", metavar="FILE")
    args, _ = parser.parse_known_args(sys.argv[1:])

    VERBOSE = validate_environment()

    if args.export is not None:
        export_path = None if args.export == "auto" else args.export
        export_results({}, export_enabled=True, export_path=export_path)


def export_results(results: dict, export_enabled: bool, export_path: str | None = None) -> str | None:
    if not export_enabled:
        return None
    now = datetime.now()
    filename = export_path or f"output_{now:%Y%m%d_%H%M%S}.json"
    payload = dict(results)
    payload["generated_at"] = now.isoformat()
    with console.status("[bold green]Processing..."):
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    return filename


class _NoopStatus:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class AgentSpinnerBehaviorTests(unittest.TestCase):
    def _patched_status(self):
        return patch.object(console, "status", return_value=_NoopStatus())

    def test_retry_with_backoff_retries_sleeps_and_reraises(self):
        calls = {"count": 0}

        def flaky():
            calls["count"] += 1
            raise RuntimeError("boom")

        wrapped = retry_with_backoff(flaky, delays=(1, 2))

        with self._patched_status(), patch.object(sys.modules[__name__], "RETRY_EXC", (RuntimeError,)):
            sleep_calls: list[int] = []
            with self.assertRaises(RuntimeError) as ctx:
                wrapped(sleeper := sleep_calls.append)

        # wrapped takes arbitrary args; pass sleeper via closure instead
        # above line passed arg to flaky; run correctly below

    def test_retry_with_backoff_retries_sleeps_and_reraises(self):
        calls = {"count": 0}
        sleep_calls: list[int] = []

        def flaky():
            calls["count"] += 1
            raise RuntimeError("boom")

        wrapped = retry_with_backoff(flaky, delays=(1, 2), sleeper=sleep_calls.append)

        with self._patched_status(), patch.object(sys.modules[__name__], "RETRY_EXC", (RuntimeError,)):
            with self.assertRaises(RuntimeError) as ctx:
                wrapped()

        self.assertEqual(str(ctx.exception), "boom")
        self.assertEqual(calls["count"], 3)
        self.assertEqual(sleep_calls, [1, 2])

    def test_validate_environment_systemexit_message_with_status(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=False), self._patched_status():
            with self.assertRaises(SystemExit) as ctx:
                validate_environment(["missing-file.txt"])
        self.assertEqual(str(ctx.exception), "Error: File path does not exist: missing-file.txt")

    def test_export_results_writes_and_returns_filename_with_status(self):
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir, self._patched_status():
            out = os.path.join(tmpdir, "result.json")
            returned = export_results({"a": 1}, export_enabled=True, export_path=out)
            self.assertEqual(returned, out)
            with open(out, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.assertEqual(data["a"], 1)
            self.assertIn("generated_at", data)

    def test_export_results_write_error_propagates_with_status(self):
        with self._patched_status(), patch("builtins.open", side_effect=OSError("no write")):
            with self.assertRaises(OSError) as ctx:
                export_results({"a": 1}, export_enabled=True, export_path="x.json")
        self.assertEqual(str(ctx.exception), "no write")


if __name__ == "__main__":
    unittest.main()
