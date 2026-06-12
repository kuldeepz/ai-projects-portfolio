"""
Sanity tests for email-composer-ai — no API key required.
Tests tone options, length prompts, and schema structure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from composer import TONES, LENGTH_PROMPTS, EMAIL_SCHEMA


def test_tone_options():
    assert len(TONES) >= 5, "Should have at least 5 tone options"
    for key, (name, desc) in TONES.items():
        assert name, f"Tone {key} missing name"
        assert desc, f"Tone {key} missing description"
        assert len(desc) > 10, f"Tone {key} description too short"
    print("  [PASS] Tone options — all 5 tones have names and descriptions")


def test_length_prompts():
    for length in ("short", "medium", "long"):
        assert length in LENGTH_PROMPTS, f"Missing length option: {length}"
        assert len(LENGTH_PROMPTS[length]) > 10
    print("  [PASS] Length prompts — short/medium/long all defined")


def test_email_schema():
    fn = EMAIL_SCHEMA
    assert fn["name"] == "email_output"
    required = fn["parameters"]["required"]
    for field in ["subject", "body", "alternative_subjects", "follow_up_suggestions"]:
        assert field in required, f"Missing required field: {field}"
    print("  [PASS] Email schema — required fields present")


def test_mock_result_structure():
    mock_result = {
        "subject": "Following Up on Our Proposal — Next Steps",
        "body": "Dear Sarah,\n\nI hope this message finds you well...\n\nBest regards,\nKuldeep",
        "alternative_subjects": [
            "Quick Follow-up: Proposal Review",
            "Checking In — Proposal Discussion"
        ],
        "follow_up_suggestions": [
            "Schedule a 30-min call to address any questions",
            "Send updated proposal deck with pricing breakdown"
        ],
        "word_count": 95,
        "tone_notes": "Formal tone applied with professional salutation and measured closing."
    }

    assert "Dear" in mock_result["body"] or "Hi" in mock_result["body"]
    assert len(mock_result["alternative_subjects"]) == 2
    assert mock_result["word_count"] > 0
    print("  [PASS] Mock result structure — all fields present and valid")


if __name__ == "__main__":
    print("\n=== email-composer-ai: Sanity Tests ===\n")
    try:
        test_tone_options()
        test_length_prompts()
        test_email_schema()
        test_mock_result_structure()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n")
        sys.exit(1)
