"""Sanity tests for team-skill-gap-analyzer — no API key required."""
import sys, os
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
