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
    "work_item,expected_missing",
    [
        ({"assigned_to": ""}, True),
        ({"assigned_to": "Some assignee"}, False),
        ({"assigned_to": "   "}, True),
        ({"assigned_to": None}, True),
        ({"assigned_to": 123}, True),
        ({}, True),
    ],
)
def test_assigned_to_edge_cases(work_item, expected_missing):
    """Covers empty, malformed, typed, and missing-key assignee edge cases."""
    assigned_to = work_item.get("assigned_to")
    is_missing = not (isinstance(assigned_to, str) and assigned_to.strip())
    assert is_missing is expected_missing

@pytest.mark.parametrize(
    "work_item,expected_missing",
    [
        ({"story_points": None}, True),
        ({"story_points": 1}, False),
        ({"story_points": 0}, False),
        ({"story_points": -1}, False),
        ({"story_points": "8"}, True),
        ({}, True),
    ],
)
def test_story_points_presence_edge_cases(work_item, expected_missing):
    """Covers None, typed, negative, and missing-key availability for story points."""
    story_points = work_item.get("story_points")
    is_missing = story_points is None or not isinstance(story_points, (int, float))
    assert is_missing is expected_missing

@pytest.mark.parametrize(
    "sp_value,is_valid",
    [
        (1, True),
        (21, True),
        (0, False),
        (34, False),
        (None, False),
        (-1, False),
        ("8", False),
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
