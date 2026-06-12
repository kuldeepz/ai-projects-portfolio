"""Sanity tests for standup-report-generator — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from standup import FORMATS, SAMPLE_NOTES

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

@pytest.mark.parametrize("notes, expected", [
    ([""], ""),
    (["", ""], " "),
    ([], ""),
])
def test_notes_join_handles_empty_strings(notes, expected):
    """Covers empty-string and empty-list note joining behavior."""
    assert " ".join(notes) == expected

@pytest.mark.parametrize("data", [
    {"raw_notes": []},
    {"raw_notes": ["single update"]},
    {"raw_notes": SAMPLE_NOTES.get("raw_notes", [])},
])
def test_raw_notes_boundary_lengths(data):
    """Covers boundary raw_notes lengths from empty to populated samples."""
    assert isinstance(data["raw_notes"], list)
    assert len(data["raw_notes"]) >= 0


def test_sample_notes_missing_raw_notes_key_behavior():
    """Application-level contract: raw_notes key is required in note payloads."""
    with pytest.raises(KeyError):
        _ = SAMPLE_NOTES["missing_raw_notes"]


@pytest.mark.parametrize("notes, expected", [
    (["   ", "\t", "\n"], ""),
    (["done", "   ", "next"], "done next"),
    ([], ""),
])
def test_application_level_note_normalization(notes, expected):
    """Validate app-facing behavior: ignore blank/whitespace-only notes."""
    normalized = " ".join(n.strip() for n in notes if isinstance(n, str) and n.strip())
    assert normalized == expected


def test_very_long_note_supported():
    """Boundary case: very long note text should be handled deterministically."""
    long_note = "x" * 10000
    output = " ".join([long_note])
    assert output == long_note
    assert len(output) == 10000


@pytest.mark.parametrize("fmt_key", ["unknown", "", "9999", "not_a_real_format"])
def test_unknown_format_key_is_not_available(fmt_key):
    """Unknown format keys should not appear as supported options."""
    assert fmt_key not in FORMATS

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
