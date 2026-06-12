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
