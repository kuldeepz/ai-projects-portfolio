"""Sanity tests for document-comparison-agent — no API key required."""
import os, sys, tempfile
import pytest
sys.path.insert(0, os.path.dirname(__file__))
from compare import read_document, COMPARE_SCHEMA, similarity_bar


def test_read_txt():
    content = "This is a sample document.\nIt has two lines."
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content); tmp = f.name
    try:
        result = read_document(tmp)
        assert "sample document" in result
        print("  [PASS] Read TXT — text extracted correctly")
    finally:
        os.unlink(tmp)


def test_similarity_bar_colors():
    high = similarity_bar(85)
    mid = similarity_bar(55)
    low = similarity_bar(20)
    assert "green" in high
    assert "yellow" in mid
    assert "red" in low
    print("  [PASS] Similarity bar — correct colors for high/mid/low scores")


def test_schema_structure():
    assert COMPARE_SCHEMA["name"] == "comparison_report"
    required = COMPARE_SCHEMA["parameters"]["required"]
    for field in ["doc1_summary", "doc2_summary", "overall_similarity", "common_themes",
                  "unique_to_doc1", "unique_to_doc2", "conflicts", "recommendation"]:
        assert field in required, f"Missing: {field}"
    print("  [PASS] Schema — all required fields present")


def test_mock_report():
    mock = {
        "doc1_summary": "Original contract from 2022.",
        "doc2_summary": "Revised contract from 2024.",
        "overall_similarity": 72,
        "common_themes": ["Intellectual property", "Payment terms"],
        "unique_to_doc1": ["30-day notice clause"],
        "unique_to_doc2": ["Remote work provisions", "Updated liability cap"],
        "conflicts": [{"topic": "Termination", "doc1_position": "60-day notice", "doc2_position": "30-day notice"}],
        "tone_comparison": "Doc 1 is more formal; Doc 2 uses plain language.",
        "recommendation": "Use Doc 2 for new agreements; it includes modern provisions."
    }
    assert 0 <= mock["overall_similarity"] <= 100
    assert len(mock["conflicts"]) == 1
    assert all(k in mock["conflicts"][0] for k in ("topic", "doc1_position", "doc2_position"))
    print("  [PASS] Mock report — structure valid")


@pytest.mark.parametrize("content", ["", "   ", "\n\n"])
def test_read_txt_empty_content_parametrized(content):
    """Covers reading text files with empty or whitespace-only content."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(content)
        tmp = f.name
    try:
        result = read_document(tmp)
        assert isinstance(result, str)
        assert result.strip() == ""
    finally:
        os.unlink(tmp)


@pytest.mark.parametrize("path_value", [None, "", "   "])
def test_read_document_none_or_blank_path(path_value):
    """Covers invalid None/blank path inputs for document reading."""
    with pytest.raises((TypeError, ValueError, FileNotFoundError, OSError)):
        read_document(path_value)


@pytest.mark.parametrize(
    "score, expected_color",
    [
        (0, "red"),
        (50, "yellow"),
        (100, "green"),
        (-1, "red"),
        (101, "green"),
    ],
)
def test_similarity_bar_boundary_scores(score, expected_color):
    """Covers boundary and out-of-range similarity scores for color mapping."""
    bar = similarity_bar(score)
    assert expected_color in bar


if __name__ == "__main__":
    print("\n=== document-comparison-agent: Sanity Tests ===\n")
    try:
        test_read_txt()
        test_similarity_bar_colors()
        test_schema_structure()
        test_mock_report()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n"); sys.exit(1)
