"""Sanity tests for pr-review-assistant — no API key required."""
import sys, os
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from reviewer import SCHEMA, VERDICT_COLORS, VERDICT_ICONS, SAMPLE_DIFF

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["overall_verdict", "summary", "comments", "positives", "checklist"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_verdict_coverage():
    verdicts = {"approve", "approve_with_comments", "request_changes", "needs_discussion"}
    assert set(VERDICT_COLORS.keys()) == verdicts
    assert set(VERDICT_ICONS.keys()) == verdicts
    print("  [PASS] Verdict maps — all 4 verdicts have colors and icons")

def test_severity_enum():
    valid = {"blocking", "major", "minor", "nit", "praise"}
    actual = set(SCHEMA["parameters"]["properties"]["comments"]["items"]["properties"]["severity"]["enum"])
    assert actual == valid
    print("  [PASS] Severity enum — 5 levels including 'praise'")

def test_sample_diff_has_issues():
    assert "SQL injection" in SAMPLE_DIFF or "f\"SELECT" in SAMPLE_DIFF
    assert "print(" in SAMPLE_DIFF
    assert "temp1234" in SAMPLE_DIFF
    print("  [PASS] Sample diff — contains SQL injection, debug print, and weak password")

@pytest.mark.parametrize(
    "candidate",
    ["", " ", "\n\t"],
)
def test_empty_string_inputs(candidate):
    """Covers empty-string-like inputs across key exported text constants."""
    assert candidate not in SCHEMA["parameters"]["required"]
    assert candidate not in VERDICT_COLORS
    assert candidate not in VERDICT_ICONS

@pytest.mark.parametrize(
    "candidate",
    [None,],
)
def test_none_inputs_where_applicable(candidate):
    """Covers None inputs for mapping lookups and required-field membership."""
    assert candidate not in SCHEMA["parameters"]["required"]
    assert candidate not in VERDICT_COLORS
    assert candidate not in VERDICT_ICONS

@pytest.mark.parametrize(
    "field_path, expected_min_len",
    [
        (("parameters", "required"), 5),
        (("parameters", "properties", "comments", "items", "properties", "severity", "enum"), 5),
        (("parameters", "properties"), 5),
    ],
)
def test_schema_boundary_cases(field_path, expected_min_len):
    """Covers boundary conditions for schema collection sizes and nesting."""
    node = SCHEMA
    for key in field_path:
        node = node[key]
    assert len(node) >= expected_min_len

if __name__ == "__main__":
    print("\n=== pr-review-assistant: Sanity Tests ===\n")
    try:
        test_schema(); test_verdict_coverage(); test_severity_enum(); test_sample_diff_has_issues()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
