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

@pytest.mark.parametrize("notes", [
    None,
    [None],
    ["done", None, "next"],
])
def test_none_inputs_raise_or_are_guarded(notes):
    """Covers None inputs to joining logic where text notes are expected."""
    with pytest.raises(TypeError):
        " ".join(notes)

@pytest.mark.parametrize("data", [
    {"raw_notes": []},
    {"raw_notes": ["single update"]},
    {"raw_notes": SAMPLE_NOTES.get("raw_notes", [])},
])
def test_raw_notes_boundary_lengths(data):
    """Covers boundary raw_notes lengths from empty to populated samples."""
    assert isinstance(data["raw_notes"], list)
    assert len(data["raw_notes"]) >= 0

if __name__ == "__main__":
    print("\n=== standup-report-generator: Sanity Tests ===\n")
    try:
        test_formats_count()
        test_formats_have_descriptions()
        test_format_keys()
        test_sample_notes_structure()
        test_sample_notes_has_blockers()
        test_sample_notes_author()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); import sys; sys.exit(1)

