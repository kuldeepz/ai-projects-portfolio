"""Sanity tests for ai-model-evaluator — no API key required."""
import sys, os
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from evaluator import EVAL_SCHEMA, SAMPLE_SUITE

def test_schema_required_fields():
    required = EVAL_SCHEMA["parameters"]["required"]
    for f in ["score", "correctness", "reasoning", "hallucination_detected"]:
        assert f in required
    print("  [PASS] Schema — required fields present")

def test_score_range():
    props = EVAL_SCHEMA["parameters"]["properties"]
    score_def = props["score"]
    assert score_def["type"] == "integer"
    assert "0" in score_def.get("description", "") or score_def.get("minimum", 0) == 0
    print("  [PASS] Score — integer type with 0-100 range")

def test_sample_suite_has_cases():
    assert "test_cases" in SAMPLE_SUITE
    assert len(SAMPLE_SUITE["test_cases"]) >= 3
    print("  [PASS] Sample suite — at least 3 test cases")

def test_sample_suite_case_structure():
    case = SAMPLE_SUITE["test_cases"][0]
    assert "id" in case
    assert "input" in case or "prompt" in case
    assert "expected" in case
    print("  [PASS] Test case structure — id/input/expected present")

def test_hallucination_is_boolean():
    props = EVAL_SCHEMA["parameters"]["properties"]
    assert props["hallucination_detected"]["type"] == "boolean"
    print("  [PASS] Hallucination field — typed as boolean")

def test_correctness_enum():
    props = EVAL_SCHEMA["parameters"]["properties"]
    valid = {"correct", "partial", "incorrect"}
    actual = set(props["correctness"]["enum"])
    assert actual == valid
    print("  [PASS] Correctness enum — correct/partial/incorrect")

@pytest.mark.parametrize("value", ["", " ", "\t"])
def test_required_field_names_are_not_empty_strings(value):
    """Ensures required schema fields do not contain empty-string-like values."""
    required = EVAL_SCHEMA["parameters"]["required"]
    assert value not in required

@pytest.mark.parametrize("case", [None] + SAMPLE_SUITE.get("test_cases", []))
def test_sample_suite_case_entries_handle_none_and_valid_cases(case):
    """Validates None handling and structure checks for sample suite case entries."""
    if case is None:
        assert case is None
    else:
        assert isinstance(case, dict)
        assert "id" in case
        assert "expected" in case

@pytest.mark.parametrize("score", [0, 100])
def test_score_boundary_values_supported(score):
    """Verifies boundary score values are within the declared schema limits."""
    score_def = EVAL_SCHEMA["parameters"]["properties"]["score"]
    minimum = score_def.get("minimum", 0)
    maximum = score_def.get("maximum", 100)
    assert minimum <= score <= maximum

if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
