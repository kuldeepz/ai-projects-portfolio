import json
from datetime import datetime
from pathlib import Path

import pytest
from rich.console import Console

import postmortem

console = Console()


def test_validate_environment_exits_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py"])

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with console.status("[bold green]Processing..."):
        with pytest.raises(SystemExit) as exc:
            postmortem.validate_environment()

    assert exc.value.code == 1
    assert any("OPENAI_API_KEY is not set" in m for m in printed)


def test_validate_environment_exits_when_no_input_files_provided(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "-v", "--verbose"])

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with console.status("[bold green]Processing..."):
        with pytest.raises(SystemExit) as exc:
            postmortem.validate_environment()

    assert exc.value.code == 2
    assert any("Provide at least one input file" in m for m in printed)


def test_validate_environment_exits_when_path_not_found(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "missing.json"])
    monkeypatch.setattr(postmortem.os.path, "exists", lambda p: False)

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with console.status("[bold green]Processing..."):
        with pytest.raises(SystemExit) as exc:
            postmortem.validate_environment()

    assert exc.value.code == 1
    assert any("File not found: missing.json" in m for m in printed)


def test_validate_environment_exits_when_not_a_file(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "path"])
    monkeypatch.setattr(postmortem.os.path, "exists", lambda p: True)
    monkeypatch.setattr(postmortem.os.path, "isfile", lambda p: False)

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with console.status("[bold green]Processing..."):
        with pytest.raises(SystemExit) as exc:
            postmortem.validate_environment()

    assert exc.value.code == 1
    assert any("Not a file: path" in m for m in printed)


def test_validate_environment_exits_when_unreadable_file(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "incident.json"])
    monkeypatch.setattr(postmortem.os.path, "exists", lambda p: True)
    monkeypatch.setattr(postmortem.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(postmortem.os, "access", lambda p, mode: False)

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with console.status("[bold green]Processing..."):
        with pytest.raises(SystemExit) as exc:
            postmortem.validate_environment()

    assert exc.value.code == 1
    assert any("File is not readable: incident.json" in m for m in printed)


def test_validate_environment_success_verbose(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "-v", "incident.json", "--verbose"])
    monkeypatch.setattr(postmortem.os.path, "exists", lambda p: True)
    monkeypatch.setattr(postmortem.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(postmortem.os, "access", lambda p, mode: True)

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with console.status("[bold green]Processing..."):
        postmortem.validate_environment()

    assert any("Setup OK" in m for m in printed)


def test_validate_environment_success_non_verbose_no_setup_banner(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "incident.json"])
    monkeypatch.setattr(postmortem.os.path, "exists", lambda p: True)
    monkeypatch.setattr(postmortem.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(postmortem.os, "access", lambda p, mode: True)

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with console.status("[bold green]Processing..."):
        postmortem.validate_environment()

    assert not any("Setup OK" in m for m in printed)


def test_validate_environment_ignores_non_file_flag_arguments(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "--mode", "dry-run", "incident.json"])

    checked = []

    def fake_exists(p):
        checked.append(p)
        return p == "incident.json"

    monkeypatch.setattr(postmortem.os.path, "exists", fake_exists)
    monkeypatch.setattr(postmortem.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(postmortem.os, "access", lambda p, mode: True)

    with console.status("[bold green]Processing..."):
        postmortem.validate_environment()

    assert "incident.json" in checked
    assert "--mode" not in checked
    assert "dry-run" not in checked


def test_export_results_writes_timestamped_json(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    fixed_time = datetime(2024, 1, 2, 3, 4, 5)
    monkeypatch.setattr(postmortem, "datetime", type("D", (), {"now": staticmethod(lambda: fixed_time)}))

    results = {"summary": "ok", "items": [1, 2, 3]}
    filename = postmortem.export_results(results)

    assert filename == "output_20240102_030405.json"
    out = Path(filename)
    assert out.exists()

    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"] == "ok"
    assert data["items"] == [1, 2, 3]
    assert data["generated_at"] == "2024-01-02T03:04:05"


def test_validate_environment_ignores_export_flags_as_input_files(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "-e", "incident.json"])

    checked = []

    def fake_exists(p):
        checked.append(p)
        return p == "incident.json"

    monkeypatch.setattr(postmortem.os.path, "exists", fake_exists)
    monkeypatch.setattr(postmortem.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(postmortem.os, "access", lambda p, mode: True)

    with console.status("[bold green]Processing..."):
        postmortem.validate_environment()

    assert "incident.json" in checked
    assert "-e" not in checked
