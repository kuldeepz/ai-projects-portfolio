import pytest

import postmortem


def test_validate_environment_exits_when_api_key_missing(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py"])

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

    with pytest.raises(SystemExit) as exc:
        postmortem.validate_environment()

    assert exc.value.code == 1
    assert any("OPENAI_API_KEY is not set" in m for m in printed)


def test_validate_environment_exits_when_path_not_found(monkeypatch):
    monkeypatch.setattr(postmortem.os, "getenv", lambda k: "key" if k == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(postmortem.sys, "argv", ["postmortem.py", "missing.json"])
    monkeypatch.setattr(postmortem.os.path, "exists", lambda p: False)

    printed = []
    monkeypatch.setattr(postmortem.console, "print", lambda msg: printed.append(str(msg)))

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

    postmortem.validate_environment()

    assert not any("Setup OK" in m for m in printed)
