import importlib.util
from pathlib import Path


def _load_composer_module():
    module_path = Path(__file__).resolve().parents[1] / "composer.py"
    spec = importlib.util.spec_from_file_location("composer", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load composer module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_print_usage_no_pricing_configured(monkeypatch):
    composer = _load_composer_module()

    captured: list[str] = []

    class StubConsole:
        def print(self, message):
            captured.append(str(message))

    monkeypatch.setattr(composer, "console", StubConsole())
    monkeypatch.setattr(composer, "CHAT_MODEL", "unknown-model")

    composer.print_usage(120, 80)

    assert len(captured) == 2
    assert "Usage: prompt=120, completion=80, total=200 tokens" in captured[0]
    assert "Cost estimate unavailable" in captured[1]
    assert "unknown-model" in captured[1]


def test_print_usage_with_pricing_formats_cost(monkeypatch):
    composer = _load_composer_module()

    captured: list[str] = []

    class StubConsole:
        def print(self, message):
            captured.append(str(message))

    monkeypatch.setattr(composer, "console", StubConsole())
    monkeypatch.setattr(composer, "CHAT_MODEL", "gpt-4o-mini")

    composer.print_usage(1000, 500)

    assert len(captured) == 1
    line = captured[0]
    assert "Usage: prompt=1000, completion=500, total=1500 tokens" in line
    assert "Estimated cost ($0.15/1M in, $0.6/1M out): $0.000450" in line
