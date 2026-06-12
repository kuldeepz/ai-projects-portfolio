...

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

...