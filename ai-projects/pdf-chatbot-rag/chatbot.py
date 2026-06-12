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
from datetime import datetime

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

PRICING_PER_1K = {
    "gpt-4o-mini": {"input": 0.000015, "output": 0.00006},
    "text-embedding-3-small": {"input": 0.00002, "output": 0.0},
}


def print_usage(response, model: str):
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


def validate_environment():
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
    print_usage(response, CHAT_MODEL)
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
        print(Fore.RED + "  No text could be extracted. Is the PDF readable?")
        return [], []


def export_results(results: dict) -> Optional[str]:
    args = sys.argv[1:]
    if "--export" not in args and "-e" not in args:
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(f"output_{timestamp}.json")

    export_payload = dict(results)
    export_payload["generated_at"] = datetime.now().isoformat()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(export_payload, f, indent=2, ensure_ascii=False)

    return str(output_path)


# -----------------------------
# Tests for validate_environment
# -----------------------------

def test_validate_environment_missing_api_key_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["chatbot.py"])
    monkeypatch.setattr(os, "getenv", lambda key: "" if key == "OPENAI_API_KEY" else None)

    try:
        validate_environment()
        assert False, "Expected SystemExit"
    except SystemExit as e:
        assert e.code == 1

    out = capsys.readouterr().out
    assert "Missing OPENAI_API_KEY" in out


def test_validate_environment_nonexistent_path_exits_1(monkeypatch, capsys):
    monkeypatch.setattr(os, "getenv", lambda key: "test-key" if key == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(sys, "argv", ["chatbot.py", "does-not-exist.pdf"])

    try:
        validate_environment()
        assert False, "Expected SystemExit"
    except SystemExit as e:
        assert e.code == 1

    out = capsys.readouterr().out
    assert "File not found" in out


def test_validate_environment_directory_path_exits_1(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(os, "getenv", lambda key: "test-key" if key == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(sys, "argv", ["chatbot.py", str(tmp_path)])

    try:
        validate_environment()
        assert False, "Expected SystemExit"
    except SystemExit as e:
        assert e.code == 1

    out = capsys.readouterr().out
    assert "Not a file" in out


def test_validate_environment_unreadable_file_exits_1(monkeypatch, tmp_path, capsys):
    f = tmp_path / "sample.pdf"
    f.write_text("x")

    monkeypatch.setattr(os, "getenv", lambda key: "test-key" if key == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(sys, "argv", ["chatbot.py", str(f)])
    monkeypatch.setattr(os, "access", lambda path, mode: False)

    try:
        validate_environment()
        assert False, "Expected SystemExit"
    except SystemExit as e:
        assert e.code == 1

    out = capsys.readouterr().out
    assert "File is not readable" in out


def test_validate_environment_valid_setup_prints_success_and_no_exit(monkeypatch, tmp_path, capsys):
    f = tmp_path / "sample.pdf"
    f.write_text("x")

    monkeypatch.setattr(os, "getenv", lambda key: "test-key" if key == "OPENAI_API_KEY" else None)
    monkeypatch.setattr(sys, "argv", ["chatbot.py", str(f)])
    monkeypatch.setattr(os, "access", lambda path, mode: True)

    validate_environment()

    out = capsys.readouterr().out
    assert "Setup OK" in out
