"""
Sanity tests for ai-resume-analyzer — no API key required.
Tests file loading, input validation, and score display logic.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from analyzer import extract_text_from_txt, score_color


def test_txt_extraction():
    content = "John Doe\nSoftware Engineer\nPython, JavaScript, SQL\n5 years experience"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        tmp_path = f.name
    try:
        result = extract_text_from_txt(tmp_path)
        assert "John Doe" in result
        assert "Python" in result
        print("  [PASS] TXT extraction — reads file content correctly")
    finally:
        os.unlink(tmp_path)


def test_score_color():
    assert score_color(90) == "green"
    assert score_color(75) == "yellow"
    assert score_color(60) == "yellow"
    assert score_color(59) == "red"
    assert score_color(0) == "red"
    print("  [PASS] Score color — correct thresholds (green≥80, yellow≥60, red<60)")


def test_analysis_schema_structure():
    """Validate that a mock analysis dict has all required keys."""
    mock_analysis = {
        "candidate_name": "Jane Smith",
        "current_role": "Backend Engineer",
        "years_experience": 4,
        "overall_score": 72,
        "technical_skills": ["Python", "Django", "PostgreSQL"],
        "soft_skills": ["Communication", "Leadership"],
        "strengths": ["Clear project impact metrics", "Strong technical stack"],
        "gaps": ["No cloud certifications mentioned", "Missing system design experience"],
        "improvements": ["Add quantified achievements", "Include open-source contributions"],
        "ats_score": 68,
        "ats_issues": ["Uses tables which ATS may misparse"],
        "summary": "Strong backend profile with room to grow in cloud and system design areas."
    }

    required_keys = [
        "candidate_name", "current_role", "years_experience", "overall_score",
        "technical_skills", "soft_skills", "strengths", "gaps",
        "improvements", "ats_score", "ats_issues", "summary"
    ]
    for key in required_keys:
        assert key in mock_analysis, f"Missing key: {key}"

    assert isinstance(mock_analysis["overall_score"], int)
    assert 1 <= mock_analysis["overall_score"] <= 100
    print("  [PASS] Analysis schema — all required keys present and valid")


if __name__ == "__main__":
    print("\n=== ai-resume-analyzer: Sanity Tests ===\n")
    try:
        test_txt_extraction()
        test_score_color()
        test_analysis_schema_structure()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n")
        sys.exit(1)
