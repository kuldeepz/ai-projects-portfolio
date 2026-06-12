import unittest
from unittest.mock import patch, call
from functools import wraps

import release_notes


class NonRetriableError(Exception):
    pass


class TransientError(Exception):
    pass


class RetryableAPIStatusError(Exception):
    def __init__(self, status_code):
        super().__init__(f"status {status_code}")
        self.status_code = status_code


class RetryWithBackoffTests(unittest.TestCase):
    def test_retry_immediate_success_no_sleep(self):
        mock_func = unittest.mock.Mock(return_value="ok")
        wrapped = release_notes.retry_with_backoff(mock_func, retriable_exceptions=(TransientError,))

        with patch("release_notes.time.sleep") as mock_sleep:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()

    def test_retry_succeeds_after_retries_expected_sleeps(self):
        mock_func = unittest.mock.Mock(side_effect=[TransientError("e1"), TransientError("e2"), "ok"])
        wrapped = release_notes.retry_with_backoff(mock_func, retriable_exceptions=(TransientError,))

        with patch("release_notes.time.sleep") as mock_sleep:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(mock_func.call_count, 3)
        mock_sleep.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock_sleep.call_count, 2)

    def test_retry_raises_last_exception_after_max_attempts(self):
        final_exc = TransientError("final")
        mock_func = unittest.mock.Mock(side_effect=[TransientError("e1"), TransientError("e2"), final_exc])
        wrapped = release_notes.retry_with_backoff(mock_func, retriable_exceptions=(TransientError,))

        with patch("release_notes.time.sleep") as mock_sleep:
            with self.assertRaises(TransientError) as ctx:
                wrapped()

        self.assertIs(ctx.exception, final_exc)
        self.assertEqual(mock_func.call_count, 3)
        mock_sleep.assert_has_calls([call(1), call(2)])
        self.assertEqual(mock_sleep.call_count, 2)

    def test_non_retriable_exception_not_retried_when_filtered(self):
        mock_func = unittest.mock.Mock(side_effect=NonRetriableError("stop"))
        wrapped = release_notes.retry_with_backoff(mock_func, retriable_exceptions=(TransientError,))

        with patch("release_notes.time.sleep") as mock_sleep:
            with self.assertRaises(NonRetriableError):
                wrapped()

        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()

    def test_api_status_error_retries_only_for_5xx(self):
        mock_func = unittest.mock.Mock(side_effect=[RetryableAPIStatusError(500), "ok"])
        wrapped = release_notes.retry_with_backoff(
            mock_func,
            retriable_exceptions=(TransientError,),
            retriable_status_exception=RetryableAPIStatusError,
        )

        with patch("release_notes.time.sleep") as mock_sleep:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(mock_func.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    def test_api_status_error_4xx_not_retried(self):
        err = RetryableAPIStatusError(400)
        mock_func = unittest.mock.Mock(side_effect=err)
        wrapped = release_notes.retry_with_backoff(
            mock_func,
            retriable_exceptions=(TransientError,),
            retriable_status_exception=RetryableAPIStatusError,
        )

        with patch("release_notes.time.sleep") as mock_sleep:
            with self.assertRaises(RetryableAPIStatusError) as ctx:
                wrapped()

        self.assertIs(ctx.exception, err)
        self.assertEqual(mock_func.call_count, 1)
        mock_sleep.assert_not_called()


class CreateChatCompletionTests(unittest.TestCase):
    def test_create_chat_completion_uses_retry_wrapper(self):
        with patch("release_notes.get_client") as mock_get_client, patch("release_notes.time.sleep") as mock_sleep:
            create = mock_get_client.return_value.chat.completions.create
            create.side_effect = [Exception("e1"), "response"]

            result = release_notes.create_chat_completion(model="m", messages=[])

        self.assertEqual(result, "response")
        self.assertEqual(create.call_count, 2)
        mock_sleep.assert_called_once_with(1)


if __name__ == "__main__":
    unittest.main()
