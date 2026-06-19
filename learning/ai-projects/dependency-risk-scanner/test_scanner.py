"""Sanity tests for dependency-risk-scanner — no API key required."""
import sys, os, tempfile
import pytest

sys.path.insert(0, os.path.dirname(__file__))
from scanner import SCHEMA, RISK_COLORS, RISK_ICONS, parse_requirements

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["ecosystem", "total_packages", "risk_summary", "packages", "critical_action_required"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_risk_levels_covered():
    levels = {"critical", "high", "medium", "low", "ok"}
    assert set(RISK_COLORS.keys()) == levels
    assert set(RISK_ICONS.keys()) == levels
    print("  [PASS] Risk levels — all 5 levels have colors and icons")

def test_parse_requirements():
    content = "flask==2.3.0\nrequests>=2.28.0\npytest"
    result = parse_requirements(content, "requirements.txt")
    assert "requirements.txt" in result
    assert "flask==2.3.0" in result
    print("  [PASS] Parse requirements — filename and content preserved")

def test_real_requirements_file():
    # Test against one of our own project requirements.txt files
    req_path = os.path.join(os.path.dirname(__file__), "..", "pdf-chatbot-rag", "requirements.txt")
    if os.path.exists(req_path):
        content = open(req_path).read()
        result = parse_requirements(content, "requirements.txt")
        assert "openai" in result
        print("  [PASS] Real requirements.txt — parsed successfully")
    else:
        print("  [SKIP] Real requirements.txt not found")

@pytest.mark.parametrize(
    "content, filename",
    [
        ("", "requirements.txt"),
        ("", ""),
        ("", "reqs.in"),
    ],
)
def test_parse_requirements_empty_string_inputs(content, filename):
    """Covers empty string content and filename parsing scenarios."""
    result = parse_requirements(content, filename)
    assert isinstance(result, str)
    if filename:
        assert filename in result

@pytest.mark.parametrize(
    "content, filename",
    [
        (None, "requirements.txt"),
        ("flask==2.3.0", None),
        (None, None),
    ],
)
def test_parse_requirements_none_inputs_where_applicable(content, filename):
    """Covers None inputs and validates graceful handling or explicit errors."""
    try:
        result = parse_requirements(content, filename)
        assert isinstance(result, str)
    except TypeError:
        assert True
    except AttributeError:
        assert True

@pytest.mark.parametrize(
    "content, filename, expected_snippet",
    [
        ("\n\n", "requirements.txt", "requirements.txt"),
        ("# only comments\n# another", "requirements.txt", "requirements.txt"),
        ("numpy==1.26.4\n", "requirements.txt", "numpy==1.26.4"),
    ],
)
def test_parse_requirements_boundary_edge_cases(content, filename, expected_snippet):
    """Covers boundary requirement-file shapes like blanks, comments, and trailing newlines."""
    result = parse_requirements(content, filename)
    assert isinstance(result, str)
    assert expected_snippet in result

if __name__ == "__main__":
    print("\n=== dependency-risk-scanner: Sanity Tests ===\n")
    try:
        test_schema(); test_risk_levels_covered(); test_parse_requirements(); test_real_requirements_file()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
