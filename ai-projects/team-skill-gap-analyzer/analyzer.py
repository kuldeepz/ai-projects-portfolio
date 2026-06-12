"""
Team Skill Gap Analyzer
Maps team members' current skills against project requirements
and surfaces gaps, training needs, and hiring recommendations.
"""

import os, sys, json
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

SCHEMA = {
    "name": "skill_gap_report",
    "description": "Team skill gap analysis and recommendations",
    "parameters": {
        "type": "object",
        "properties": {
            "coverage_score": {"type": "integer", "description": "0-100: how well team covers project needs"},
            "critical_gaps": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"skill": {"type": "string"}, "required_level": {"type": "string"},
                                         "current_coverage": {"type": "string"}, "impact": {"type": "string"}},
                          "required": ["skill", "required_level", "current_coverage", "impact"]}
            },
            "member_fit": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"member": {"type": "string"}, "fit_score": {"type": "integer"},
                                         "strong_areas": {"type": "array", "items": {"type": "string"}},
                                         "development_areas": {"type": "array", "items": {"type": "string"}}},
                          "required": ["member", "fit_score", "strong_areas", "development_areas"]}
            },
            "training_recommendations": {
                "type": "array",
                "items": {"type": "object",
                          "properties": {"skill": {"type": "string"}, "for_members": {"type": "array", "items": {"type": "string"}},
                                         "course_suggestion": {"type": "string"}, "priority": {"type": "string"}},
                          "required": ["skill", "for_members", "priority"]}
            },
            "hiring_recommendations": {"type": "array", "items": {"type": "string"}},
            "overall_recommendation": {"type": "string"}
        },
        "required": ["coverage_score", "critical_gaps", "member_fit",
                     "training_recommendations", "hiring_recommendations", "overall_recommendation"]
    }
}

SAMPLE_DATA = {
    "project": {
        "name": "AI-Powered Customer Analytics Platform",
        "required_skills": [
            {"skill": "Python", "level": "expert", "importance": "critical"},
            {"skill": "LLM/OpenAI API", "level": "intermediate", "importance": "critical"},
            {"skill": "Vector databases (Pinecone/pgvector)", "level": "intermediate", "importance": "high"},
            {"skill": "MLOps / model deployment", "level": "intermediate", "importance": "high"},
            {"skill": "FastAPI", "level": "intermediate", "importance": "high"},
            {"skill": "Azure DevOps", "level": "basic", "importance": "medium"},
            {"skill": "React", "level": "basic", "importance": "medium"},
            {"skill": "Prompt engineering", "level": "advanced", "importance": "critical"},
            {"skill": "Data pipelines (Airflow/Spark)", "level": "basic", "importance": "medium"},
            {"skill": "RAG architecture", "level": "intermediate", "importance": "critical"},
        ]
    },
    "team": [
        {"name": "Kuldeep", "role": "AI Lead",
         "skills": {"Python": "expert", "LLM/OpenAI API": "expert", "Prompt engineering": "expert",
                    "RAG architecture": "advanced", "FastAPI": "intermediate", "Azure DevOps": "intermediate"}},
        {"name": "Sarah", "role": "Backend Engineer",
         "skills": {"Python": "expert", "FastAPI": "expert", "Data pipelines (Airflow/Spark)": "intermediate",
                    "Azure DevOps": "intermediate", "LLM/OpenAI API": "basic"}},
        {"name": "Raj", "role": "DevOps Engineer",
         "skills": {"MLOps / model deployment": "advanced", "Azure DevOps": "expert",
                    "Vector databases (Pinecone/pgvector)": "basic", "Python": "intermediate"}},
        {"name": "Priya", "role": "Frontend Engineer",
         "skills": {"React": "expert", "Python": "basic", "Azure DevOps": "basic"}},
        {"name": "Tom", "role": "Data Engineer",
         "skills": {"Data pipelines (Airflow/Spark)": "expert", "Python": "advanced",
                    "Vector databases (Pinecone/pgvector)": "basic"}},
    ]
}

def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Setup error:[/red] OPENAI_API_KEY is not set or is empty.")
        console.print("Set it in your environment or .env file and try again.")
        sys.exit(1)

    if len(sys.argv) >= 2:
        path = sys.argv[1]
        if not os.path.exists(path):
            console.print(f"[red]Setup error:[/red] File not found: {path}")
            sys.exit(1)
        if not os.path.isfile(path):
            console.print(f"[red]Setup error:[/red] Not a file: {path}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"[red]Setup error:[/red] File is not readable: {path}")
            sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")

def analyze_gaps(data: dict) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are an engineering manager and talent strategist. Analyze team skills vs project requirements. "
                "Identify critical gaps that could block delivery, recommend targeted training (with specific courses/resources), "
                "and suggest what profiles to hire if gaps can't be closed through training. Be specific and realistic."
            )},
            {"role": "user", "content": f"Analyze this team vs project requirements:\n\n{json.dumps(data, indent=2)}"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "skill_gap_report"}},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(data: dict, report: dict):
    score = report["coverage_score"]
    s_color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]{data['project']['name']}[/bold]\n"
        f"Team Coverage Score: [{s_color} bold]{score}/100[/{s_color} bold]",
        title="[bold cyan]Team Skill Gap Analysis[/bold cyan]", border_style="cyan"
    ))

    if report["critical_gaps"]:
        t = Table(show_header=True, header_style="bold red")
        t.add_column("Skill"); t.add_column("Required"); t.add_column("Coverage"); t.add_column("Impact", ratio=2)
        for g in report["critical_gaps"]:
            t.add_row(g["skill"], g["required_level"], g["current_coverage"], g["impact"])
        console.print(Panel(t, title="[bold red]Critical Gaps[/bold red]", border_style="red"))

    mt = Table(show_header=True, header_style="bold")
    mt.add_column("Member"); mt.add_column("Role"); mt.add_column("Fit", width=6)
    mt.add_column("Strong Areas", ratio=2); mt.add_column("Needs Development", ratio=2)
    for m in report["member_fit"]:
        fit = m["fit_score"]
        f_c = "green" if fit >= 75 else "yellow" if fit >= 50 else "red"
        mt.add_row(m["member"], next((tm["role"] for tm in data["team"] if tm["name"] == m["member"]), ""),
                   f"[{f_c}]{fit}[/{f_c}]",
                   ", ".join(m["strong_areas"][:2]),
                   ", ".join(m["development_areas"][:2]))
    console.print(Panel(mt, title="[bold]Member Fit Scores[/bold]", border_style="blue"))

    if report["training_recommendations"]:
        tt = Table(show_header=True, header_style="bold yellow")
        tt.add_column("Priority", width=10); tt.add_column("Skill")
        tt.add_column("Who", ratio=1); tt.add_column("Suggestion", ratio=2)
        priority_order = {"immediate": 0, "high": 1, "medium": 2, "low": 3}
        for tr in sorted(report["training_recommendations"], key=lambda x: priority_order.get(x.get("priority","low"), 3)):
            p = tr.get("priority", "medium")
            p_c = {"immediate": "bold red", "high": "red", "medium": "yellow", "low": "dim"}.get(p, "white")
            tt.add_row(f"[{p_c}]{p}[/{p_c}]", tr["skill"],
                       ", ".join(tr["for_members"]), tr.get("course_suggestion", "—"))
        console.print(Panel(tt, title="[bold yellow]Training Recommendations[/bold yellow]", border_style="yellow"))

    if report["hiring_recommendations"]:
        console.print(Panel(
            "\n".join(f"  [cyan]→[/cyan] {h}" for h in report["hiring_recommendations"]),
            title="[bold]Hiring Recommendations[/bold]", border_style="magenta"
        ))
    console.print(Panel(f"[italic]{report['overall_recommendation']}[/italic]",
                        title="[bold]Overall Recommendation[/bold]", border_style="dim"))
    console.print()

def main():
    validate_environment()
    if len(sys.argv) < 2:
        console.print("[dim]No file provided — using sample team data...[/dim]\n")
        data = SAMPLE_DATA
    else:
        with open(sys.argv[1]) as f:
            data = json.load(f)

    with console.status("[bold green]Analyzing skill gaps...[/bold green]"):
        report = analyze_gaps(data)
    display(data, report)

if __name__ == "__main__":
    main()
