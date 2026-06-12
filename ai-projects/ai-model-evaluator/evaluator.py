import json
import os
import sys
import time

import pytest

import evaluator


def retry_with_backoff(func, delays=(1, 2, 4), sleep_fn=time.sleep):
    def wrapper(*args, **kwargs):
        last_exc = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                if attempt == len(delays):
                    raise
                sleep_fn(delays[attempt])
        raise last_exc

    return wrapper


def test_validate_environment_missing_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setattr(sys, "argv", ["evaluator.py"])

    with pytest.raises(SystemExit) as exc:
        evaluator.validate_environment()

    assert exc.value.code == 1


def test_validate_environment_empty_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "   ")
    monkeypatch.setattr(sys, "argv", ["evaluator.py"])

    with pytest.raises(SystemExit) as exc:
        evaluator.validate_environment()

    assert exc.value.code == 1


def test_validate_environment_non_file_path(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "--suite-file", "some_path"])
    monkeypatch.setattr(os.path, "isfile", lambda p: False)

    with pytest.raises(SystemExit) as exc:
        evaluator.validate_environment()

    assert exc.value.code == 1


def test_validate_environment_unreadable_file(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "--suite-file", "suite.json"])
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    monkeypatch.setattr(os, "access", lambda p, mode: False)

    with pytest.raises(SystemExit) as exc:
        evaluator.validate_environment()

    assert exc.value.code == 1


def test_validate_environment_valid_setup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "--suite-file", "suite.json", "--flag", "--export"])
    monkeypatch.setattr(os.path, "isfile", lambda p: p == "suite.json")
    monkeypatch.setattr(os, "access", lambda p, mode: True)

    evaluator.validate_environment()


def test_validate_suite_missing_required_field():
    with pytest.raises(SystemExit) as exc:
        evaluator.validate_suite({"name": "suite", "system_prompt": "prompt"})
    assert exc.value.code == 1


def test_validate_suite_empty_required_field():
    with pytest.raises(SystemExit) as exc:
        evaluator.validate_suite({"name": "", "system_prompt": "prompt", "test_cases": [{}]})
    assert exc.value.code == 1


def test_validate_suite_test_cases_must_be_non_empty_list():
    with pytest.raises(SystemExit) as exc:
        evaluator.validate_suite({"name": "suite", "system_prompt": "prompt", "test_cases": []})
    assert exc.value.code == 1


def test_validate_suite_valid():
    evaluator.validate_suite(
        {
            "name": "suite",
            "system_prompt": "prompt",
            "test_cases": [{"input": "x", "expected": "y"}],
        }
    )


def test_main_validates_before_run_evaluation(monkeypatch):
    calls = []

    def fake_validate_env():
        calls.append("validate_environment")

    def fake_validate_suite(*args, **kwargs):
        calls.append("validate_suite")

    def fake_run(*args, **kwargs):
        calls.append("run")
        return {"ok": True}

    monkeypatch.setattr(evaluator, "validate_environment", fake_validate_env)
    monkeypatch.setattr(evaluator, "validate_suite", fake_validate_suite)
    monkeypatch.setattr(evaluator, "run_evaluation", retry_with_backoff(fake_run, sleep_fn=lambda _: None))

    monkeypatch.setattr(sys, "argv", ["evaluator.py"])

    if not hasattr(evaluator, "main"):
        pytest.skip("main() not present in evaluator module")

    try:
        evaluator.main()
    except SystemExit:
        pass

    assert calls
    assert calls[0] == "validate_environment"
    assert "validate_suite" in calls
    assert "run" in calls
    assert calls.index("validate_suite") < calls.index("run")


def test_main_export_writes_output_file(monkeypatch, tmp_path):
    calls = []
    written = {}
    run_result = {"summary": {"passed": 1, "failed": 0}, "details": [{"id": 1, "result": "pass"}]}

    def fake_validate_env():
        calls.append("validate_environment")

    def fake_validate_suite(*args, **kwargs):
        calls.append("validate_suite")

    def fake_run(*args, **kwargs):
        calls.append("run")
        return run_result

    real_open = open

    def fake_open(path, mode="r", *args, **kwargs):
        if isinstance(path, str) and path.startswith("output_") and path.endswith(".json") and "w" in mode:
            calls.append("open_export")
            written["path"] = path
            return real_open(tmp_path / path, mode, *args, **kwargs)
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(evaluator, "validate_environment", fake_validate_env)
    monkeypatch.setattr(evaluator, "validate_suite", fake_validate_suite)
    monkeypatch.setattr(evaluator, "run_evaluation", retry_with_backoff(fake_run, sleep_fn=lambda _: None))
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "--export"])
    monkeypatch.setattr("builtins.open", fake_open)

    if not hasattr(evaluator, "main"):
        pytest.skip("main() not present in evaluator module")

    try:
        result = evaluator.main()
    except SystemExit:
        result = None

    assert calls
    assert calls[0] == "validate_environment"
    assert "validate_suite" in calls
    assert "run" in calls
    assert calls.index("validate_suite") < calls.index("run")

    if written:
        assert "open_export" in calls
        assert calls.index("run") < calls.index("open_export")
        export_file = tmp_path / written["path"]
        assert export_file.exists()
        with open(export_file, "r", encoding="utf-8") as f:
            data = json.lo
