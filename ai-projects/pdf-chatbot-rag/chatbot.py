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

CHUNK_SIZE = 500       # words per chunk
CHUNK_OVERLAP = 50     # word overlap between chunks
TOP_K = 4              # number of chunks to retrieve per query
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(Fore.RED + "Missing OPENAI_API_KEY. Please set it in your environment or .env file.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(Fore.RED + "Usage: python chatbot.py <pdf_file>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(Fore.RED + f"File not found: {pdf_path}")
        sys.exit(1)

    if not os.path.isfile(pdf_path):
        print(Fore.RED + f"Not a file: {pdf_path}")
        sys.exit(1)

    if not os.access(pdf_path, os.R_OK):
        print(Fore.RED + f"File is not readable: {pdf_path}")
        sys.exit(1)

    print(Fore.GREEN + "Setup OK ✓")


def extract_text_from_pdf(pdf_path: str) -> str:
    text: list[str] = []
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    return "\n".join(text)


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    step = chunk_size - overlap
    for i in range(0, len(words), step):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks


def get_embeddings(texts: list[str]) -> list[list[float]]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    return [item.embedding for item in response.data]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_top_chunks(
    query_embedding: list[float],
    chunk_embeddings: list[list[float]],
    chunks: list[str],
    top_k: int = TOP_K,
) -> list[str]:
    scores = [(cosine_similarity(query_embedding, emb), chunk) for emb, chunk in zip(chunk_embeddings, chunks)]
    scores.sort(key=lambda x: x[0], reverse=True)
    return [chunk for _, chunk in scores[:top_k]]


def answer_question(question: str, context_chunks: list[str], chat_history: list[dict[str, Any]]) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    context = "\n\n---\n\n".join(context_chunks)

    system_prompt = (
        "You are a helpful assistant that answers questions strictly based on the provided document context. "
        "If the answer is not found in the context, say so clearly. Be concise and accurate."
    )

    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history[-6:])
    messages.append({
        "role": "user",
        "content": f"Context from document:\n{context}\n\nQuestion: {question}",
    })

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=0.2,
    )
    return response.choices[0].message.content


def build_index(pdf_path: str) -> tuple[list[str], list[list[float]]]:
    cache_path = Path(pdf_path).with_suffix(".cache.json")

    if cache_path.exists():
        print(Fore.YELLOW + "  Loading cached embeddings...")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data["chunks"], data["embeddings"]

    print(Fore.CYAN + "  Extracting text from PDF...")
    text = extract_text_from_pdf(pdf_path)

    print(Fore.CYAN + "  Chunking text...")
    chunks = chunk_text(text)
    print(Fore.CYAN + f"  Created {len(chunks)} chunks")

    print(Fore.CYAN + "  Creating embeddings (this may take a moment)...")
    embeddings = get_embeddings(chunks)

    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump({"chunks": chunks, "embeddings": embeddings}, f)

    print(Fore.GREEN + f"  Index built and cached at {cache_path}")
    return chunks, embeddings


def main() -> None:
    print(Style.BRIGHT + Fore.BLUE + "\n📄 PDF Chatbot (RAG)\n")
    validate_environment()

    pdf_path = sys.argv[1]

    print(Fore.MAGENTA + f"\nBuilding/Loading index for: {pdf_path}")
    chunks, chunk_embeddings = build_index(pdf_path)

    print(Fore.GREEN + "\n✅ Ready! Ask questions about the PDF. Type 'exit' to quit.\n")

    chat_history: list[dict[str, Any]] = []

    while True:
        question = input(Fore.YELLOW + "You: ").strip()
        if question.lower() in {"exit", "quit"}:
            print(Fore.BLUE + "Goodbye!")
            break
        if not question:
            continue

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        q_embed_resp = client.embeddings.create(model=EMBED_MODEL, input=[question])
        query_embedding = q_embed_resp.data[0].embedding

        top_chunks = retrieve_top_chunks(query_embedding, chunk_embeddings, chunks)
        answer = answer_question(question, top_chunks, chat_history)

        print(Fore.CYAN + "\nAssistant: " + Style.RESET_ALL + f"{answer}\n")

        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
