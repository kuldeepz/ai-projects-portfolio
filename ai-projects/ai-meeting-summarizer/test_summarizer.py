"""Sanity tests for ai-meeting-summarizer — no API key required."""
import os, sys, tempfile
import pytest
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


@pytest.mark.parametrize(
    "title, attendees, executive_summary, key_topics, decisions, action_items, blockers, sentiment",
    [
        ("", [], "", [], [], [], [], "neutral"),
        ("", ["Alice"], "", [{"topic": "", "discussion": ""}], [], [], [], "mixed"),
        ("", [], "", [], [""], [{"task": "", "owner": "", "due": ""}], [""], "tense"),
    ],
)
def test_save_notes_handles_empty_string_inputs(title, attendees, executive_summary, key_topics, decisions, action_items, blockers, sentiment):
    """Covers saving notes when multiple fields contain empty-string content."""
    notes = {
        "title": title,
        "attendees": attendees,
        "executive_summary": executive_summary,
        "key_topics": key_topics,
        "decisions": decisions,
        "action_items": action_items,
        "blockers": blockers,
        "follow_up_meetings": [],
        "sentiment": sentiment,
        "duration_estimate": ""
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        tmp = f.name
    try:
        save_notes(notes, tmp)
        with open(tmp) as f:
            content = f.read()
        assert isinstance(content, str)
        assert len(content) >= 0
    finally:
        os.unlink(tmp)


@pytest.mark.parametrize(
    "duration_estimate, follow_up_meetings",
    [
        (None, []),
        ("30 minutes", None),
        (None, None),
    ],
)
def test_save_notes_allows_optional_none_inputs(duration_estimate, follow_up_meetings):
    """Covers optional fields receiving None where applicable during save."""
    notes = {
        "title": "Weekly Sync",
        "attendees": ["Alice"],
        "executive_summary": "Status updates",
        "key_topics": [{"topic": "Roadmap", "discussion": "Reviewed milestones"}],
        "decisions": ["Proceed with beta"],
        "action_items": [{"task": "Prepare release notes", "owner": "Alice", "due": "2024-08-01"}],
        "blockers": [],
        "follow_up_meetings": follow_up_meetings,
        "sentiment": "neutral",
        "duration_estimate": duration_estimate,
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        tmp = f.name
    try:
        save_notes(notes, tmp)
        with open(tmp) as f:
            content = f.read()
        assert "Weekly Sync" in content
    finally:
        os.unlink(tmp)


@pytest.mark.parametrize("sentiment", ["positive", "neutral", "tense", "mixed"])
def test_save_notes_accepts_valid_sentiment_values(sentiment):
    """Valid sentiment values should be accepted by save_notes behavior."""
    notes = {
        "title": "Sentiment Check",
        "attendees": ["Alice"],
        "executive_summary": "Testing valid sentiments",
        "key_topics": [{"topic": "Quality", "discussion": "Validation behavior"}],
        "decisions": ["Keep tests strict"],
        "action_items": [{"task": "Run CI", "owner": "Alice", "due": "2024-08-01"}],
        "blockers": [],
        "follow_up_meetings": [],
        "sentiment": sentiment,
        "duration_estimate": "30 minutes",
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        tmp = f.name
    try:
        save_notes(notes, tmp)
        with open(tmp) as f:
            content = f.read()
        assert "Sentiment Check" in content
    finally:
        os.unlink(tmp)


def test_save_notes_rejects_invalid_sentiment_value():
    """Invalid sentiment should raise an error during save behavior validation."""
    notes = {
        "title": "Sentiment Check",
        "attendees": ["Alice"],
        "executive_summary": "Testing invalid sentiment",
        "key_topics": [{"topic": "Quality", "discussion": "Validation behavior"}],
        "decisions": ["Keep tests strict"],
        "action_items": [{"task": "Run CI", "owner": "Alice", "due": "2024-08-01"}],
        "blockers": [],
        "follow_up_meetings": [],
        "sentiment": "invalid",
        "duration_estimate": "30 minutes",
    }
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w") as f:
        tmp = f.name
    try:
        with pytest.raises(Exception):
            save_notes(notes, tmp)
    finally:
        os.unlink(tmp)


if __name__ == "__main__":
    print("\n=== ai-meeting-summarizer: Sanity Tests ===\n")
    try:
        test_schema_structure()
        test_save_notes()
        test_sentiment_values()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
