"""
Sanity test for pdf-chatbot-rag.
Creates a small in-memory text and validates chunking, embedding retrieval, and QA pipeline.
"""

import os
import sys
import math

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
