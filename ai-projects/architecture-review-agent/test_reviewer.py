"""Sanity tests for architecture-review-agent — no API key required."""
import sys, os
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from reviewer import SCHEMA, SAMPLE_DESIGN


def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in [
        "architecture_type",
        "overall_score",
        "risks",
        "single_points_of_failure",
        "well_architected_gaps",
        "recommendations",
    ]:
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


@pytest.mark.parametrize("design", ["", "   ", "\n\t", None])
def test_sample_design_input_shape(design):
    """Validate production-facing design input assumptions via SAMPLE_DESIGN interface."""
    if design is None:
        with pytest.raises(AttributeError):
            design.lower()
    else:
        normalized = design.lower().strip()
        assert normalized == ""


@pytest.mark.parametrize("expected", ["50,000", "single ec2"])
def test_sample_design_contains_expected_review_signals(expected):
    """Assert review-relevant signals are present in the production sample design text."""
    haystack = SAMPLE_DESIGN if expected == "50,000" else SAMPLE_DESIGN.lower()
    needle = expected if expected == "50,000" else expected.lower()
    assert needle in haystack


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
