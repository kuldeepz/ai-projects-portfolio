"""Sanity tests for ai-decision-log-creator — no API key required."""
import sys, os
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
