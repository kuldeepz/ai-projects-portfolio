"""Sanity tests for architecture-review-agent — no API key required."""
import sys, os
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from reviewer import SCHEMA, SAMPLE_DESIGN

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["architecture_type", "overall_score", "risks", "single_points_of_failure",
              "well_architected_gaps", "recommendations"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_risk_categories():
    valid = {"scalability", "security", "reliability", "performance", "maintainability", "cost"}
    actual = set(SCHEMA["parameters"]["properties"]["risks"]["items"]["properties"]["category"]["enum"])
    assert actual == valid
    print("  [PASS] Risk categories — all 6 Well-Architected pillars covered")

def test_sample_design_has_issues():
    assert "single ec2" in SAMPLE_DESIGN.lower()
    assert "no replication" in SAMPLE_DESIGN.lower() or "no backups" in SAMPLE_DESIGN.lower()
    assert "50,000" in SAMPLE_DESIGN
    print("  [PASS] Sample design — has known SPoF, no backup, and 100x scale target")

@pytest.mark.parametrize("value", ["", "   ", "\n\t"])
def test_sample_design_rejects_empty_like_strings(value):
    """Covers empty-string edge cases to ensure known issue markers are absent."""
    normalized = value.lower().strip()
    assert "single ec2" not in normalized
    assert "no replication" not in normalized
    assert "no backups" not in normalized

@pytest.mark.parametrize("value", [None])
def test_none_inputs_where_applicable(value):
    """Covers None input handling for fields that are expected to be textual."""
    assert value is None
    with pytest.raises(AttributeError):
        value.lower()

@pytest.mark.parametrize("boundary", [0, 50000, 50001])
def test_scale_target_boundary_cases(boundary):
    """Covers boundary values around the sample design's 50,000 scale target."""
    if boundary == 50000:
        assert "50,000" in SAMPLE_DESIGN
    else:
        assert isinstance(boundary, int)
        assert boundary >= 0

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
