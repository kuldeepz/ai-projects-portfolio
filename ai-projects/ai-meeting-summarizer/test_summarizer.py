"""Sanity tests for ai-meeting-summarizer — no API key required."""
import os, sys, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from summarizer import NOTES_SCHEMA, save_notes


def test_schema_structure():
    fn = NOTES_SCHEMA
    assert fn["name"] == "meeting_notes"
    required = fn["parameters"]["required"]
    for field in ["title", "attendees", "executive_summary", "key_topics", "decisions", "action_items", "blockers", "sentiment"]:
        assert field in required, f"Missing: {field}"
    print("  [PASS] Schema — all required fields present")


def test_save_notes():
    mock_notes = {
        "title": "Q3 Sprint Planning",
        "attendees": ["Alice", "Bob"],
        "executive_summary": "Team planned the Q3 sprint with 12 story points.",
        "key_topics": [{"topic": "Backlog refinement", "discussion": "Reviewed 15 tickets."}],
        "decisions": ["Use feature flags for rollout"],
        "action_items": [{"task": "Set up CI/CD pipeline", "owner": "Bob", "due": "2024-07-15"}],
        "blockers": ["Waiting on infra access"],
        "follow_up_meetings": ["Demo next Friday"],
        "sentiment": "positive",
        "duration_estimate": "45 minutes"
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        tmp = f.name
    try:
        save_notes(mock_notes, tmp)
        with open(tmp) as f:
            content = f.read()
        assert "Q3 Sprint Planning" in content
        assert "Bob" in content
        assert "| Set up CI/CD pipeline |" in content
        print("  [PASS] Save notes — markdown file written correctly")
    finally:
        os.unlink(tmp)


def test_sentiment_values():
    valid = {"positive", "neutral", "tense", "mixed"}
    props = NOTES_SCHEMA["parameters"]["properties"]
    enum_vals = set(props["sentiment"]["enum"])
    assert enum_vals == valid, f"Unexpected enum: {enum_vals}"
    print("  [PASS] Sentiment enum — all four values valid")


if __name__ == "__main__":
    print("\n=== ai-meeting-summarizer: Sanity Tests ===\n")
    try:
        test_schema_structure()
        test_save_notes()
        test_sentiment_values()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
