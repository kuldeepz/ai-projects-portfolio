import os
import sys
import types
import pytest

import evaluator


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
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "some_path"])
    monkeypatch.setattr(os.path, "exists", lambda p: p == "some_path")
    monkeypatch.setattr(os.path, "isfile", lambda p: False)

    with pytest.raises(SystemExit) as exc:
        evaluator.validate_environment()

    assert exc.value.code == 1


def test_validate_environment_unreadable_file(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "suite.json"])
    monkeypatch.setattr(os.path, "exists", lambda p: p == "suite.json")
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    monkeypatch.setattr(os, "access", lambda p, mode: False)

    with pytest.raises(SystemExit) as exc:
        evaluator.validate_environment()

    assert exc.value.code == 1


def test_validate_environment_valid_setup(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "suite.json", "--flag"])
    monkeypatch.setattr(os.path, "exists", lambda p: p == "suite.json")
    monkeypatch.setattr(os.path, "isfile", lambda p: True)
    monkeypatch.setattr(os, "access", lambda p, mode: True)

    evaluator.validate_environment()


def test_main_validates_before_run_evaluation(monkeypatch):
    calls = []

    def fake_validate():
        calls.append("validate")

    def fake_run(*args, **kwargs):
        calls.append("run")

    monkeypatch.setattr(evaluator, "validate_environment", fake_validate)
    monkeypatch.setattr(evaluator, "run_evaluation", fake_run)

    # Make parse path deterministic regardless of implementation details.
    monkeypatch.setattr(sys, "argv", ["evaluator.py"])

    # Some versions may rely on argparse in main; provide fallback no-op if needed.
    if not hasattr(evaluator, "main"):
        pytest.skip("main() not present in evaluator module")

    try:
        evaluator.main()
    except SystemExit:
        # Allow CLI-oriented exit behavior; ordering assertion still valid.
        pass

    assert calls and calls[0] == "validate"
    assert "run" in calls
