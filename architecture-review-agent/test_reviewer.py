"""Sanity tests for architecture-review-agent — no API key required."""
import sys, os
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

if __name__ == "__main__":
    print("\n=== architecture-review-agent: Sanity Tests ===\n")
    try:
        test_schema(); test_risk_categories(); test_sample_design_has_issues()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
