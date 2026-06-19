"""Sanity tests for ado-workitem-analyzer — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from analyzer import SCHEMA, SAMPLE_WORK_ITEM, estimate_story_points, readiness_score

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["ready_score", "missing_fields", "improved_acceptance_criteria",
              "story_point_suggestion", "risks", "suggestions"]:
        assert f in required
    print("  [PASS] Schema — all required fields present")

def test_fibonacci_enum():
    # story point suggestion should be fibonacci via analyzer behavior
    valid_sp = {1, 2, 3, 5, 8, 13, 21}
    assert estimate_story_points(SAMPLE_WORK_ITEM) in valid_sp
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
    """Covers empty-string and whitespace edge cases through analyzer scoring behavior."""
    item = dict(SAMPLE_WORK_ITEM)
    item["story_points"] = 3
    item["acceptance_criteria"] = "Given valid credentials, when user logs in, then dashboard is shown."
    item["assigned_to"] = input_value

    score, _issues, missing = readiness_score(item)

    assert ("assigned_to" in missing) is expected_missing
    assert score >= 0

@pytest.mark.parametrize(
    "story_points,expected_missing",
    [
        (None, True),
        (1, False),
        (0, False),
    ],
)
def test_story_points_none_and_boundary_inputs(story_points, expected_missing):
    """Covers None and boundary numeric inputs via analyzer missing-field detection."""
    item = dict(SAMPLE_WORK_ITEM)
    item["assigned_to"] = "Some assignee"
    item["acceptance_criteria"] = "Given valid credentials, when user logs in, then dashboard is shown."
    item["story_points"] = story_points

    score, _issues, missing = readiness_score(item)

    assert ("story_points" in missing) is expected_missing
    assert score >= 0

@pytest.mark.parametrize(
    "title,description,acceptance_criteria,is_valid",
    [
        ("A", "B", "C", True),
        ("A" * 200, "B" * 1000, "Given/When/Then with more detail", True),
        ("", "", "", False),
    ],
)
def test_fibonacci_story_point_boundary_values(title, description, acceptance_criteria, is_valid):
    """Validates story point suggestion comes from analyzer and is Fibonacci."""
    item = dict(SAMPLE_WORK_ITEM)
    item["title"] = title
    item["description"] = description
    item["acceptance_criteria"] = acceptance_criteria

    sp_value = estimate_story_points(item)
    valid_sp = {1, 2, 3, 5, 8, 13, 21}

    assert (sp_value in valid_sp) is is_valid

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
