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
    score_table.add_column()

    overall = analysis["overall_score"]
    ats = analysis["ats_score"]
    score_table.add_row(
        "Overall Score",
        f"[{score_color(overall)} bold]{overall}/100[/{score_color(overall)} bold]"
    )
    score_table.add_row(
        "ATS Score",
        f"[{score_color(ats)} bold]{ats}/100[/{score_color(ats)} bold]"
    )
    console.print(Panel(score_table, title="[bold]Scores[/bold]", border_style="blue"))

    # Skills
    skills_table = Table(show_header=True, header_style="bold magenta")
    skills_table.add_column("Technical Skills", style="cyan")
    skills_table.add_column("Soft Skills", style="green")
    max_len = max(len(analysis["technical_skills"]), len(analysis["soft_skills"]))
    tech = analysis["technical_skills"] + [""] * max_len
    soft = analysis["soft_skills"] + [""] * max_len
    for t, s in zip(tech[:max_len], soft[:max_len]):
        skills_table.add_row(t, s)
    console.print(Panel(skills_table, title="[bold]Skills Identified[/bold]", border_style="magenta"))

    # Strengths
    strengths_text = "\n".join(f"  [green]✔[/green] {s}" for s in analysis["strengths"])
    console.print(Panel(strengths_text, title="[bold green]Strengths[/bold green]", border_style="green"))

    # Gaps
    gaps_text = "\n".join(f"  [red]✘[/red] {g}" for g in analysis["gaps"])
    console.print(Panel(gaps_text, title="[bold red]Gaps & Missing Areas[/bold red]", border_style="red"))

    # Improvements
    improvements_text = "\n".join(f"  [yellow]→[/yellow] {i}" for i in analysis["improvements"])
    console.print(Panel(improvements_text, title="[bold yellow]Actionable Improvements[/bold yellow]", border_style="yellow"))

    # ATS Issues
    if analysis["ats_issues"]:
        ats_text = "\n".join(f"  [orange3]⚠[/orange3] {i}" for i in analysis["ats_issues"])
        console.print(Panel(ats_text, title="[bold orange3]ATS Issues[/bold orange3]", border_style="orange3"))

    # Summary
    console.print(Panel(
        f"[italic]{analysis['summary']}[/italic]",
        title="[bold]Overall Assessment[/bold]",
        border_style="dim"
    ))
    console.print()


def main():
    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] python analyzer.py <resume.pdf|resume.txt> [target_role]")
        console.print("[dim]Example: python analyzer.py my_resume.pdf 'Senior Data Engineer'[/dim]")
        sys.exit(1)

    resume_path = sys.argv[1]
    target_role = sys.argv[2] if len(sys.argv) > 2 else ""

    if not os.path.exists(resume_path):
        console.print(f"[red]File not found:[/red] {resume_path}")
        sys.exit(1)

    console.print(f"\n[cyan]Analyzing resume:[/cyan] {resume_path}")
    if target_role:
        console.print(f"[cyan]Target role:[/cyan] {target_role}")

    resume_text = load_resume(resume_path)
    if not resume_text.strip():
        console.print("[red]Could not extract text from the resume.[/red]")
        sys.exit(1)

    with console.status("[bold green]Analyzing with GPT-4o-mini...[/bold green]"):
        analysis = analyze_resume(resume_text, target_role)

    display_results(analysis)


if __name__ == "__main__":
    main()
