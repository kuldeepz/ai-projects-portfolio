"""Sanity tests for ado-test-case-generator — no API key required."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from test_case_generator import SCHEMA, SAMPLE_STORY

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["story_summary", "test_cases", "coverage_summary"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_case_type_enum():
    valid = {"happy_path", "edge_case", "negative", "security", "performance"}
    actual = set(SCHEMA["parameters"]["properties"]["test_cases"]["items"]["properties"]["type"]["enum"])
    assert actual == valid
    print("  [PASS] Test case types — all 5 types defined")

def test_priority_enum():
    valid = {"critical", "high", "medium", "low"}
    actual = set(SCHEMA["parameters"]["properties"]["test_cases"]["items"]["properties"]["priority"]["enum"])
    assert actual == valid
    print("  [PASS] Priority enum — all 4 levels defined")

def test_sample_story_has_ac():
    assert "acceptance_criteria" in SAMPLE_STORY
    assert len(SAMPLE_STORY["acceptance_criteria"]) > 20
    print("  [PASS] Sample story — has acceptance criteria for test generation")

if __name__ == "__main__":
    print("\n=== ado-test-case-generator: Sanity Tests ===\n")
    try:
        test_schema(); test_case_type_enum(); test_priority_enum(); test_sample_story_has_ac()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
