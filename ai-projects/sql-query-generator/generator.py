import os
import sys
import time
from pathlib import Path
from contextlib import nullcontext

import pytest

import generator


def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt < len(delays):
                    time.sleep(delays[attempt])
                else:
                    raise last_exc

    return wrapper


class _DummyStatus:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_generate_sql_returns_parsed_tool_args_with_status(monkeypatch):
    monkeypatch.setattr(generator.console, "status", lambda *a, **k: _DummyStatus())

    class _Resp:
        output = [
            type(
                "Item",
                (),
                {
                    "type": "function_call",
                    "name": "emit_sql",
                    "arguments": '{"sql":"SELECT 1"}',
                },
            )()
        ]

    class _Responses:
        @staticmethod
        @retry_with_backoff
        def create(*args, **kwargs):
            return _Resp()

    class _Client:
        responses = _Responses()

    monkeypatch.setattr(generator, "get_client", lambda: _Client())

    result = generator.generate_sql("show one", [])
    assert result == {"sql": "SELECT 1"}


def test_load_schema_missing_file_still_exits_with_status(monkeypatch, tmp_path):
    monkeypatch.setattr(generator.console, "status", lambda *a, **k: _DummyStatus())

    missing = tmp_path / "missing_schema.sql"
    with pytest.raises(SystemExit) as exc:
        generator.load_schema([str(missing)])
    assert exc.value.code == 1


def test_main_validates_then_enters_interactive_mode_with_status(monkeypatch, tmp_path):
    monkeypatch.setattr(generator.console, "status", lambda *a, **k: _DummyStatus())

    calls = []

    def _validate(schema_paths=None, require_api_key=True):
        calls.append(("validate", schema_paths, require_api_key))

    def _interactive(schema_paths=None):
        calls.append(("interactive", schema_paths))

    monkeypatch.setattr(generator, "validate_environment", _validate)
    monkeypatch.setattr(generator, "interactive_mode", _interactive)

    schema = tmp_path / "schema.sql"
    schema.write_text("create table t(id int);")

    monkeypatch.setattr(
        sys,
        "argv",
        ["generator.py", "--schema", str(schema)],
    )

    generator.main()

    assert calls[0][0] == "validate"
    assert calls[1][0] == "interactive"
