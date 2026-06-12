"""Sanity tests for sentiment-dashboard — no API key required."""
import os, sys, csv, tempfile
sys.path.insert(0, os.path.dirname(__file__))
from dashboard import SENTIMENT_SCHEMA, SENTIMENT_COLORS, SENTIMENT_ICONS, score_bar, save_batch_csv, process_batch_file


def test_sentiment_schema():
    assert SENTIMENT_SCHEMA["name"] == "sentiment_result"
    required = SENTIMENT_SCHEMA["parameters"]["required"]
    for field in ["sentiment", "score", "confidence", "emotions", "key_phrases", "summary"]:
        assert field in required
    enum = SENTIMENT_SCHEMA["parameters"]["properties"]["sentiment"]["enum"]
    assert set(enum) == {"positive", "negative", "neutral", "mixed"}
    print("  [PASS] Schema — required fields and sentiment enum valid")


def test_colors_and_icons():
    for s in ("positive", "negative", "neutral", "mixed"):
        assert s in SENTIMENT_COLORS
        assert s in SENTIMENT_ICONS
    print("  [PASS] Colors and icons — all 4 sentiments covered")


def test_score_bar_colors():
    pos = score_bar(0.8)
    neg = score_bar(-0.8)
    neutral = score_bar(0.0)
    assert "green" in pos
    assert "red" in neg
    assert "blue" in neutral
    print("  [PASS] Score bar — correct colors for positive/negative/neutral")


def test_save_batch_csv():
    results = [
        {"sentiment": "positive", "score": 0.9, "confidence": 95,
         "emotions": [{"emotion": "joy", "intensity": "high"}], "summary": "Very happy."},
        {"sentiment": "negative", "score": -0.6, "confidence": 80,
         "emotions": [{"emotion": "frustration", "intensity": "medium"}], "summary": "Quite unhappy."}
    ]
    labels = ["Review 1", "Review 2"]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
        tmp = f.name
    try:
        save_batch_csv(results, labels, tmp)
        with open(tmp) as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2
        assert rows[0]["sentiment"] == "positive"
        assert rows[1]["sentiment"] == "negative"
        print("  [PASS] Save batch CSV — 2 rows written correctly")
    finally:
        os.unlink(tmp)


def test_process_batch_file():
    rows = [["text", "label"], ["Great product!", "rev1"], ["Terrible service", "rev2"]]
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
        tmp = f.name
    try:
        texts, labels = process_batch_file(tmp)
        assert texts == ["Great product!", "Terrible service"]
        assert labels == ["rev1", "rev2"]
        print("  [PASS] Process batch file — texts and labels parsed correctly")
    finally:
        os.unlink(tmp)


if __name__ == "__main__":
    print("\n=== sentiment-dashboard: Sanity Tests ===\n")
    try:
        test_sentiment_schema()
        test_colors_and_icons()
        test_score_bar_colors()
        test_save_batch_csv()
        test_process_batch_file()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
