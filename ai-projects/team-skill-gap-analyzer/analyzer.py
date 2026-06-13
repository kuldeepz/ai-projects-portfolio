import os
import sys
import time
import unittest
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Optional
from unittest.mock import patch


VERBOSE = False


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
    resp = client.responses.create(model=model_name, **kwargs)
    if VERBOSE:
        elapsed = time.time() - start
        print(f"✅ Done in {elapsed:.1f}s")
    usage = getattr(resp, "usage", None)
    if usage:
        print_usage(usage, model_name)
    return resp


def _parse_cli_args(args: list[str]) -> tuple[bool, Optional[str]]:
    verbose = False
    input_path: Optional[str] = None

    for arg in args:
        if arg in ("--verbose", "-v"):
            verbose = True
        elif input_path is None:
            input_path = arg

    return verbose, input_path


class TestCliParsing(unittest.TestCase):
    def test_verbose_long_flag_and_input_path(self) -> None:
        verbose, input_path = _parse_cli_args(["--verbose", "file.txt"])
        self.assertTrue(verbose)
        self.assertEqual(input_path, "file.txt")

    def test_short_verbose_flag_without_input_path(self) -> None:
        verbose, input_path = _parse_cli_args(["-v"])
        self.assertTrue(verbose)
        self.assertIsNone(input_path)

    def test_unknown_extra_args_first_non_flag_is_input(self) -> None:
        verbose, input_path = _parse_cli_args(["--verbose", "file.txt", "--unknown", "extra"])
        self.assertTrue(verbose)
        self.assertEqual(input_path, "file.txt")

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_short_verbose_runs_setup_check_without_input(self) -> None:
        validate_environment(None)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True)
    def test_verbose_with_input_validates_existing_file(self) -> None:
        with NamedTemporaryFile() as tmp:
            validate_environment(tmp.name)


if __name__ == "__main__":
    args = sys.argv[1:]

    if args and args[0] == "--run-tests":
        unittest.main(argv=[sys.argv[0]])
    else:
        VERBOSE, input_path = _parse_cli_args(args)
        validate_environment(input_path)
