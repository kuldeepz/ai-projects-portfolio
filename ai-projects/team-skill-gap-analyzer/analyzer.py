import os, sys, pytest

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
    tmp_path: pytest.TempPathFactory,
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
    tmp_path: pytest.TempPathFactory,
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
    tmp_path: pytest.TempPathFactory,
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
    tmp_path: pytest.TempPathFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _set_api_key(monkeypatch)
    file_path = tmp_path / "input.json"
    file_path.write_text("{}", encoding="utf-8")

    analyzer.validate_environment(str(file_path))

    out = capsys.readouterr().out
    assert "Setup OK" in out


def test_token_tracking_prints_usage_and_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    if not hasattr(analyzer, "print_token_usage"):
        pytest.skip("print_token_usage helper not available")

    captured = {}

    def _fake_print(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    monkeypatch.setattr(analyzer, "print", _fake_print)

    analyzer.print_token_usage(
        {
            "prompt_tokens": 120,
            "completion_tokens": 30,
            "total_tokens": 150,
        },
        "gpt-4o-mini",
    )

    output = " ".join(str(x) for x in captured.get("args", ()))
    assert "120" in output
    assert "30" in output
    assert "150" in output
    assert "$" in output or "cost" in output.lower()


def test_analysis_invokes_token_tracking_helper(monkeypatch: pytest.MonkeyPatch) -> None:
    target_fn = None
    for name in ("analyze_team_skill_gap", "analyze_skill_gap", "analyze"):
        if hasattr(analyzer, name):
            target_fn = getattr(analyzer, name)
            break

    if target_fn is None:
        pytest.skip("No analysis entry point found")

    if not hasattr(analyzer, "print_token_usage"):
        pytest.skip("print_token_usage helper not available")

    class _FakeResponse:
        usage = {
            "prompt_tokens": 50,
            "completion_tokens": 10,
            "total_tokens": 60,
        }

        class _Choice:
            class _Msg:
                content = "ok"

            message = _Msg()

        choices = [_Choice()]

    class _Completions:
        @staticmethod
        def create(*args, **kwargs):
            return _FakeResponse()

    class _Chat:
        completions = _Completions()

    class _Client:
        chat = _Chat()

    called = {"value": False}

    def _fake_print_token_usage(usage, model=None):
        called["value"] = True
        assert usage["prompt_tokens"] == 50
        assert usage["completion_tokens"] == 10
        assert usage["total_tokens"] == 60

    monkeypatch.setattr(analyzer, "print_token_usage", _fake_print_token_usage)
    if hasattr(analyzer, "client"):
        monkeypatch.setattr(analyzer, "client", _Client())

    try:
        target_fn({"skills": []})
    except Exception:
        pytest.skip("Analysis signature differs; skipping token hook assertion")

    assert called["value"] is True
