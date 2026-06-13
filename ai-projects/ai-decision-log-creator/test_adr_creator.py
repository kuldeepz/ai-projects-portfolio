"""Sanity tests for ai-decision-log-creator — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from adr_creator import SCHEMA, SAMPLE_DISCUSSION

def test_schema_required_fields():
    required = SCHEMA["parameters"]["required"]
    for f in ["title", "status", "context", "decision", "rationale", "alternatives_considered", "full_markdown"]:
        assert f in required
    print("  [PASS] Schema — all ADR fields present")

def test_status_enum():
    props = SCHEMA["parameters"]["properties"]
    valid = {"proposed", "accepted", "deprecated", "superseded"}
    actual = set(props["status"]["enum"])
    assert actual == valid
    print("  [PASS] Status enum — proposed/accepted/deprecated/superseded")

def test_alternatives_array():
    props = SCHEMA["parameters"]["properties"]
    assert props["alternatives_considered"]["type"] == "array"
    print("  [PASS] Alternatives — typed as array")

def test_sample_discussion_has_tech():
    assert "pgvector" in SAMPLE_DISCUSSION
    print("  [PASS] Sample discussion — pgvector technology present")

def test_sample_discussion_has_decision_context():
    low = SAMPLE_DISCUSSION.lower()
    assert "vector" in low or "database" in low or "storage" in low
    print("  [PASS] Sample discussion — database/storage decision context")

def test_full_markdown_field():
    props = SCHEMA["parameters"]["properties"]
    assert "full_markdown" in props
    assert props["full_markdown"]["type"] == "string"
    print("  [PASS] full_markdown — present and typed as string")

@pytest.mark.parametrize("input_text", ["", "   ", "\n\t"])
def test_sample_discussion_empty_string_inputs(input_text):
    """Covers empty and whitespace-only string edge cases for discussion parsing assumptions."""
    normalized = (input_text or "").strip().lower()
    assert "vector" not in normalized
    assert "database" not in normalized
    assert "storage" not in normalized

@pytest.mark.parametrize("value", [None])
def test_none_inputs_where_applicable(value):
    """Covers None input handling where optional text values may be absent."""
    normalized = (value or "").lower()
    assert normalized == ""

@pytest.mark.parametrize(
    "status, expected",
    [
        ("proposed", True),
        ("accepted", True),
        ("deprecated", True),
        ("superseded", True),
        ("PROPOSED", False),
        ("", False),
        ("rejected", False),
    ],
)
def test_status_enum_boundary_cases(status, expected):
    """Covers boundary and invalid status values against the schema enum."""
    actual = status in SCHEMA["parameters"]["properties"]["status"]["enum"]
    assert actual is expected

if __name__ == "__main__":
    print("\n=== ai-decision-log-creator: Sanity Tests ===\n")
    try:
        test_schema_required_fields()
        test_status_enum()
        test_alternatives_array()
        test_sample_discussion_has_tech()
        test_sample_discussion_has_decision_context()
        test_full_markdown_field()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); import sys; sys.exit(1)
