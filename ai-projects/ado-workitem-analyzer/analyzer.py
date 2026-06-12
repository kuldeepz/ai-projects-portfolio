"""
ADO Work Item Analyzer
Reads Azure DevOps work items (from JSON export or typed input) and:
- Flags missing/incomplete acceptance criteria
- Scores definition-of-ready completeness
- Suggests improvements to the work item
"""

import os, sys, json
from datetime import datetime
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

def print_usage(response):
    usage = response.usage
    prompt_tokens = usage.prompt_tokens
    completion_tokens = usage.completion_tokens
    total_tokens = usage.total_tokens
    cost = (prompt_tokens / 1000) * 0.000015 + (completion_tokens / 1000) * 0.00006
    console.print(f"📊 Tokens: {prompt_tokens} in + {completion_tokens} out = {total_tokens} total | 💰 Est. cost: ${cost:.4f}")

SCHEMA = {
    "name": "workitem_analysis",
    "description": "Analysis of an ADO work item for completeness and quality",
    "parameters": {
        "type": "object",
        "properties": {
            "ready_score": {"type": "integer", "description": "Definition-of-Ready score 0-100"},
            "missing_fields": {"type": "array", "items": {"type": "string"}, "description": "Fields that are absent or empty"},
            "acceptance_criteria_issues": {"type": "array", "items": {"type": "string"}, "description": "Problems with acceptance criteria"},
            "improved_acceptance_criteria": {"type": "string", "description": "Rewritten acceptance criteria in Given/When/Then BDD format"},
            "story_point_suggestion": {"type": "integer", "description": "Suggested story point estimate (Fibonacci: 1,2,3,5,8,13)"},
            "risks": {"type": "array", "items": {"type": "string"}, "description": "Risks or dependencies flagged"},
            "suggestions": {"type": "array", "items": {"type": "string"}, "description": "Actionable improvements to the work item"},
            "summary": {"type": "string"}
        },
        "required": ["ready_score", "missing_fields", "acceptance_criteria_issues",
                     "improved_acceptance_criteria", "story_point_suggestion", "risks", "suggestions", "summary"]
    }
}

SAMPLE_WORK_ITEM = {
    "id": "WI-1042",
    "type": "User Story",
    "title": "As a user I want to login",
    "description": "User should be able to login to the application",
    "acceptance_criteria": "Login works",
    "story_points": None,
    "priority": "Medium",
    "assigned_to": "",
    "sprint": "Sprint 14",
    "tags": []
}

def analyze_workitem(item: dict) -> dict:
    with console.status("[bold green]Calling OpenAI for analysis...[/bold green]"):
        response = get_client().chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": (
                    "You are a senior Agile coach and BA reviewing Azure DevOps work items. "
                    "Evaluate completeness, flag issues with acceptance criteria, and rewrite "
                    "acceptance criteria in Given/When/Then BDD format. Be specific and actionable."
                )},
                {"role": "user", "content": f"Analyze this work item:\n\n{json.dumps(item, indent=2)}"}
            ],
            tools=[{"type": "function", "function": SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "workitem_analysis"}},
            temperature=0.2,
        )
    print_usage(response)
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(item: dict, analysis: dict):
    score = analysis["ready_score"]
    color = "green" if score >= 75 else "yellow" if score >= 50 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]{item.get('id','?')} — {item.get('title','?')}[/bold]\n"
        f"[dim]{item.get('type','?')} · {item.get('sprint','')}[/dim]\n"
        f"Ready Score: [{color} bold]{score}/100[/{color} bold]",
        title="[bold cyan]ADO Work Item Analysis[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{analysis['summary']}[/italic]", title="Summary", border_style="dim"))

    if analysis["missing_fields"]:
        console.print(Panel("\n".join(f"  [red]✘[/red] {f}" for f in analysis["missing_fields"]),
                            title="[bold red]Missing Fields[/bold red]", border_style="red"))

    if analysis["acceptance_criteria_issues"]:
        console.print(Panel("\n".join(f"  [yellow]⚠[/yellow] {i}" for i in analysis["acceptance_criteria_issues"]),
                            title="[bold yellow]AC Issues[/bold yellow]", border_style="yellow"))

    console.print(Panel(
        f"[green]{analysis['improved_acceptance_criteria']}[/green]",
        title="[bold green]Improved Acceptance Criteria (BDD)[/bold green]", border_style="green"
    ))

    t = Table(show_header=False, box=None, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    t.add_row("Suggested Story Points", f"[bold]{analysis['story_point_suggestion']}[/bold]")
    console.print(Panel(t, title="Estimation", border_style="dim"))

    if analysis["risks"]:
        console.print(Panel("\n".join(f"  [red]⚡[/red] {r}" for r in analysis["risks"]),
                            title="[bold]Risks & Dependencies[/bold]", border_style="red"))

    console.print(Panel("\n".join(f"  [cyan]→[/cyan] {s}" for s in analysis["suggestions"]),
                        title="[bold]Improvement Suggestions[/bold]", border_style="blue"))
    console.print()

def main():
    export = False
    args = sys.argv[1:]
    if "--export" in args:
        export = True
        args.remove("--export")
    if "-e" in args:
        export = True
        args.remove("-e")

    if len(args) < 1:
        console.print("[yellow]Usage:[/yellow] python analyzer.py <workitem.json>")
        console.print("[dim]Running with built-in sample work item...[/dim]\n")
        item = SAMPLE_WORK_ITEM
    else:
        with console.status("[bold green]Loading work item JSON...[/bold green]"):
            with open(args[0], "r", encoding="utf-8") as f:
                item = json.load(f)

    analysis = analyze_workitem(item)
    display(item, analysis)

    if export:
        generated_at = datetime.now().isoformat()
        output = {
            "work_item": item,
            "analysis": analysis,
            "generated_at": generated_at,
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"output_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)


def _run_tests():
    import tempfile
    from unittest.mock import MagicMock, patch

    class _DummyStatus:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    # test: file input path enters load-status context
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tf:
        json.dump(SAMPLE_WORK_ITEM, tf)
        temp_path = tf.name

    try:
        with patch.object(console, "status", side_effect=lambda *_a, **_k: _DummyStatus()) as mock_status, \
             patch(__name__ + ".analyze_workitem", return_value={
                 "ready_score": 80,
                 "missing_fields": [],
                 "acceptance_criteria_issues": [],
                 "improved_acceptance_criteria": "Given X When Y Then Z",
                 "story_point_suggestion": 3,
                 "risks": [],
                 "suggestions": ["Do A"],
                 "summary": "Looks good"
             }), \
             patch(__name__ + ".display", MagicMock()), \
             patch.object(sys, "argv", ["analyzer.py", temp_path]):
            main()
            assert any("Loading work item JSON" in str(c) for c in mock_status.call_args_list)
    finally:
        os.unlink(temp_path)

    # test: sample path skips file-load status
    with patch.object(console, "status", side_effect=lambda *_a, **_k: _DummyStatus()) as mock_status, \
         patch(__name__ + ".analyze_workitem", return_value={
             "ready_score": 80,
             "missing_fields": [],
             "acceptance_criteria_issues": [],
             "improved_acceptance_criteria": "Given X When Y Then Z",
             "story_point_suggestion": 3,
             "risks": [],
             "suggestions": ["Do A"],
             "summary": "Looks good"
         }), \
         patch(__name__ + ".display", MagicMock()), \
         patch.object(sys, "argv", ["analyzer.py"]):
        main()
        assert not any("Loading work item JSON" in str(c) for c in mock_status.call_args_list)

    # test: API analysis path enters analysis-status once
    mock_response = MagicMock()
    mock_response.usage.prompt_tokens = 10
    mock_response.usage.completion_tokens = 5
    mock_response.usage.total_tokens = 15
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.tool_calls = [MagicMock()]
    mock_response.choices[0].message.tool_calls[0].function.arguments = json.dumps({
        "ready_score": 80,
        "missing_fields": [],
        "acceptance_criteria_issues": [],
        "improved_acceptance_criteria": "Given X When Y Then Z",
        "story_point_suggestion": 3,
        "risks": [],
        "suggestions": ["Do A"],
        "summary": "Looks good"
    })

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_response

    with patch.object(console, "status", side_effect=lambda *_a, **_k: _DummyStatus()) as mock_status, \
         patch(__name__ + ".get_client", return_value=mock_client):
        analyze_workitem(SAMPLE_WORK_ITEM)
        analysis_calls = [c for c in mock_status.call_args_list if "Calling OpenAI for analysis" in str(c)]
        assert len(analysis_calls) == 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        _run_tests()
        console.print("[green]All tests passed[/green]")
    else:
        main()
