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

    class FixedDateTime:
        @classmethod
        def now(cls):
            return datetime(2024, 1, 2, 3, 4, 5)

    monkeypatch.setattr(postmortem, "datetime", FixedDateTime)

    results = {"summary": "ok", "details": {"a": 1}}
    out_path = postmortem.export_results(results)

    assert Path(out_path).exists()
    assert Path(out_path).name == "postmortem_20240102_030405.json"
    assert json.loads(Path(out_path).read_text(encoding="utf-8")) == results


def test_main_with_export_triggers_export_results(monkeypatch, tmp_path):
    input_file = tmp_path / "incident.json"
    input_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(
        postmortem.sys,
        "argv",
        ["postmortem.py", "--export", str(input_file)],
    )

    monkeypatch.setattr(postmortem.os.path, "exists", lambda p: True)
    monkeypatch.setattr(postmortem.os.path, "isfile", lambda p: True)
    monkeypatch.setattr(postmortem.os, "access", lambda p, mode: True)

    monkeypatch.setattr(postmortem, "collect_json_files", lambda: [str(input_file)])
    monkeypatch.setattr(postmortem, "read_incident_files", lambda files: [{"id": "inc-1"}])
    monkeypatch.setattr(postmortem, "generate_postmortem", lambda incidents: {"summary": "generated"})

    called = {}

    def fake_export_results(result):
        called["result"] = result
        return str(tmp_path / "export.json")

    monkeypatch.setattr(postmortem, "export_results", fake_export_results)

    postmortem.main()

    assert called.get("result") == {"summary": "generated"}
