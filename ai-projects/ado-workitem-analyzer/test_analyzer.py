"""Sanity tests for ado-workitem-analyzer — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from analyzer import SCHEMA, SAMPLE_WORK_ITEM, analyze_work_item

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["ready_score", "missing_fields", "improved_acceptance_criteria",
              "story_point_suggestion", "risks", "suggestions"]:
        assert f in required
    print("  [PASS] Schema — all required fields present")

def test_fibonacci_enum():
    # story point suggestion should be fibonacci
    valid_sp = {1, 2, 3, 5, 8, 13, 21}
    result = analyze_work_item(SAMPLE_WORK_ITEM)
    assert result["story_point_suggestion"] in valid_sp
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
    """Covers empty-string and whitespace edge cases via analyzer behavior."""
    item = {**SAMPLE_WORK_ITEM, "assigned_to": input_value}
    result = analyze_work_item(item)
    assert ("assigned_to" in result["missing_fields"]) is expected_missing

@pytest.mark.parametrize(
    "story_points,expected_missing",
    [
        (None, True),
        (1, False),
        (0, False),
    ],
)
def test_story_points_none_and_boundary_inputs(story_points, expected_missing):
    """Covers None and boundary numeric inputs via analyzer behavior."""
    item = {**SAMPLE_WORK_ITEM, "story_points": story_points, "assigned_to": "owner"}
    result = analyze_work_item(item)
    assert ("story_points" in result["missing_fields"]) is expected_missing

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
    """Covers boundary and invalid edge values through analyzer outputs."""
    item = {**SAMPLE_WORK_ITEM, "story_points": sp_value, "assigned_to": "owner"}
    result = analyze_work_item(item)
    valid_sp = {1, 2, 3, 5, 8, 13, 21}
    assert (result["story_point_suggestion"] in valid_sp) is is_valid

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
