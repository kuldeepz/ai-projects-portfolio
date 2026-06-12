import os
import sys
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
    monkeypatch.setattr(sys, "argv", ["evaluator.py", "--suite-file", "suite.json", "--flag"])
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

    monkeypatch.setattr(evaluator, "validate_environment", fake_validate_env)
    monkeypatch.setattr(evaluator, "validate_suite", fake_validate_suite)
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

    assert calls
    assert calls[0] == "validate_environment"
    assert "validate_suite" in calls
    assert "run" in calls
    assert calls.index("validate_suite") < calls.index("run")
