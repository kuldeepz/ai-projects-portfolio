"""Sanity tests for ado-release-notes-generator — no API key required."""
import sys, os
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
    import re
    assert re.match(r"v\d+\.\d+\.\d+", SAMPLE_ITEMS["version"]), "Version should follow vX.Y.Z"
    print("  [PASS] Version — follows semantic versioning format")

if __name__ == "__main__":
    print("\n=== ado-release-notes-generator: Sanity Tests ===\n")
    try:
        test_schema(); test_sample_has_all_types(); test_version_format()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
