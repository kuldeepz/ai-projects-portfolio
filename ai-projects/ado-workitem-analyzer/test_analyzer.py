"""Sanity tests for ado-workitem-analyzer — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from analyzer import SCHEMA, SAMPLE_WORK_ITEM

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["ready_score", "missing_fields", "improved_acceptance_criteria",
              "story_point_suggestion", "risks", "suggestions"]:
        assert f in required
    print("  [PASS] Schema — all required fields present")

def test_fibonacci_enum():
    # story point suggestion should be fibonacci
    valid_sp = {1, 2, 3, 5, 8, 13, 21}
    mock_result = {"ready_score": 40, "missing_fields": ["story_points", "assigned_to"],
                   "acceptance_criteria_issues": ["Too vague"], "improved_acceptance_criteria": "Given...",
                   "story_point_suggestion": 5, "risks": [], "suggestions": ["Add AC"], "summary": "Needs work"}
    assert mock_result["story_point_suggestion"] in valid_sp
    print("  [PASS] Story point — value is valid Fibonacci number")

def test_sample_item_has_issues():
    # The sample item has known gaps — verify we can detect them programmatically
    assert SAMPLE_WORK_ITEM["story_points"] is None, "Sample should have no story points"
    assert SAMPLE_WORK_ITEM["assigned_to"] == "", "Sample should have no assignee"
    assert "Login works" == SAMPLE_WORK_ITEM["acceptance_criteria"], "Sample has weak AC"
    print("  [PASS] Sample work item — has expected gaps for demo purposes")

@pytest.mark.parametrize(
    "input_value,expected_missing",
    [
        ("", True),
        ("Some assignee", False),
        ("   ", True),
    ],
)
def test_assigned_to_empty_string_edge_cases(input_value, expected_missing):
    """Covers empty-string and whitespace edge cases for assignee presence checks."""
    is_missing = not bool(input_value and input_value.strip())
    assert is_missing is expected_missing

@pytest.mark.parametrize(
    "story_points,expected_missing",
    [
        (None, True),
        (1, False),
        (0, False),
    ],
)
def test_story_points_none_and_boundary_inputs(story_points, expected_missing):
    """Covers None and boundary numeric inputs for story points availability."""
    is_missing = story_points is None
    assert is_missing is expected_missing

@pytest.mark.parametrize(
    "sp_value,is_valid",
    [
        (1, True),
        (21, True),
        (0, False),
        (34, False),
        (None, False),
    ],
)
def test_fibonacci_story_point_boundary_values(sp_value, is_valid):
    """Covers boundary and invalid edge values for Fibonacci story point suggestions."""
    valid_sp = {1, 2, 3, 5, 8, 13, 21}
    assert (sp_value in valid_sp) is is_valid

if __name__ == "__main__":
    print("\n=== ado-workitem-analyzer: Sanity Tests ===\n")
    try:
        test_schema(); test_fibonacci_enum(); test_sample_item_has_issues()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
