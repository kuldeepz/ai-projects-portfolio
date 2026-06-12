"""
AI Resume Analyzer
Extracts skills, identifies gaps, scores the resume, and gives improvement suggestions.
"""

import os
import sys
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
import PyPDF2
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

load_dotenv()

_client = None


def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exception = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e
                if i == len(delays) - 1:
                    break
                time.sleep(delay)
        raise last_exception
    return wrapper


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


console = Console()

CHAT_MODEL = "gpt-4o-mini"

ANALYSIS_SCHEMA = {
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


def validate_environment():
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
    with open(pdf_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        return "\n".join(p.extract_text() or "" for p in reader.pages)


def extract_text_from_txt(txt_path: str) -> str:
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
def analyze_resume(resume_text: str, target_role: str = "") -> dict:
    """Call GPT with function calling to get structured resume analysis."""
    role_context = f"\nTarget role: {target_role}" if target_role else ""

    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an expert resume reviewer and career coach with 15+ years of experience "
                    "in technical recruiting. Analyze resumes critically and provide honest, actionable feedback."
                )
            },
            {
                "role": "user",
                "content": f"Analyze this resume:{role_context}\n\n{resume_text}"
            }
        ],
        tools=[{"type": "function", "function": ANALYSIS_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "resume_analysis"}},
        temperature=0.3,
    )

    tool_call = response.choices[0].message.tool_calls[0]
    return json.loads(tool_call.function.arguments)


# ------------------------------
# Unit tests for retry behavior
# ------------------------------
import unittest
from unittest.mock import patch


class TestRetryWithBackoff(unittest.TestCase):
    def test_succeeds_immediately_no_sleep(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            return "ok"

        wrapped = retry_with_backoff(fn)
        with patch("time.sleep") as sleep_mock:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 1)
        sleep_mock.assert_not_called()

    def test_fails_twice_then_succeeds(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("temporary")
            return "ok"

        wrapped = retry_with_backoff(fn)
        with patch("time.sleep") as sleep_mock:
            result = wrapped()

        self.assertEqual(result, "ok")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(sleep_mock.call_count, 2)
        sleep_mock.assert_any_call(1)
        sleep_mock.assert_any_call(2)

    def test_fails_all_attempts_exception_propagated(self):
        calls = {"n": 0}

        def fn():
            calls["n"] += 1
            raise ValueError("always fails")

        wrapped = retry_with_backoff(fn)
        with patch("time.sleep") as sleep_mock:
            with self.assertRaises(ValueError):
                wrapped()

        self.assertEqual(calls["n"], 3)
        self.assertEqual(sleep_mock.call_count, 2)
        sleep_mock.assert_any_call(1)
        sleep_mock.assert_any_call(2)


if __name__ == "__main__":
    unittest.main()
