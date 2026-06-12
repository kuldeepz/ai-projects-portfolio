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
from typing import Any
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from colorama import init, Fore, Style

load_dotenv()
init(autoreset=True)

_client: OpenAI | None = None


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

PRICING_PER_1K = {
    "gpt-4o-mini": {"input": 0.000015, "output": 0.00006},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
}


def print_usage(response: Any, model: str) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        print(f"📊 [{model}] Tokens: 0 in + 0 out = 0 total | 💰 Est. cost: $0.000000")
        return

    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0

    rates = PRICING_PER_1K.get(model, {"input": 0.0, "output": 0.0})
    cost = (prompt_tokens / 1000) * rates["input"] + (completion_tokens / 1000) * rates["output"]

    print(
        f"📊 [{model}] Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total "
        f"| 💰 Est. cost: ${cost:.6f}"
    )


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        print(Fore.RED + "Missing OPENAI_API_KEY. Please set it in your environment or .env file.")
        sys.exit(1)

    if len(sys.argv) >= 2:
        args = sys.argv[1:]
        filtered_args = []
        i = 0
        while i < len(args):
            if args[i] in ("--export", "-e"):
                i += 1
                continue
            filtered_args.append(args[i])
            i += 1

        for arg in filtered_args:
            path = Path(arg)
            if not path.exists():
                print(Fore.RED + f"File not found: {arg}")
                sys.exit(1)
            if not path.is_file():
                print(Fore.RED + f"Not a file: {arg}")
                sys.exit(1)
            if not os.access(path, os.R_OK):
                print(Fore.RED + f"File is not readable: {arg}")
                sys.exit(1)

    print(Fore.GREEN + "Setup OK ✓")


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
        print_usage(response, EMBED_MODEL)
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


def answer_question(question: str, context_chunks: list[str], chat_history: list[dict[str, Any]]) -> str:
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
    print_usage(response, CHAT_MODEL)
    return response.choices[0].message.content


def build_index(pdf_path: str) -> tuple[list[str], list[list[float]]]:
    """Extract, chunk, and embed a PDF. Returns chunks and their embeddings."""
    cache_path = Path(pdf_path).with_suffix(".cache.json")

    if cache_path.exists():
        print(Fore.YELLOW + "  Loading cached embeddings...")
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        return cached["chunks"], cached["embeddings"]

    print(Fore.CYAN + "  Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)

    print(Fore.CYAN + "  Chunking text...")
    chunks = chunk_text(text)

    print(Fore.CYAN + "  Creating embeddings...")
    embeddings = get_embeddings(chunks)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks, "embeddings": embeddings}, f)

    return chunks, embeddings


def export_results(results: dict[str, Any], enabled: bool, output_path: Path | None = None) -> Path | None:
    """Export results to JSON when enabled."""
    if not enabled:
        return None

    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(f"output_{timestamp}.json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return output_path
