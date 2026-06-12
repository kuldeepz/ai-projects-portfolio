import os, sys, pytest

import analyzer


def _set_api_key(monkeypatch, value="test-key"):
    monkeypatch.setenv("OPENAI_API_KEY", value)


def test_validate_environment_exits_when_api_key_missing(monkeypatch, capsys):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(sys, "argv", ["analyzer.py"])

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "OPENAI_API_KEY is not set or is empty" in out


def test_validate_environment_exits_when_api_key_blank(monkeypatch, capsys):
    _set_api_key(monkeypatch, "   ")
    monkeypatch.setattr(sys, "argv", ["analyzer.py"])

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "OPENAI_API_KEY is not set or is empty" in out


def test_validate_environment_exits_for_missing_file_path(monkeypatch, tmp_path, capsys):
    _set_api_key(monkeypatch)
    bad_path = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(sys, "argv", ["analyzer.py", str(bad_path)])

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "File not found" in out
    assert str(bad_path) in out


def test_validate_environment_exits_for_directory_path(monkeypatch, tmp_path, capsys):
    _set_api_key(monkeypatch)
    dir_path = tmp_path / "data_dir"
    dir_path.mkdir()
    monkeypatch.setattr(sys, "argv", ["analyzer.py", str(dir_path)])

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "Not a file" in out
    assert str(dir_path) in out


def test_validate_environment_exits_for_unreadable_file(monkeypatch, tmp_path, capsys):
    _set_api_key(monkeypatch)
    file_path = tmp_path / "input.json"
    file_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["analyzer.py", str(file_path)])

    monkeypatch.setattr(analyzer.os, "access", lambda p, m: False)

    with pytest.raises(SystemExit) as exc:
        analyzer.validate_environment()

    assert exc.value.code == 1
    out = capsys.readouterr().out
    assert "File is not readable" in out
    assert str(file_path) in out


def test_validate_environment_success_with_valid_setup(monkeypatch, tmp_path, capsys):
    _set_api_key(monkeypatch)
    file_path = tmp_path / "input.json"
    file_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["analyzer.py", str(file_path)])

    analyzer.validate_environment()

    out = capsys.readouterr().out
    assert "Setup OK" in out
