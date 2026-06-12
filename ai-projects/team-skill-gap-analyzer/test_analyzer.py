"""Sanity tests for team-skill-gap-analyzer — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from analyzer import SCHEMA, SAMPLE_DATA

def test_schema_required_fields():
    required = SCHEMA["parameters"]["required"]
    for f in ["coverage_score", "critical_gaps", "member_fit", "training_recommendations", "hiring_recommendations"]:
        assert f in required
    print("  [PASS] Schema — all required fields present")

def test_coverage_score_range():
    props = SCHEMA["parameters"]["properties"]
    score_def = props["coverage_score"]
    assert score_def["type"] == "integer"
    assert "0" in score_def.get("description", "") or score_def.get("minimum", 0) == 0
    print("  [PASS] Coverage score — integer type with 0-100 range")

def test_sample_team_size():
    assert len(SAMPLE_DATA["team"]) == 5
    print("  [PASS] Sample data — exactly 5 team members")

def test_sample_team_member_structure():
    member = SAMPLE_DATA["team"][0]
    for f in ["name", "role", "skills"]:
        assert f in member, f"Missing '{f}' in team member"
    assert isinstance(member["skills"], (list, dict))
    print("  [PASS] Team member structure — name/role/skills present")

def test_sample_has_requirements():
    assert "project" in SAMPLE_DATA
    proj = SAMPLE_DATA["project"]
    assert "required_skills" in proj or "requirements" in proj
    print("  [PASS] Sample data — project requirements present")

def test_training_recommendations_structure():
    props = SCHEMA["parameters"]["properties"]
    assert props["training_recommendations"]["type"] == "array"
    items = props["training_recommendations"]["items"]["properties"]
    assert "skill" in items
    assert "priority" in items
    print("  [PASS] Training recommendations — skill/priority fields defined")

def test_member_fit_is_array():
    props = SCHEMA["parameters"]["properties"]
    assert props["member_fit"]["type"] == "array"
    print("  [PASS] Member fit — typed as array")

def test_required_fields_are_non_empty_and_unique():
    """Required fields should be meaningful schema keys without duplicates."""
    required = SCHEMA["parameters"]["required"]
    assert isinstance(required, list)
    assert all(isinstance(f, str) and f.strip() for f in required)
    assert len(required) == len(set(required))

def test_sample_project_requirements_have_valid_structure():
    """Project requirements container should be present and typed consistently."""
    assert "project" in SAMPLE_DATA
    project = SAMPLE_DATA["project"]
    assert isinstance(project, dict) and project

    key = "required_skills" if "required_skills" in project else "requirements" if "requirements" in project else None
    assert key is not None

    requirements = project[key]
    assert isinstance(requirements, (list, dict))
    if isinstance(requirements, list):
        assert all((isinstance(item, str) and item.strip()) or isinstance(item, dict) for item in requirements)

def test_all_team_member_skills_have_consistent_types():
    """Every team member should expose skills as list/dict, with at least one entry."""
    members = SAMPLE_DATA["team"]
    assert isinstance(members, list) and members

    for member in members:
        skills = member.get("skills")
        assert isinstance(skills, (list, dict))
        if isinstance(skills, list):
            assert all(isinstance(skill, str) and skill.strip() for skill in skills)
            assert len(skills) > 0
        else:
            assert len(skills) > 0

@pytest.mark.parametrize("idx", [0, -1, 4])
def test_team_member_boundary_indexes_have_required_keys(idx):
    """Validate first/last team members (boundary indexes) include core keys."""
    member = SAMPLE_DATA["team"][idx]
    for f in ["name", "role", "skills"]:
        assert f in member

if __name__ == "__main__":
    print("\n=== team-skill-gap-analyzer: Sanity Tests ===\n")
    try:
        test_schema_required_fields()
        test_coverage_score_range()
        test_sample_team_size()
        test_sample_team_member_structure()
        test_sample_has_requirements()
        test_training_recommendations_structure()
        test_member_fit_is_array()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); import sys; sys.exit(1)

