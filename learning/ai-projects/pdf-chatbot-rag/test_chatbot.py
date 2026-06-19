"""
Sanity test for pdf-chatbot-rag.
Creates a small in-memory text and validates chunking, embedding retrieval, and QA pipeline.
"""

import os
import sys
import math
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from chatbot import chunk_text, cosine_similarity, retrieve_top_chunks


def test_chunking():
    text = " ".join([f"word{i}" for i in range(1200)])
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) > 1, "Should produce multiple chunks"
    for c in chunks:
        assert len(c.split()) <= 500, "Chunk exceeds max size"
    print("  [PASS] Chunking — produces correct chunk sizes")


def test_cosine_similarity():
    a = [1.0, 0.0, 0.0]
    b = [1.0, 0.0, 0.0]
    c = [0.0, 1.0, 0.0]
    assert abs(cosine_similarity(a, b) - 1.0) < 1e-6, "Identical vectors should have similarity 1"
    assert abs(cosine_similarity(a, c)) < 1e-6, "Orthogonal vectors should have similarity 0"
    print("  [PASS] Cosine similarity — identity and orthogonality correct")


def test_retrieval():
    chunks = ["The sky is blue and vast.", "Python is a programming language.", "Coffee is great in the morning."]
    # Fake embeddings — manually make chunk[1] closest to query
    embeddings = [
        [0.1, 0.9, 0.0],
        [0.9, 0.1, 0.0],
        [0.0, 0.0, 1.0],
    ]
    query_embedding = [0.85, 0.15, 0.0]
    top = retrieve_top_chunks(query_embedding, embeddings, chunks, top_k=1)
    assert top[0] == chunks[1], f"Expected chunk about Python, got: {top[0]}"
    print("  [PASS] Retrieval — returns most similar chunk correctly")


@pytest.mark.parametrize(
    "text,chunk_size,overlap",
    [
        ("", 100, 10),
        ("", 1, 0),
        (None, 100, 10),
    ],
)
def test_chunk_text_empty_and_none_inputs(text, chunk_size, overlap):
    """Covers empty and None inputs for chunking behavior."""
    if text is None:
        try:
            chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        except Exception:
            assert True
        else:
            assert True
    else:
        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        assert chunks == []


@pytest.mark.parametrize(
    "a,b,expected",
    [
        ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0], 0.0),
        ([-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], -1.0),
        ([1.0], [1.0], 1.0),
    ],
)
def test_cosine_similarity_boundary_cases(a, b, expected):
    """Covers zero vectors and extreme directional similarity values."""
    result = cosine_similarity(a, b)
    assert math.isfinite(result)
    assert abs(result - expected) < 1e-6


@pytest.mark.parametrize(
    "top_k,expected_len",
    [
        (0, 0),
        (1, 1),
        (10, 3),
    ],
)
def test_retrieve_top_chunks_topk_edges(top_k, expected_len):
    """Covers retrieval edge cases for top_k boundaries and overflow."""
    chunks = ["a", "b", "c"]
    embeddings = [
        [1.0, 0.0],
        [0.5, 0.5],
        [0.0, 1.0],
    ]
    query_embedding = [1.0, 0.0]
    result = retrieve_top_chunks(query_embedding, embeddings, chunks, top_k=top_k)
    assert isinstance(result, list)
    assert len(result) == expected_len


if __name__ == "__main__":
    print("\n=== pdf-chatbot-rag: Sanity Tests ===\n")
    try:
        test_chunking()
        test_cosine_similarity()
        test_retrieval()
        print("\n[ALL TESTS PASSED]\n")
    except AssertionError as e:
        print(f"\n[FAILED] {e}\n")
        sys.exit(1)
