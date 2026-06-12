"""
AI Resume Analyzer
Extracts skills, identifies gaps, scores the resume, and gives improvement suggestions.
"""

import os
import sys
import json
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
    for path_arg in file_args:
        p = Path(path_arg)
        if p.suffix.lower() in (".pdf", ".txt", ".md"):
            if not p.exists():
                console.print(f"[red]File not found:[/red] {path_arg}")
                sys.exit(1)
            if not p.is_file():
                console.print(f"[red]Not a file:[/red] {path_arg}")
                sys.exit(1)
            if not os.access(p, os.R_OK):
                console.print(f"[red]File is not readable:[/red] {path_arg}")
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


def score_color(score: int) -> str:
    if score >= 80:
        return "green"
    elif score >= 60:
        return "yellow"
    return "red"


def display_results(analysis: dict):
    console.print()
    console.print(Panel.fit(
        f"[bold white]{analysis['candidate_name']}[/bold white]\n"
        f"[dim]{analysis['current_role']} · {analysis['years_experience']} yrs exp[/dim]",
        title="[bold cyan]Resume Analysis Report[/bold cyan]",
        border_style="cyan"
    ))

    # Scores
    score_table = Table(show_header=False, box=None, padding=(0, 2))
    score_table.add_column(style="dim")
    s
