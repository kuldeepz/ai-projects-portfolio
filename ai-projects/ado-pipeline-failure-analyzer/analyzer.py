import argparse
import pytest
from pathlib import Path

import analyzer


def _set_argv(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(analyzer.sys, "argv", ["analyzer.py", *args])


def _args_with_input(path: str | None = None) -> argparse.Namespace:
    return argparse.Namespace(input_file=path)


def test_validate_environment_exits_when_api_key_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(_args_with_input())

    assert exc.value.code == 1


def test_validate_environment_exits_for_nonexistent_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    missing = tmp_path / "missing.log"

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(_args_with_input(str(missing)))

    assert exc.value.code == 1


def test_validate_environment_exits_when_path_is_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    directory = tmp_path / "logs"
    directory.mkdir()

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(_args_with_input(str(directory)))

    assert exc.value.code == 1


def test_validate_environment_exits_when_file_not_readable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    log_file = tmp_path / "pipeline.log"
    log_file.write_text("content", encoding="utf-8")

    monkeypatch.setattr(analyzer.os, "access", lambda *_args, **_kwargs: False)

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(_args_with_input(str(log_file)))

    assert exc.value.code == 1


def test_validate_environment_success_with_valid_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    log_file = tmp_path / "pipeline.log"
    log_file.write_text("ok", encoding="utf-8")

    analyzer.validate_environment(_args_with_input(str(log_file)))


def test_main_runs_analyzer_flow_after_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    monkeypatch.setattr(analyzer, "validate_environment", lambda *_a, **_k: calls.append("validate"))

    if hasattr(analyzer, "run"):
        monkeypatch.setattr(analyzer, "run", lambda: calls.append("run"))
        analyzer.main()
        assert calls == ["validate", "run"]
        return

    if hasattr(analyzer, "analyze_pipeline_failure"):
        monkeypatch.setattr(analyzer, "analyze_pipeline_failure", lambda *a, **k: calls.append("analyze"))
        monkeypatch.setattr(analyzer, "parse_cli_args", lambda: type("Args", (), {"verbose": False})())
        monkeypatch.setattr(analyzer.sys, "argv", ["analyzer.py"])
        analyzer.main()
        assert calls[0] == "validate"
        assert "analyze" in calls
        return

    pytest.skip("No known analyzer entrypoint found to assert integration flow")
