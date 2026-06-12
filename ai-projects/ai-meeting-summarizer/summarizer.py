...

def retry_with_backoff(func: Any) -> Any:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        delays = [1, 2, 4]
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception:
                if attempt == len(delays):
                    raise
                time.sleep(delays[attempt])

    return wrapper


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        _client.chat.completions.create = retry_with_backoff(_client.chat.completions.create)
    return _client

...