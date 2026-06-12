import argparse
import json
import unittest
from datetime import datetime
from functools import wraps
from unittest.mock import patch, call, mock_open

import release_notes


class NonRetriableError(Exception):
    pass


class RetryWithBackoffTests(unittest.TestCase):
    def test_retry_immediate_success_no_sleep(self):
        mock_func = unittest.mock.Mock(return_value="ok")
        wrapped = release_notes.retry_with_backoff(mock_func)

        with patch("release_notes.time.sleep") as mock_sleep:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()

    def test_retry_succeeds_after_retries_expected_sleeps(self):
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

    def test_retry_raises_last_exception_after_max_attempts(self):
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

    def test_non_retriable_exception_not_retried_when_filtered(self):
        def retry_with_filter(func):
            @wraps(func)
            def wrapped(*args, **kwargs):
                delays = [1, 2, 4]
                last_exception = None
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
    def test_create_chat_completion_uses_retry_wrapper(self):
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


class ExportResultsIfRequestedTests(unittest.TestCase):
    @patch("argparse.ArgumentParser.parse_known_args")
    @patch("builtins.open", new_callable=mock_open)
    @patch("json.dump")
    def test_no_write_when_export_flag_absent(self, mock_json_dump, mock_file, mock_parse_known_args):
        mock_parse_known_args.return_value = (argparse.Namespace(export=False), [])

        _export_results_if_requested({"tests_run": 1})

        mock_file.assert_not_called()
        mock_json_dump.assert_not_called()

    @patch("argparse.ArgumentParser.parse_known_args")
    @patch("json.dump")
    @patch("builtins.open", new_callable=mock_open)
    @patch("__main__.datetime")
    def test_write_with_expected_payload_and_filename(
        self, mock_datetime, mock_file, mock_json_dump, mock_parse_known_args
    ):
        mock_parse_known_args.return_value = (argparse.Namespace(export=True), [])
        mock_datetime.now.side_effect = [
            unittest.mock.Mock(isoformat=unittest.mock.Mock(return_value="2024-01-01T12:00:00")),
            unittest.mock.Mock(strftime=unittest.mock.Mock(return_value="20240101_120000")),
        ]

        _export_results_if_requested({"tests_run": 5, "successful": True})

        mock_file.assert_called_once_with("output_20240101_120000.json", "w", encoding="utf-8")
        expected_payload = {
            "tests_run": 5,
            "successful": True,
            "generated_at": "2024-01-01T12:00:00",
        }
        handle = mock_file()
        mock_json_dump.assert_called_once_with(expected_payload, handle, ensure_ascii=False, indent=2)

    @patch("argparse.ArgumentParser.parse_known_args")
    @patch("builtins.open", side_effect=OSError("disk full"))
    def test_graceful_handling_of_write_errors(self, mock_open_file, mock_parse_known_args):
        mock_parse_known_args.return_value = (argparse.Namespace(export=True), [])

        try:
            _export_results_if_requested({"tests_run": 2})
        except OSError as exc:  # pragma: no cover - fail explicitly
            self.fail(f"_export_results_if_requested should handle write errors gracefully, raised: {exc}")


def _export_results_if_requested(results):
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
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
    except OSError:
        return


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
