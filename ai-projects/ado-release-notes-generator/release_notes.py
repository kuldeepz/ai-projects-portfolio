import argparse
import json
import unittest
from collections.abc import Callable
from datetime import datetime
from functools import wraps
from typing import Any
from unittest.mock import call, patch

import release_notes


class NonRetriableError(Exception):
    pass


class RetryWithBackoffTests(unittest.TestCase):
    def test_retry_immediate_success_no_sleep(self) -> None:
        mock_func = unittest.mock.Mock(return_value="ok")
        wrapped = release_notes.retry_with_backoff(mock_func)

        with patch("release_notes.time.sleep") as mock_sleep:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()

    def test_retry_succeeds_after_retries_expected_sleeps(self) -> None:
        transient_error = release_notes.APIConnectionError("e1", request=None)
        timeout_error = release_notes.APITimeoutError(request=None)
        mock_func = unittest.mock.Mock(side_effect=[transient_error, timeout_error, "ok"])
        wrapped = release_notes.retry_with_backoff(mock_func)

        with patch("release_notes.time.sleep") as mock_sleep:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(mock_func.call_count, 3)
        mock_sleep.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock_sleep.call_count, 2)

    def test_retry_raises_last_exception_after_max_attempts(self) -> None:
        e1 = release_notes.APIConnectionError("e1", request=None)
        e2 = release_notes.APITimeoutError(request=None)
        final_exc = release_notes.RateLimitError("final", response=None, body=None)
        mock_func = unittest.mock.Mock(side_effect=[e1, e2, final_exc])
        wrapped = release_notes.retry_with_backoff(mock_func)

        with patch("release_notes.time.sleep") as mock_sleep:
            with self.assertRaises(release_notes.RateLimitError) as ctx:
                wrapped()

        self.assertIs(ctx.exception, final_exc)
        self.assertEqual(mock_func.call_count, 3)
        mock_sleep.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock_sleep.call_count, 2)

    def test_non_retriable_exception_not_retried_when_filtered(self) -> None:
        def retry_with_filter(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                delays = [1, 2, 4]
                last_exception: Exception | None = None
                for i, delay in enumerate(delays):
                    try:
                        return func(*args, **kwargs)
                    except NonRetriableError:
                        raise
                    except Exception as e:
                        last_exception = e
                        if i < len(delays) - 1:
                            release_notes.time.sleep(delay)
                raise last_exception

            return wrapped

        mock_func = unittest.mock.Mock(side_effect=NonRetriableError("stop"))
        wrapped = retry_with_filter(mock_func)

        with patch("release_notes.time.sleep") as mock_sleep:
            with self.assertRaises(NonRetriableError):
                wrapped()

        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()


class CreateChatCompletionTests(unittest.TestCase):
    def test_create_chat_completion_uses_retry_wrapper(self) -> None:
        with patch("release_notes.get_client") as mock_get_client, patch("release_notes.time.sleep") as mock_sleep:
            create = mock_get_client.return_value.chat.completions.create
            create.side_effect = [
                release_notes.APIConnectionError("e1", request=None),
                "response",
            ]

            result = release_notes.create_chat_completion(model="m", messages=[])

        self.assertEqual(result, "response")
        self.assertEqual(create.call_count, 2)
        mock_sleep.assert_called_once_with(1)


def _export_results_if_requested(results: dict[str, Any]) -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-e", "--export", action="store_true")
    args, _ = parser.parse_known_args()

    if not args.export:
        return

    generated_at = datetime.now().isoformat()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = dict(results)
    output["generated_at"] = generated_at
    filename = f"output_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    test_program = unittest.main(exit=False)
    test_results = {
        "tests_run": test_program.result.testsRun,
        "failures": len(test_program.result.failures),
        "errors": len(test_program.result.errors),
        "skipped": len(test_program.result.skipped),
        "successful": test_program.result.wasSuccessful(),
    }
    _export_results_if_requested(test_results)
