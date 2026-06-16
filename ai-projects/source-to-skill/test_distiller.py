"""
Tests for the source-to-skill distiller.

These cover the pure, offline logic (ingestion routing, validation, slugify,
writing) without hitting the network or the Claude API.

Run:  python -m pytest test_distiller.py -v
"""

from pathlib import Path

import pytest

import distiller
from distiller import SkillDoc


# ─── slugify ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Hello World", "hello-world"),
        ("RAG vs Fine-Tuning!", "rag-vs-fine-tuning"),
        ("  spaced  out  ", "spaced-out"),
        ("Under_scores_too", "under-scores-too"),
        ("", "untitled"),
    ],
)
def test_slugify(raw, expected):
    assert distiller.slugify(raw) == expected


# ─── ingest routing ──────────────────────────────────────────────────────────


def test_ingest_text_file(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("hello knowledge")
    kind, title, text = distiller.ingest(str(f))
    assert kind == "text file"
    assert title == "note"
    assert "hello knowledge" in text


def test_ingest_unsupported_extension(tmp_path):
    f = tmp_path / "data.xyz"
    f.write_text("nope")
    with pytest.raises(SystemExit):
        distiller.ingest(str(f))


def test_ingest_missing_file():
    with pytest.raises(SystemExit):
        distiller.ingest("/no/such/file.pdf")


def test_truncate_long_source():
    text = "x" * (distiller.MAX_SOURCE_CHARS + 100)
    out, truncated = distiller._truncate(text)
    assert truncated is True
    assert len(out) == distiller.MAX_SOURCE_CHARS


# ─── skill validation ─────────────────────────────────────────────────────────


def _valid_skill_body() -> str:
    return (
        "# Sample Skill\n> does a thing\n\n"
        "## When to Use\nwhen X\n\n"
        "## Steps\n1. do it\n\n"
        "## Output Format\nmarkdown\n\n"
        "## Example Invocation\n```\n/sample\n```\n\n"
        "## Notes\n- none\n"
    )


def test_validate_skill_ok():
    doc = SkillDoc(
        name="sample-skill",
        category="developer",
        description="Do a thing. Use when X.",
        body=_valid_skill_body(),
    )
    assert distiller.validate_skill(doc) == []


def test_validate_skill_bad_category_defaults():
    doc = SkillDoc(
        name="sample-skill",
        category="marketing",
        description="x",
        body=_valid_skill_body(),
    )
    problems = distiller.validate_skill(doc)
    assert any("category" in p for p in problems)
    assert doc.category == "developer"  # mutated to a valid default


def test_validate_skill_missing_section():
    body = "# Title\n> x\n\n## When to Use\ny\n\n## Steps\n1. z\n"
    doc = SkillDoc(
        name="sample-skill", category="developer", description="x", body=body
    )
    problems = distiller.validate_skill(doc)
    assert any("Output Format" in p for p in problems)


# ─── writing ──────────────────────────────────────────────────────────────────


def test_write_note(tmp_path):
    path = distiller.write_note(
        "# T\n> s\n\ncontent", "My Title", "http://example.com", tmp_path
    )
    assert path == tmp_path / "my-title.md"
    written = path.read_text()
    assert "source: http://example.com" in written
    assert "content" in written


# ─── budget tracking ──────────────────────────────────────────────────────────


class _FakeUsage:
    def __init__(self, prompt_tokens, completion_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


def test_estimate_cost_inr_uncached():
    # 1M uncached input + 1M output, in INR
    cost = distiller.estimate_cost_inr(1_000_000, 1_000_000)
    expected = (
        distiller.USD_PER_1M_INPUT + distiller.USD_PER_1M_OUTPUT
    ) * distiller.USD_TO_INR
    assert round(cost, 2) == round(expected, 2)


def test_estimate_cost_inr_credits_cached_tokens():
    # All input cached -> cheaper than all-uncached
    all_uncached = distiller.estimate_cost_inr(1_000_000, 0, cached_tokens=0)
    all_cached = distiller.estimate_cost_inr(1_000_000, 0, cached_tokens=1_000_000)
    assert all_cached < all_uncached


def test_record_usage_accumulates(tmp_path, monkeypatch):
    monkeypatch.setattr(distiller, "LEDGER_PATH", tmp_path / "usage.cache.json")
    distiller.record_usage(_FakeUsage(1000, 500))
    ledger = distiller.record_usage(_FakeUsage(1000, 500))
    assert ledger["calls"] == 2
    assert ledger["input_tokens"] == 2000
    assert ledger["output_tokens"] == 1000
    assert ledger["spent_inr"] > 0


def test_check_budget_blocks_when_over(tmp_path, monkeypatch):
    monkeypatch.setattr(distiller, "LEDGER_PATH", tmp_path / "usage.cache.json")
    monkeypatch.setattr(distiller, "BUDGET_INR", 0.0001)
    distiller.record_usage(_FakeUsage(1000, 1000))
    with pytest.raises(SystemExit):
        distiller.check_budget()


def test_check_budget_ok_when_under(tmp_path, monkeypatch):
    monkeypatch.setattr(distiller, "LEDGER_PATH", tmp_path / "usage.cache.json")
    monkeypatch.setattr(distiller, "BUDGET_INR", 8000.0)
    distiller.record_usage(_FakeUsage(1000, 1000))
    distiller.check_budget()  # should not raise


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
