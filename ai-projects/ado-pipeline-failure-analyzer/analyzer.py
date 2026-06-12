import time
from unittest.mock import Mock

import pytest

import analyzer


def test_retry_with_backoff_success_first_call(monkeypatch):
    create_mock = Mock(return_value={"ok": True})
    sleep_mock = Mock()

    monkeypatch.setattr(analyzer, "get_client", lambda: Mock(chat=Mock(completions=Mock(create=create_mock))))
    monkeypatch.setattr(analyzer.time, "sleep", sleep_mock)

    result = analyzer.create_chat_completion(model="gpt-4o-mini", messages=[])

    assert result == {"ok": True}
    assert create_mock.call_count == 1
    sleep_mock.assert_not_called()


def test_retry_with_backoff_retry_then_success(monkeypatch):
    create_mock = Mock(side_effect=[Exception("temporary"), {"ok": True}])
    sleep_mock = Mock()

    monkeypatch.setattr(analyzer, "get_client", lambda: Mock(chat=Mock(completions=Mock(create=create_mock))))
    monkeypatch.setattr(analyzer.time, "sleep", sleep_mock)

    result = analyzer.create_chat_completion(model="gpt-4o-mini", messages=[])

    assert result == {"ok": True}
    assert create_mock.call_count == 2
    sleep_mock.assert_called_once_with(1)


def test_retry_with_backoff_exhaust_retries_and_raise(monkeypatch):
    create_mock = Mock(side_effect=Exception("always fails"))
    sleep_mock = Mock()

    monkeypatch.setattr(analyzer, "get_client", lambda: Mock(chat=Mock(completions=Mock(create=create_mock))))
    monkeypatch.setattr(analyzer.time, "sleep", sleep_mock)

    with pytest.raises(Exception, match="always fails"):
        analyzer.create_chat_completion(model="gpt-4o-mini", messages=[])

    assert create_mock.call_count == 3
    assert sleep_mock.call_count == 2
    sleep_mock.assert_any_call(1)
    sleep_mock.assert_any_call(2)
