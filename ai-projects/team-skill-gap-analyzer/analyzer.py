import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional


# Approx pricing defaults (USD per 1K tokens)
PROMPT_COST_PER_1K = 0.005
COMPLETION_COST_PER_1K = 0.015


def validate_environment(input_file: Optional[str]) -> None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or not api_key.strip():
        print("OPENAI_API_KEY is not set or is empty")
        raise SystemExit(1)

    if input_file is not None:
        p = Path(input_file)
        if not p.exists():
            print(f"File not found: {p}")
            raise SystemExit(1)
        if not p.is_file():
            print(f"Not a file: {p}")
            raise SystemExit(1)
        if not os.access(str(p), os.R_OK):
            print(f"File is not readable: {p}")
            raise SystemExit(1)

    print("Setup OK")


def calculate_estimated_cost(prompt_tokens: int, completion_tokens: int) -> float:
    prompt_cost = (prompt_tokens / 1000.0) * PROMPT_COST_PER_1K
    completion_cost = (completion_tokens / 1000.0) * COMPLETION_COST_PER_1K
    return float(prompt_cost + completion_cost)


def print_token_usage(
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
) -> None:
    print(
        "Token usage -> "
        f"prompt: {prompt_tokens}, "
        f"completion: {completion_tokens}, "
        f"total: {total_tokens}, "
        f"estimated_cost_usd: {estimated_cost:.4f}"
    )


def extract_token_usage(response: Any) -> Dict[str, int]:
    usage = None

    if isinstance(response, dict):
        usage = response.get("usage")
    else:
        usage = getattr(response, "usage", None)

    if usage is None:
        return {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    if isinstance(usage, dict):
        prompt = int(usage.get("prompt_tokens", 0) or 0)
        completion = int(usage.get("completion_tokens", 0) or 0)
        total = int(usage.get("total_tokens", prompt + completion) or 0)
    else:
        prompt = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion = int(getattr(usage, "completion_tokens", 0) or 0)
        total = int(getattr(usage, "total_tokens", prompt + completion) or 0)

    return {
        "prompt_tokens": prompt,
        "completion_tokens": completion,
        "total_tokens": total,
    }


def track_and_print_usage(response: Any, model_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    usage = None
    if isinstance(response, dict):
        usage = response.get("usage")
    else:
        usage = getattr(response, "usage", None)

    if not usage:
        return None

    token_usage = extract_token_usage(response)
    estimated_cost = calculate_estimated_cost(
        prompt_tokens=token_usage["prompt_tokens"],
        completion_tokens=token_usage["completion_tokens"],
    )

    if model_name:
        print(f"Model: {model_name}")

    print_token_usage(
        prompt_tokens=token_usage["prompt_tokens"],
        completion_tokens=token_usage["completion_tokens"],
        total_tokens=token_usage["total_tokens"],
        estimated_cost=estimated_cost,
    )

    return {
        "model": model_name,
        "prompt_tokens": token_usage["prompt_tokens"],
        "completion_tokens": token_usage["completion_tokens"],
        "total_tokens": token_usage["total_tokens"],
        "estimated_cost": estimated_cost,
    }


def create_response_with_usage_tracking(client: Any, model_name: str, **kwargs: Any) -> Any:
    response = client.responses.create(model=model_name, **kwargs)
    track_and_print_usage(response, model_name=model_name)
    return response


if __name__ == "__main__":
    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    validate_environment(file_arg)
