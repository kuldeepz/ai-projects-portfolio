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
from rich.console import Console

load_dotenv()
init(autoreset=True)
console = Console()

CHUNK_SIZE = 500       # words per chunk
CHUNK_OVERLAP = 50     # word overlap between chunks
TOP_K = 4              # number of chunks to retrieve per query
EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4o-mini"


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print(Fore.RED + "Missing OPENAI_API_KEY. Please set it in your .env file.")
        sys.exit(1)

    if len(sys.argv) < 2:
        print(Fore.YELLOW + "Usage: python chatbot.py <path_to_pdf>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    path = Path(pdf_path)

    if not os.path.exists(pdf_path):
        print(Fore.RED + f"File not found: {pdf_path}")
        sys.exit(1)

    if path.suffix.lower() != ".pdf":
        print(Fore.RED + f"Expected a PDF file: {pdf_path}")
        sys.exit(1)

    try:
        with open(pdf_path, "rb") as f:
            if f.read(4) != b"%PDF":
                print(Fore.RED + f"Invalid PDF file: {pdf_path}")
                sys.exit(1)
    except OSError:
        print(Fore.RED + f"Cannot read file: {pdf_path}")
        sys.exit(1)

    print(Fore.GREEN + "Setup OK ✓")


def read_pdf(pdf_path: str) -> str:
    text = ""
    with console.status("[bold green]Processing..."):
        with open(pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            for page in reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted + "\n"
    return text


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap

    return chunks


def get_embedding(text: str) -> list[float]:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with console.status("[bold green]Processing..."):
        response = client.embeddings.create(model=EMBED_MODEL, input=text)
    return response.data[0].embedding


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def retrieve_top_chunks(query_embedding: list[float], chunk_embeddings: list[list[float]], chunks: list[str], top_k: int = TOP_K) -> list[str]:
    scored = []
    with console.status("[bold green]Processing..."):
        for i, emb in enumerate(chunk_embeddings):
            score = cosine_similarity(query_embedding, emb)
            scored.append((score, chunks[i]))

        scored.sort(reverse=True, key=lambda x: x[0])
    return [chunk for _, chunk in scored[:top_k]]


def answer_question(question: str, context_chunks: list[str], chat_history: list[dict[str, Any]]) -> str:
    context = "\n\n".join(context_chunks)

    system_prompt = (
        "You are a helpful assistant answering questions based ONLY on provided context from a PDF. "
        "If the answer is not in the context, say you don't know."
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(chat_history)
    messages.append({
        "role": "user",
        "content": f"Context:\n{context}\n\nQuestion: {question}"
    })

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    with console.status("[bold green]Processing..."):
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.2,
        )
    return response.choices[0].message.content


def build_index(pdf_path: str) -> tuple[list[str], list[list[float]]]:
    print(Fore.CYAN + "Reading PDF...")
    text = read_pdf(pdf_path)

    print(Fore.CYAN + "Chunking text...")
    chunks = chunk_text(text)
    print(Fore.CYAN + f"Created {len(chunks)} chunks")

    print(Fore.CYAN + "Generating embeddings (this may take a moment)...")
    with console.status("[bold green]Processing..."):
        embeddings = [get_embedding(chunk) for chunk in chunks]

    return chunks, embeddings


def save_chat_history(chat_history: list[dict[str, Any]], output_path: str = "chat_history.json") -> None:
    data = {
        "timestamp": datetime.now().isoformat(),
        "history": chat_history,
    }
    with console.status("[bold green]Processing..."):
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def main() -> None:
    validate_environment()
    pdf_path = sys.argv[1]

    print(Style.BRIGHT + Fore.MAGENTA + "\n📄 PDF Chatbot with RAG")
    print(Fore.MAGENTA + f"Using file: {pdf_path}\n")

    chunks, chunk_embeddings = build_index(pdf_path)

    chat_history = []

    print(Fore.GREEN + "\nAsk questions about the document.")
    print(Fore.GREEN + "Type 'exit' to quit, 'save' to save chat history.\n")

    while True:
        question = input(Fore.YELLOW + "You: ").strip()

        if question.lower() in ["exit", "quit"]:
            print(Fore.CYAN + "Goodbye!")
            break

        if question.lower() == "save":
            save_chat_history(chat_history)
            print(Fore.GREEN + "Chat history saved to chat_history.json")
            continue

        if not question:
            continue

        print(Fore.CYAN + "Thinking...")
        query_embedding = get_embedding(question)
        top_chunks = retrieve_top_chunks(query_embedding, chunk_embeddings, chunks)
        answer = answer_question(question, top_chunks, chat_history)

        print(Fore.GREEN + "Assistant: " + answer + "\n")

        chat_history.append({"role": "user", "content": question})
        chat_history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    main()
