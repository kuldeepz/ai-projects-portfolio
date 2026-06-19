"""
AI Resume Analyzer
Extracts skills, identifies gaps, scores the resume, and gives improvement suggestions.
"""

import os
import sys
import json
import time
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

load_dotenv()

_client: OpenAI | None = None
VERBOSE: bool = False


def retry_with_backoff(func: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        delays = [1, 2, 4]
        last_exception: Exception | None = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if i == len(delays) - 1:
                    break
                with console.status("[bold green]Processing..."):
                    time.sleep(delay)
        raise last_exception
    return wrapper


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


console: Console = Console()

CHAT_MODEL: str = "gpt-4o-mini"


def print_usage(response: Any) -> None:
    usage = getattr(response, "usage", None)
    if not usage:
        return
    prompt_tokens = getattr(usage, "prompt_tokens", 0) or 0
    completion_tokens = getattr(usage, "completion_tokens", 0) or 0
    total_tokens = getattr(response, "total_tokens", prompt_tokens + completion_tokens) or (prompt_tokens + completion_tokens)
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")


ANALYSIS_SCHEMA: dict[str, Any] = {
    "name": "resume_analysis",
    "description": "Structured analysis of a resume",
    "parameters": {
        "type": "object",
        "properties": {
            "candidate_name": {"type": "string", "description": "Full name of the candidate"},
            "current_role": {"type": "string", "description": "Most recent job title"},
            "years_experience": {"type": "number", "description": "Estimated total years of experience"},
            "overall_score": {"type": "integer", "description": "Resume quality score 1-100"},
            "technical_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of technical skills found"
            },
            "soft_skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of soft skills found"
            },
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Top 3-5 strengths of the resume"
            },
            "gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Key skill gaps or missing areas"
            },
            "improvements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific actionable improvement suggestions"
            },
            "ats_score": {"type": "integer", "description": "ATS (Applicant Tracking System) friendliness score 1-100"},
            "ats_issues": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Issues that could hurt ATS parsing"
            },
            "summary": {"type": "string", "description": "2-3 sentence overall assessment"}
        },
        "required": [
            "candidate_name", "current_role", "years_experience", "overall_score",
            "technical_skills", "soft_skills", "strengths", "gaps",
            "improvements", "ats_score", "ats_issues", "summary"
        ]
    }
}


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Missing OPENAI_API_KEY.[/red] Set it in your environment or .env file.")
        sys.exit(1)

    file_args = [arg for arg in sys.argv[1:] if not arg.startswith("-")]
    if file_args:
        resume_path = Path(file_args[0])
        if not resume_path.exists():
            console.print(f"[red]File not found:[/red] {resume_path}")
            sys.exit(1)
        if not resume_path.is_file():
            console.print(f"[red]Not a file:[/red] {resume_path}")
            sys.exit(1)
        if not os.access(resume_path, os.R_OK):
            console.print(f"[red]File is not readable:[/red] {resume_path}")
            sys.exit(1)
        if resume_path.suffix.lower() not in (".pdf", ".txt", ".md"):
            console.print(f"[red]Unsupported file type:[/red] {resume_path.suffix}")
            sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")


def extract_text_from_pdf(pdf_path: str) -> str:
    with console.status("[bold green]Processing..."):
        with open(pdf_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(p.extract_text() or "" for p in reader.pages)


def extract_text_from_txt(txt_path: str) -> str:
    with console.status("[bold green]Processing..."):
        with open(txt_path, "r", encoding="utf-8") as f:
            return f.read()


def load_resume(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    elif ext in (".txt", ".md"):
        return extract_text_from_txt(path)
    else:
        console.print(f"[red]Unsupported file type: {ext}. Use PDF or TXT.[/red]")
        sys.exit(1)


@retry_with_backoff
def analyze_resume(resume_text: str, target_role: str = "") -> dict[str, Any]:
    """Call GPT with function calling to get structured resume analysis."""
    with console.status("[bold green]Processing..."):
        role_line = f"Target role: {target_role}\n" if target_role else ""
        prompt = (
            "Analyze this resume and return structured JSON via function call.\n"
            f"{role_line}"
            f"Resume:\n{resume_text}"
        )

        client = get_client()
        response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": "You are an expert resume reviewer."},
                {"role": "user", "content": prompt},
            ],
            tools=[{"type": "function", "function": ANALYSIS_SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "resume_analysis"}},
            temperature=0.2,
        )

    print_usage(response)

    message = response.choices[0].message
    tool_calls = getattr(message, "tool_calls", None) or []
    if tool_calls:
        args = tool_calls[0].function.arguments
        return json.loads(args) if isinstance(args, str) else args

    content = message.content or "{}"
    if isinstance(content, list):
        content = "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
    return json.loads(content)
