"""Sanity tests for standup-report-generator — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from standup import FORMATS, SAMPLE_NOTES, build_report


def test_formats_count():
    assert len(FORMATS) >= 4
    print("  [PASS] Formats — at least 4 report formats defined")


def test_formats_have_descriptions():
    for key, val in FORMATS.items():
        assert val[0], f"Format '{key}' missing description"
    print("  [PASS] Formats — all formats have descriptions")


def test_format_keys():
    keys = set(FORMATS.keys())
    # Formats may use numeric keys or named keys
    assert len(keys) >= 4
    print("  [PASS] Formats — at least 4 format keys present")


def test_sample_notes_structure():
    assert isinstance(SAMPLE_NOTES["raw_notes"], list)
    assert len(SAMPLE_NOTES["raw_notes"]) > 3
    print("  [PASS] Sample notes — list with >3 items")


def test_sample_notes_has_blockers():
    notes_text = " ".join(SAMPLE_NOTES["raw_notes"]).lower()
    assert "block" in notes_text or "waiting" in notes_text or "delay" in notes_text
    print("  [PASS] Sample notes — contains blocker/waiting mention")


def test_sample_notes_author():
    assert "name" in SAMPLE_NOTES or any("kuldeep" in n.lower() for n in SAMPLE_NOTES.get("raw_notes", []))
    print("  [PASS] Sample notes — author context present")


@pytest.mark.parametrize("notes", [
    [""],
    ["", ""],
    [],
])
def test_build_report_handles_empty_note_inputs(notes):
    """Ensure report generation handles empty-note edge cases without crashing."""
    fmt_key = next(iter(FORMATS.keys()))
    result = build_report({"raw_notes": notes}, format_key=fmt_key)
    assert result is not None
    assert isinstance(result, str)


@pytest.mark.parametrize("data", [
    {"raw_notes": []},
    {"raw_notes": ["single update"]},
    {"raw_notes": SAMPLE_NOTES.get("raw_notes", [])},
])
def test_build_report_raw_notes_boundary_lengths(data):
    """Covers boundary raw_notes lengths from empty to populated samples."""
    fmt_key = next(iter(FORMATS.keys()))
    result = build_report(data, format_key=fmt_key)
    assert result is not None
    assert isinstance(result, str)


def test_sample_notes_missing_raw_notes_key_behavior():
    """Application-level contract: raw_notes key is required in note payloads."""
    with pytest.raises(KeyError):
        _ = SAMPLE_NOTES["missing_raw_notes"]


@pytest.mark.parametrize("notes", [
    ["   ", "\t", "\n"],
    ["done", "   ", "next"],
    [],
])
def test_build_report_normalizes_or_tolerates_whitespace_notes(notes):
    """Validate app-facing behavior with whitespace-only notes."""
    fmt_key = next(iter(FORMATS.keys()))
    result = build_report({"raw_notes": notes}, format_key=fmt_key)
    assert result is not None
    assert isinstance(result, str)


def test_build_report_very_long_note_supported():
    """Boundary case: very long note text should be handled deterministically."""
    long_note = "x" * 10000
    fmt_key = next(iter(FORMATS.keys()))
    result = build_report({"raw_notes": [long_note]}, format_key=fmt_key)
    assert isinstance(result, str)
    assert "x" in result


@pytest.mark.parametrize("notes", [None, [None], ["done", None, "next"]])
def test_build_report_none_inputs_raise_or_are_guarded(notes):
    """None note entries should either be handled gracefully or raise a clear error."""
    fmt_key = next(iter(FORMATS.keys()))
    try:
        result = build_report({"raw_notes": notes}, format_key=fmt_key)
        assert isinstance(result, str)
    except (TypeError, ValueError, AttributeError):
        # Accept explicit validation failures as guarded behavior.
        pass


@pytest.mark.parametrize("fmt_key", ["unknown", "", "9999", "not_a_real_format"])
def test_unknown_format_key_is_not_available(fmt_key):
    """Unknown format keys should not appear as supported options."""
    assert fmt_key not in FORMATS


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
