import json
import os
import sys
import time
import unittest
from datetime import datetime
from io import StringIO
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

from rich.console import Console


VERBOSE = False
console = Console()


def validate_environment(input_path: Optional[str]) -> None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or not api_key.strip():
        print("OPENAI_API_KEY is not set or is empty")
        raise SystemExit(1)

    if input_path is None:
        print("Setup OK")
        return

    p = Path(input_path)
    if not p.exists():
        print(f"File not found: {p}")
        raise SystemExit(1)
    if not p.is_file():
        print(f"Not a file: {p}")
        raise SystemExit(1)
    if not os.access(p, os.R_OK):
        print(f"File is not readable: {p}")
        raise SystemExit(1)

    print("Setup OK")


def extract_token_usage(response: Any) -> Dict[str, int]:
    usage_obj: Any = None

    if isinstance(response, dict):
        usage_obj = response.get("usage")
    else:
        usage_obj = getattr(response, "usage", None)

    if usage_obj is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if isinstance(usage_obj, dict):
        prompt_tokens = int(usage_obj.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage_obj.get("completion_tokens", 0) or 0)
        total_tokens = int(usage_obj.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    else:
        prompt_tokens = int(getattr(usage_obj, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage_obj, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage_obj, "total_tokens", prompt_tokens + completion_tokens) or 0)

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def calculate_estimated_cost(prompt_tokens: int, completion_tokens: int) -> float:
    # Simple default estimate (USD per 1K tokens)
    prompt_rate_per_1k = 0.01
    completion_rate_per_1k = 0.03
    return (prompt_tokens / 1000.0) * prompt_rate_per_1k + (
        completion_tokens / 1000.0
    ) * completion_rate_per_1k


def print_token_usage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
) -> None:
    print(
        "Token usage - "
        f"prompt: {prompt_tokens}, "
        f"completion: {completion_tokens}, "
        f"total: {total_tokens}, "
        f"estimated_cost_usd: {estimated_cost:.4f}"
    )


def print_usage(usage: Any, model_name: Optional[str] = None) -> None:
    if usage is None:
        return

    if isinstance(usage, dict):
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)
    else:
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)
        total_tokens = int(getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0)

    estimated_cost = calculate_estimated_cost(prompt_tokens, completion_tokens)
    if model_name:
        print(f"Model: {model_name}")
    print_token_usage(prompt_tokens, completion_tokens, total_tokens, estimated_cost)


def create_response_with_usage(client: Any, model_name: str, **kwargs: Any) -> Any:
    if VERBOSE:
        input_value = kwargs.get("input", "")
        input_text = str(input_value)
        print(f"Input size - chars: {len(input_text)}, tokens(approx): {len(input_text) // 4}")
        print("⏳ Calling OpenAI API...")
        start = time.time()
    with console.status("[bold green]Processing..."):
        resp = client.responses.create(model=model_name, **kwargs)
    if VERBOSE:
        elapsed = time.time() - start
        print(f"✅ Done in {elapsed:.1f}s")
    usage = getattr(resp, "usage", None)
    if usage:
        print_usage(usage, model_name)
    return resp


def _parse_cli_args(args: list[str]) -> tuple[bool, Optional[str], Optional[str]]:
    verbose = False
    input_path: Optional[str] = None
    export_path: Optional[str] = None

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--verbose", "-v"):
            verbose = True
        elif arg in ("--export", "-e"):
            if i + 1 >= len(args) or args[i + 1].startswith("-"):
                raise SystemExit("Missing value for --export")
            export_path = args[i + 1]
            i += 1
        elif input_path is None:
            input_path = arg
        i += 1

    return verbose, input_path, export_path


def export_results(results: Dict[str, Any], export_path: Optional[str] = None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = export_path or f"output_{timestamp}.json"
    payload = dict(results)
    payload["generated_at"] = datetime.now().isoformat()
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return file_name


def run_cli(results: Dict[str, Any], argv: Optional[list[str]] = None) -> Dict[str, Any]:
    args = sys.argv[1:] if argv is None else argv
    _, _, export_path = _parse_cli_args(args)
    if export_path is not None:
        out = export_results(results, export_path)
        print(f"Exported JSON: {out}")
    return results


class TestCliParsing(unittest.TestCase):
    def test_verbose_long_flag_and_input_path(self) -> None:
        verbose, input_path, export_path = _parse_cli_args(["--verbose", "file.txt"])
        self.assertTrue(verbose)
        self.assertEqual(input_path, "file.txt")
        self.assertIsNone(export_path)

    def test_short_verbose_flag_without_input_path(self) -> None:
        verbose, input_path, export_path = _parse_cli_args(["-v"])
        self.assertTrue(verbose)
        self.assertIsNone(input_path)
        self.assertIsNone(export_path)

    def test_export_long_flag_with_value_and_input(self) -> None:
        verbose, input_path, export_path = _parse_cli_args(["--export", "out.json", "file.txt"])
        self.assertFalse(verbose)
        self.assertEqual(input_path, "file.txt")
        self.assertEqual(export_path, "out.json")

    def test_export_short_flag_with_value(self) -> None:
        verbose, input_path, export_path = _parse_cli_args(["-e", "out.json"])
        self.assertFalse(verbose)
        self.assertIsNone(input_path)
        self.assertEqual(export_path, "out.json")

    def test_export_missing_value_raises(self) -> None:
        with self.assertRaises(SystemExit):
            _parse_cli_args(["--export"])

    def test_run_cli_exports_when_export_flag_is_provided(self) -> None:
        sample_results = {"score": 42}
        with patch(__name__ + ".export_results", return_value="out.json") as mock_export:
            with patch("builtins.print") as mock_print:
                returned = run_cli(sample_results, ["--export", "out.json"])
        self.assertEqual(returned, sample_results)
        mock_export.assert_called_once_with(sample_results, "out.json")
        mock_print.assert_any_call("Exported JSON: out.json")
