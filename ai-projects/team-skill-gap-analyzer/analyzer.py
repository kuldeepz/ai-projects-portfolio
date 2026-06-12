import os, sys, pytest
from pathlib import Path

import analyzer


def _set_api_key(monkeypatch: pytest.MonkeyPatch, value: str = "test-key") -> None:
    monkeypatch.setenv("OPENAI_API_KEY", value)


def test_validate_environment_exits_when_api_key_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(None)

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "OPENAI_API_KEY is not set or is empty" in out


def test_validate_environment_exits_when_api_key_blank(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _set_api_key(monkeypatch, "   ")

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(None)

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "OPENAI_API_KEY is not set or is empty" in out


def test_validate_environment_exits_for_missing_file_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_api_key(monkeypatch)
    bad_path = tmp_path / "does_not_exist.json"

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(str(bad_path))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "File not found" in out
    assert str(bad_path) in out


def test_validate_environment_exits_for_directory_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_api_key(monkeypatch)
    dir_path = tmp_path / "data_dir"
    dir_path.mkdir()

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(str(dir_path))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Not a file" in out
    assert str(dir_path) in out


def test_validate_environment_exits_for_unreadable_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_api_key(monkeypatch)
    file_path = tmp_path / "input.json"
    file_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(analyzer.os, "access", lambda p, m: False)

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment(str(file_path))

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "File is not readable" in out
    assert str(file_path) in out


def test_validate_environment_success_with_valid_setup(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_api_key(monkeypatch)
    file_path = tmp_path / "input.json"
    file_path.write_text("{}", encoding="utf-8")

    analyzer.validate_environment(str(file_path))

    out = capsys.readouterr().out
    assert "Setup OK" in out


def test_print_token_usage_outputs_expected_values(capsys: pytest.CaptureFixture[str]) -> None:
    analyzer.print_token_usage(
        prompt_tokens=100,
        completion_tokens=50,
        total_tokens=150,
        estimated_cost=0.0123,
    )

    out = capsys.readouterr().out
    assert "100" in out
    assert "50" in out
    assert "150" in out
    assert "0.0123" in out or "0.012" in out


def test_extract_usage_from_response_dict() -> None:
    response = {
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 80,
            "total_tokens": 200,
        }
    }

    usage = analyzer.extract_token_usage(response)

    assert usage["prompt_tokens"] == 120
    assert usage["completion_tokens"] == 80
    assert usage["total_tokens"] == 200


def test_calculate_estimated_cost_returns_positive_float() -> None:
    cost = analyzer.calculate_estimated_cost(
        prompt_tokens=1000,
        completion_tokens=500,
    )

    assert isinstance(cost, float)
    assert cost >= 0
