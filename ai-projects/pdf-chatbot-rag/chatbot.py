"""
PDF Chatbot with RAG (Retrieval-Augmented Generation)
Loads a PDF, chunks it, creates embeddings, and answers questions using relevant context.
"""

import os
import sys
import json
import math
import hashlib
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from colorama import init, Fore, Style

load_dotenv()
init(autoreset=True)

_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

CHUNK_SIZE = 500       # words per chunk
CHUNK_OVERLAP = 50     # word overlap between chunks
TOP_K = 4              # number of chunks to retrieve per query
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    text = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """Get OpenAI embeddings for a list of texts in batches."""
    all_embeddings = []
    batch_size = 100
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        response = get_client().embeddings.create(model=EMBED_MODEL, input=batch)
        all_embeddings.extend([item.embedding for item in response.data])
    return all_embeddings


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_top_chunks(query_embedding: list[float], chunk_embeddings: list[list[float]], chunks: list[str], top_k: int = TOP_K) -> list[str]:
    """Return the top-k most relevant chunks by cosine similarity."""
    scores = [(cosine_similarity(query_embedding, emb), chunk) for emb, chunk in zip(chunk_embeddings, chunks)]
    scores.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scores[:top_k]]


def answer_question(question: str, context_chunks: list[str], chat_history: list[dict]) -> str:
    """Generate an answer using GPT with retrieved context."""
    context = "\n\n---\n\n".join(context_chunks)

    system_prompt = (
        "You are a helpful assistant that answers questions strictly based on the provided document context. "
        "If the answer is not found in the context, say so clearly. Be concise and accurate."
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-6:])  # keep last 3 turns for context
    messages.append({
        "role": "user",
        "content": f"Context from document:\n{context}\n\nQuestion: {question}"
    })

    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content


def build_index(pdf_path: str) -> tuple[list[str], list[list[float]]]:
    """Extract, chunk, and embed a PDF. Returns chunks and their embeddings."""
    cache_path = Path(pdf_path).with_suffix(".cache.json")

    if cache_path.exists():
        print(Fore.YELLOW + "  Loading cached embeddings...")
        with open(cache_path) as f:
            data = json.load(f)
        return data["chunks"], data["embeddings"]

    print(Fore.CYAN + "  Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)
    if not text.strip():
        print(Fore.RED + "  No text could be extracted. Is the PDF scanned/image-based?")
        sys.exit(1)

    print(Fore.CYAN + f"  Chunking text ({len(text.split())} words)...")
    chunks = chunk_text(text)
    print(Fore.CYAN + f"  Created {len(chunks)} chunks. Generating embeddings...")

    embeddings = get_embeddings(chunks)

    with open(cache_path, "w") as f:
        json.dump({"chunks": chunks, "embeddings": embeddings}, f)
    print(Fore.GREEN + "  Embeddings cached for future use.")

    return chunks, embeddings


def run_chat(pdf_path: str):
    """Main interactive chat loop."""
    print(Fore.GREEN + Style.BRIGHT + "\n=== PDF Chatbot (RAG) ===")
    print(Fore.WHITE + f"Loading: {pdf_path}\n")

    if not os.path.exists(pdf_path):
        print(Fore.RED + f"File not found: {pdf_path}")
        sys.exit(1)

    chunks, embeddings = build_index(pdf_path)
    print(Fore.GREEN + f"\nReady! {len(chunks)} chunks indexed from your PDF.")
    print(Fore.WHITE + "Type your question below. Type 'exit' to quit.\n")

    chat_history = []

    while True:
        try:
            question = input(Fore.CYAN + "You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print(Fore.YELLOW + "\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("exit", "quit", "q"):
            print(Fore.YELLOW + "Goodbye!")
            break

        query_embedding = get_embeddings([question])[0]
        top_chunks = retrieve_top_chunks(query_embedding, embeddings, chunks)
        answer = answer_question(question, top_chunks, chat_history)

        print(Fore.GREEN + "\nAssistant: " + Style.RESET_ALL + answer + "\n")

        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(Fore.YELLOW + "Usage: python chatbot.py <path_to_pdf>")
        print(Fore.WHITE + "Example: python chatbot.py sample.pdf")
        sys.exit(1)

    run_chat(sys.argv[1])
