"""
Document Comparison Agent
Compares two documents (text or PDF) and identifies differences,
similarities, conflicts, and produces a structured diff report.
"""

import os
import sys
import json
import time
from functools import wraps
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text

load_dotenv()

console = Console()
CHAT_MODEL = "gpt-4o-mini"

_client = None


def _is_retryable_openai_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code in (429, 500, 502, 503, 504):
        return True

    exc_name = exc.__class__.__name__
    retryable_names = {
        "RateLimitError",
        "APIConnectionError",
        "APITimeoutError",
        "InternalServerError",
    }
    return exc_name in retryable_names


def retry_with_backoff(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exception = None
        for attempt in range(len(delays) + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if not _is_retryable_openai_error(e):
                    raise
                last_exception = e
                if attempt < len(delays):
                    with console.status("[bold green]Processing..."):
                        time.sleep(delays[attempt])
                else:
                    raise last_exception
    return wrapper


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def print_usage(response) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(usage, "total_tokens", prompt_tokens + completion_tokens) or 0
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(
        f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}"
    )


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("❌ Missing OPENAI_API_KEY. Set it in your environment or .env file.")
        sys.exit(1)

    file_args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    for file_path in file_args:
        path = Path(file_path)
        if not path.exists():
            console.print(f"❌ File not found: {file_path}")
            sys.exit(1)
        if not path.is_file():
            console.print(f"❌ Not a file: {file_path}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"❌ File is not readable: {file_path}")
            sys.exit(1)

    console.print("Setup OK ✓")


COMPARE_SCHEMA = {
    "name": "comparison_report",
    "description": "Structured comparison between two documents",
    "parameters": {
        "type": "object",
        "properties": {
            "doc1_summary": {"type": "string", "description": "2-3 sentence summary of document 1"},
            "doc2_summary": {"type": "string", "description": "2-3 sentence summary of document 2"},
            "overall_similarity": {
                "type": "integer",
                "description": "Similarity score 0-100 (100 = identical content)"
            },
            "common_themes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Topics or points present in both documents"
            },
            "unique_to_doc1": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key points or information only in document 1"
            },
            "unique_to_doc2": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key points or information only in document 2"
            },
            "conflicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "doc1_position": {"type": "string"},
                        "doc2_position": {"type": "string"}
                    },
                    "required": ["topic", "doc1_position", "doc2_position"]
                },
                "description": "Areas where the two documents contradict or disagree"
            },
            "tone_comparison": {
                "type": "string",
                "description": "How the writing tone/style differs between documents"
            },
            "recommendation": {
                "type": "string",
                "description": "Suggested next steps or which document to prefer for a given purpose"
            }
        },
        "required": [
            "doc1_summary", "doc2_summary", "overall_similarity",
            "common_themes", "unique_to_doc1", "unique_to_doc2",
            "conflicts", "recommendation"
        ]
    }
}


def read_document(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        with console.status("[bold green]Processing..."):
            with open(path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(p.extract_text() or "" for p in reader.pages)
    with console.status("[bold green]Processing..."):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()


def parse_response(response) -> dict:
    message = response.choices[0].message

    if getattr(message, "tool_calls", None):
        tool_call = message.tool_calls[0]
        arguments = tool_call.function.arguments
        if isinstance(arguments, str):
            return json.loads(arguments)
        return arguments

    content = message.content
    if isinstance(content, str):
        return json.loads(content)

    raise ValueError("Unable to parse model response into comparison report")


@retry_with_backoff
def compare_documents(text1: str, text2: str, doc1_name: str, doc2_name: str, context: str = "") -> dict:
    system_prompt = (
        "You are a precise document comparison analyst. Compare two documents and return "
        "a structured report using the provided schema. Be objective, concise, and factual."
    )

    user_prompt = f"""
Compare the following two documents.

Document 1 Name: {doc1_name}
Document 1 Content:
{text1}

Document 2 Name: {doc2_name}
Document 2 Content:
{text2}

Additional Context:
{context or "None provided."}
"""

    with console.status("[bold green]Comparing documents..."):
        response = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            tools=[{"type": "function", "function": COMPARE_SCHEMA}],
            tool_choice={"type": "function", "function": {"name": COMPARE_SCHEMA["name"]}},
            temperature=0,
        )

    print_usage(response)
    return parse_response(response)


def display_report(report: dict, doc1_name: str, doc2_name: str) -> None:
    console.print(Panel.fit("📄 Document Comparison Report", style="bold cyan"))

    summary_table = Table(title="Summaries")
    summary_table.add_column("Document", style="bold")
    summary_table.add_column("Summary")
    summary_table.add_row(doc1_name, report.get("doc1_summary", ""))
    summary_table.add_row(doc2_name, report.get("doc2_summary", ""))
    console.print(summary_table)

    similarity = report.get("overall_similarity", 0)
    console.print(Panel(f"Overall Similarity: {similarity}/100", style="green"))

    common = "\n".join(f"• {x}" for x in report.get("common_themes", [])) or "None"
    only1 = "\n".join(f"• {x}" for x in report.get("unique_to_doc1", [])) or "None"
    only2 = "\n".join(f"• {x}" for x in report.get("unique_to_doc2", [])) or "None"

    console.print(
        Columns(
            [
                Panel(common, title="Common Themes", border_style="cyan"),
                Panel(only1, title=f"Unique to {doc1_name}", border_style="magenta"),
                Panel(only2, title=f"Unique to {doc2_name}", border_style="yellow"),
            ]
        )
    )

    conflicts = report.get("conflicts", [])
    if conflicts:
        conflict_table = Table(title="Conflicts")
        conflict_table.add_column("Topic", style="bold red")
        conflict_table.add_column(doc1_name)
        conflict_table.add_column(doc2_name)
        for c in conflicts:
            conflict_table.add_row(c.get("topic", ""), c.get("doc1_position", ""), c.get("doc2_position", ""))
        console.print(conflict_table)

    tone = report.get("tone_comparison")
    if tone:
        console.print(Panel(Text(tone), title="Tone Comparison", border_style="blue"))

    recommendation = report.get("recommendation")
    if recommendation:
        console.print(Panel(Text(recommendation), title="Recommendation", border_style="bold green"))


def main() -> None:
    validate_environment()

    if len(sys.argv) < 3:
        console.print("Usage: python compare.py <document1> <document2> [context]")
        sys.exit(1)

    doc1_path = sys.argv[1]
    doc2_path = sys.argv[2]
    context = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""

    text1 = read_document(doc1_path)
    text2 = read_document(doc2_path)

    report = compare_documents(text1, text2, Path(doc1_path).name, Path(doc2_path).name, context)
    display_report(report, Path(doc1_path).name, Path(doc2_path).name)


if __name__ == "__main__":
    main()
