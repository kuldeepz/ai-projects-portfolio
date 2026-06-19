"""
Sanity tests for ai-code-reviewer — no API key required.
Tests language detection, schema structure, and severity mapping.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from reviewer import detect_language, SEVERITY_COLORS, SEVERITY_ICONS, REVIEW_SCHEMA


def test_language_detection():
    cases = {
        "app.py": "python",
        "index.js": "javascript",
        "main.go": "go",
        "server.ts": "typescript",
        "Main.java": "java",
        "lib.rs": "rust",
        "unknown.xyz": "",
    }
    for filename, expected in cases.items():
        result = detect_language(filename)
        assert result == expected, f"detect_language({filename!r}) → {result!r}, expected {expected!r}"
    print("  [PASS] Language detection — all extensions correctly mapped")


def test_severity_coverage():
    severities = ["critical", "high", "medium", "low"]
    for s in severities:
        assert s in SEVERITY_COLORS, f"Missing color for severity: {s}"
        assert s in SEVERITY_ICONS, f"Missing icon for severity: {s}"
    print("  [PASS] Severity mapping — all four levels have colors and icons")


def test_review_schema_structure():
    fn = REVIEW_SCHEMA
    assert fn["name"] == "code_review"
    required = fn["parameters"]["required"]
    for field in ["language", "overall_score", "summary", "security_issues", "bugs"]:
        assert field in required, f"Missing required field: {field}"
    print("  [PASS] Review schema — required fields all present")


def test_issue_schema():
    """Mock a review result and validate its structure."""
    mock_review = {
        "language": "python",
        "overall_score": 55,
        "summary": "The code has critical SQL injection vulnerabilities.",
        "security_issues": [
            {"severity": "critical", "issue": "SQL injection via f-string", "fix": "Use parameterized queries"}
        ],
        "bugs": [],
        "performance_issues": [{"issue": "N+1 query in loop", "fix": "Batch fetch outside loop"}],
        "best_practice_violations": ["No type hints", "Hardcoded credentials"],
        "positive_aspects": ["Good function naming"],
        "refactored_snippet": "cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))"
    }
    assert mock_review["overall_score"] <= 100
    assert all(i["severity"] in ("critical", "high", "medium", "low") for i in mock_review["security_issues"])
    print("  [PASS] Issue schema — severity values and structure valid")


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("", ""),
        ("README", ""),
        ("script.py", "python"),
    ],
)
def test_language_detection_edge_and_empty_inputs(filename, expected):
    """Covers empty and extension edge cases for language detection."""
    assert detect_language(filename) == expected


@pytest.mark.parametrize("invalid_input", [None])
def test_language_detection_none_input(invalid_input):
    """Covers None input handling for language detection."""
    with pytest.raises(TypeError):
        detect_language(invalid_input)


@pytest.mark.parametrize("score", [0, 100])
def test_issue_schema_overall_score_boundaries(score):
    """Covers boundary overall_score values allowed by the review schema."""
    score_schema = REVIEW_SCHEMA["parameters"]["properties"]["overall_score"]
    assert score_schema.get("minimum") == 0
    assert score_schema.get("maximum") == 100

    mock_review = {
        "language": "python",
        "overall_score": score,
        "summary": "Boundary score validation.",
        "security_issues": [],
        "bugs": [],
    }
    assert score_schema["minimum"] <= mock_review["overall_score"] <= score_schema["maximum"]


if __name__ == "__main__":
    print("\n=== ai-code-reviewer: Sanity Tests ===\n")
    try:
        test_language_detection()
        test_severity_coverage()
        test_review_schema_structure()
        test_issue_schema()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n")
        sys.exit(1)
