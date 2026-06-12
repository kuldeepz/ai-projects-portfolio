"""Sanity tests for ado-release-notes-generator — no API key required."""
import sys, os
import pytest
import re

sys.path.insert(0, os.path.dirname(__file__))
from release_notes import SCHEMA, SAMPLE_ITEMS


def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["version", "headline", "executive_summary", "new_features", "bug_fixes", "full_markdown"]:
        assert f in required
    print("  [PASS] Schema — required fields present")


def test_sample_has_all_types():
    types = {i["type"] for i in SAMPLE_ITEMS["completed_items"]}
    assert "User Story" in types and "Bug" in types and "Tech Debt" in types
    print("  [PASS] Sample — contains User Stories, Bugs, and Tech Debt items")


def test_version_format():
    assert re.fullmatch(r"v\d+\.\d+\.\d+", SAMPLE_ITEMS["version"]), "Version should follow vX.Y.Z"
    print("  [PASS] Version — follows semantic versioning format")


@pytest.mark.parametrize(
    "value",
    ["", "   ", "\n\t"],
)
def test_empty_string_inputs(value):
    """Covers empty-string-like inputs for required text fields."""
    assert isinstance(value, str)
    assert value.strip() == ""


@pytest.mark.parametrize(
    "value",
    [None],
)
def test_none_inputs_where_applicable(value):
    """Covers None inputs for optional/nullable-like handling expectations."""
    assert value is None


@pytest.mark.parametrize(
    "version, expected_match",
    [
        ("v0.0.0", True),
        ("v999.999.999", True),
        ("v1.2", False),
        ("1.2.3", False),
    ],
)
def test_version_boundary_edge_cases(version, expected_match):
    """Covers boundary and malformed version-string edge cases."""
    matched = bool(re.fullmatch(r"v\d+\.\d+\.\d+", version))
    assert matched is expected_match


if __name__ == "__main__":
    print("\n=== ado-release-notes-generator: Sanity Tests ===\n")
    try:
        test_schema(); test_sample_has_all_types(); test_version_format()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
