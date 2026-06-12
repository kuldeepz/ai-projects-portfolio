"""
AI Decision Log Creator (Architecture Decision Records)
Converts discussion notes or meeting summaries into formal ADR documents.
"""

import os, sys, json, time
from datetime import date
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"
VERBOSE = False

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

SCHEMA = {
    "name": "adr",
    "description": "Architecture Decision Record",
    "parameters": {
        "type": "object",
        "properties": {
            "adr_number": {"type": "string"},
            "title": {"type": "string"},
            "status": {"type": "string", "enum": ["proposed", "accepted", "deprecated", "superseded"]},
            "context": {"type": "string", "description": "Why this decision was needed"},
            "decision": {"type": "string", "description": "What was decided"},
            "rationale": {"type": "string", "description": "Why this option was chosen over alternatives"},
            "alternatives_considered": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"option": {"type": "string"}, "pros": {"type": "string"}, "cons": {"type": "string"}},
                          "required": ["option", "pros", "cons"]}
            },
            "consequences": {
                "type": "object",
                "properties": {"positive": {"type": "array", "items": {"type": "string"}},
                               "negative": {"type": "array", "items": {"type": "string"}},
                               "risks": {"type": "array", "items": {"type": "string"}}},
                "required": ["positive", "negative", "risks"]
            },
            "full_markdown": {"type": "string"}
        },
        "required": ["title", "status", "context", "decision", "rationale",
                     "alternatives_considered", "consequences", "full_markdown"]
    }
}

SAMPLE_DISCUSSION = """
Date: 2024-06-10
Participants: Kuldeep (AI Lead), Sarah (Backend), Raj (DevOps)

We need to decide how to store and serve vector embeddings for our RAG system.
Currently we're doing cosine similarity in pure Python which works for our POC (5K docs)
but won't scale to the production target of 500K documents.

Options discussed:
1. Pinecone - managed, easy to set up, $70/mo for our scale, SOC2 compliant
2. pgvector (Postgres extension) - we already use Postgres, free, but need to manage ourselves
3. Qdrant self-hosted on Kubernetes - open source, more control, team has k8s expertise
4. Weaviate Cloud - similar to Pinecone, $90/mo

We leaned toward pgvector because:
- We already manage Postgres, adding an extension is low-ops overhead
- Cost is infrastructure only (no per-query pricing)
- Team knows SQL, no new query language
- Raj confirmed our RDS instance can be upgraded to support pgvector

Concerns raised:
- Sarah worried about performance at 500K+ docs, Raj said we can add HNSW index
- Kuldeep noted we need to document the decision so future team members understand why not Pinecone

Action: Use pgvector. Raj to upgrade RDS and create migration. Sarah to update the embedding pipeline.
"""

def create_adr(discussion: str, adr_number: str = "001") -> dict:
    if VERBOSE:
        prompt = f"Create an ADR (number: {adr_number}) from this discussion:\n\n{discussion}"
        console.print(f"[dim]Model:[/dim] {MODEL}")
        console.print(f"[dim]Input chars:[/dim] {len(prompt)}")
        console.print(f"[dim]Input tokens (est):[/dim] {max(1, len(prompt) // 4)}")
        console.print("⏳ Calling OpenAI API...")
        start = time.perf_counter()
    with console.status("[bold green]Processing...[/bold green]"):
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a principal engineer creating Architecture Decision Records (ADRs) in the "
                    "Michael Nygard format. Extract the decision from the discussion, structure it formally, "
                    "ensure the context section captures WHY the decision was needed, and the consequences "
                    "section is honest about tradeoffs. Write the full_markdown as a complete, ready-to-commit ADR file."
                )},
                {"role": "user", "content": f"Create an ADR (number: {adr_number}) from this discussion:\n\n{discussion}"}
            ],
            tools=[{"type": "function", "function": SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "adr"}},
            temperature=0.2,
        )
    if VERBOSE:
        elapsed = time.perf_counter() - start
        console.print(f"✅ Done in {elapsed:.1f}s")
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def main():
    global VERBOSE
    args = sys.argv[1:]
    if "--verbose" in args:
        VERBOSE = True
        args.remove("--verbose")
    if "-v" in args:
        VERBOSE = True
        args.remove("-v")

    if len(args) < 1:
        console.print("[dim]No file provided — using sample discussion...[/dim]\n")
        discussion = SAMPLE_DISCUSSION
        adr_num = "001"
    else:
        with console.status("[bold green]Processing...[/bold green]"):
            with open(args[0]) as f:
                discussion = f.read()
        adr_num = args[1] if len(args) > 1 else "001"

    with console.status("[bold green]Generating ADR...[/bold green]"):
        adr = create_adr(discussion, adr_num)

    console.print()
    console.print(Panel(Markdown(adr["full_markdown"]),
                        title=f"[bold cyan]ADR-{adr_num}: {adr['title']}[/bold cyan]",
                        border_style="cyan"))


def _run_tests():
    from types import SimpleNamespace
    from unittest.mock import patch, mock_open

    def fake_response():
        payload = json.dumps({
            "title": "Use pgvector",
            "status": "accepted",
            "context": "ctx",
            "decision": "dec",
            "rationale": "why",
            "alternatives_considered": [],
            "consequences": {"positive": [], "negative": [], "risks": []},
            "full_markdown": "# ADR"
        })
        return SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(
                    tool_calls=[SimpleNamespace(function=SimpleNamespace(arguments=payload))]
                )
            )]
        )

    class _Status:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    global VERBOSE

    # (1) -v and --verbose both set verbosity and (2) positional args still parse after removal
    for flag in ("-v", "--verbose"):
        VERBOSE = False
        calls = []
        with patch.object(console, "status", side_effect=lambda *a, **k: _Status()), \
             patch.object(console, "print"), \
             patch("builtins.open", mock_open(read_data="discussion from file")), \
             patch(__name__ + ".create_adr", side_effect=lambda d, n: calls.append((d, n)) or {
                 "title": "T", "full_markdown": "# M"
             }):
            sys.argv = ["adr_creator.py", flag, "notes.txt", "123"]
            main()
        assert VERBOSE is True
        assert calls == [("discussion from file", "123")]

    # (3) non-verbose flow unchanged
    VERBOSE = False
    prints = []
    fake_client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: fake_response()
            )
        )
    )
    with patch.object(console, "status", side_effect=lambda *a, **k: _Status()), \
         patch.object(console, "print", side_effect=lambda *a, **k: prints.append(a)):
        with patch(__name__ + ".get_client", return_value=fake_client):
            create_adr("x", "001")
    assert not any("Model:" in " ".join(map(str, p)) for p in prints)

    # (4) verbose flow prints diagnostics and does not crash
    VERBOSE = True
    prints = []
    with patch.object(console, "status", side_effect=lambda *a, **k: _Status()), \
         patch.object(console, "print", side_effect=lambda *a, **k: prints.append(a)):
        with patch(__name__ + ".get_client", return_value=fake_client):
            create_adr("x", "001")
    joined = "\n".join(" ".join(map(str, p)) for p in prints)
    assert "Model:" in joined
    assert "Input chars:" in joined
    assert "Input tokens (est):" in joined
    assert "Calling OpenAI API" in joined


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--self-test":
        _run_tests()
    else:
        main()
