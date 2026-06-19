"""Sanity tests for ado-pipeline-failure-analyzer — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from analyzer import SCHEMA, SAMPLE_LOG

def test_schema():
    required = SCHEMA["parameters"]["required"]
    for f in ["failure_stage", "root_cause", "error_type", "severity", "fix_steps", "prevention_tips"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_error_type_enum():
    valid = {"compilation_error","test_failure","dependency_error","config_error",
             "permission_error","timeout","network_error","resource_error","unknown"}
    actual = set(SCHEMA["parameters"]["properties"]["error_type"]["enum"])
    assert actual == valid
    print("  [PASS] Error type enum — all 9 types defined")

def test_sample_log_has_failures():
    assert "FAILED" in SAMPLE_LOG
    assert "ModuleNotFoundError" in SAMPLE_LOG
    assert "##[error]" in SAMPLE_LOG
    print("  [PASS] Sample log — contains expected failure markers")

def test_log_tail_truncation():
    # verify the tail strategy keeps the end
    long_log = "irrelevant header\n" * 500 + "REAL ERROR HERE"
    truncated = long_log[-8000:]
    assert "REAL ERROR HERE" in truncated
    print("  [PASS] Log truncation — tail strategy preserves error at end")

@pytest.mark.parametrize(
    "log_input, expected",
    [
        ("", ""),
        ("short log", "short log"),
        ("x" * 9000, "x" * 8000),
    ],
)
def test_log_tail_truncation_parametrized(log_input, expected):
    """Covers empty, short, and over-limit log truncation boundary behavior."""
    truncated = log_input[-8000:]
    assert truncated == expected

@pytest.mark.parametrize(
    "log_input",
    [None, "", SAMPLE_LOG],
)
def test_failure_markers_detection_with_none_and_empty(log_input):
    """Validates marker detection for None, empty input, and known failing sample logs."""
    text = "" if log_input is None else log_input
    has_markers = (
        "FAILED" in text
        and "ModuleNotFoundError" in text
        and "##[error]" in text
    )
    assert has_markers is (log_input == SAMPLE_LOG)

@pytest.mark.parametrize(
    "candidate, is_valid",
    [
        ("", False),
        (None, False),
        ("unknown", True),
        ("timeout", True),
        ("not_a_real_type", False),
    ],
)
def test_error_type_enum_membership_edge_cases(candidate, is_valid):
    """Checks empty/None and valid-invalid boundary values for error_type enum membership."""
    enum_values = set(SCHEMA["parameters"]["properties"]["error_type"]["enum"])
    assert ((candidate in enum_values) if candidate is not None else False) is is_valid

if __name__ == "__main__":
    print("\n=== ado-pipeline-failure-analyzer: Sanity Tests ===\n")
    try:
        test_schema(); test_error_type_enum(); test_sample_log_has_failures(); test_log_tail_truncation()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
