"""
ADO Test Case Generator
Takes a user story (text or JSON) and generates comprehensive BDD test cases
covering happy paths, edge cases, and negative scenarios.
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
    "name": "test_cases",
    "description": "Test cases generated from a user story",
    "parameters": {
        "type": "object",
        "properties": {
            "story_summary": {"type": "string"},
            "test_cases": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "type": {"type": "string", "enum": ["happy_path", "edge_case", "negative", "security", "performance"]},
                        "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                        "given": {"type": "string"},
                        "when": {"type": "string"},
                        "then": {"type": "string"},
                        "test_data": {"type": "string"},
                        "automation_candidate": {"type": "boolean"}
                    },
                    "required": ["id", "title", "type", "priority", "given", "when", "then", "automation_candidate"]
                }
            },
            "coverage_summary": {"type": "string"},
            "missing_scenarios": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["story_summary", "test_cases", "coverage_summary"]
    }
}

SAMPLE_STORY = {
    "id": "US-101",
    "title": "Multi-factor authentication for login",
    "description": "As a registered user, I want to enable MFA on my account so that my account is more secure.",
    "acceptance_criteria": (
        "- User can enable MFA from account settings\n"
        "- System sends OTP via email or SMS\n"
        "- OTP expires after 5 minutes\n"
        "- User can disable MFA\n"
        "- Failed OTP attempts are limited to 3 before lockout"
    )
}

def generate_test_cases(story: dict) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are a senior QA engineer. Generate comprehensive test cases in BDD format "
                "(Given/When/Then) covering: happy paths, edge cases, negative tests, security tests, "
                "and performance considerations. Assign realistic test data where relevant."
            )},
            {"role": "user", "content": f"Generate test cases for this user story:\n\n{json.dumps(story, indent=2)}"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "test_cases"}},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

TYPE_COLORS = {
    "happy_path": "green", "edge_case": "yellow", "negative": "red",
    "security": "magenta", "performance": "blue"
}
PRIORITY_COLORS = {"critical": "bold red", "high": "red", "medium": "yellow", "low": "dim"}

def display(story: dict, result: dict):
    console.print()
    console.print(Panel.fit(
        f"[bold]{story.get('id','?')} — {story.get('title','?')}[/bold]\n"
        f"[dim]{len(result['test_cases'])} test cases generated[/dim]",
        title="[bold cyan]Test Case Generator[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic]{result['coverage_summary']}[/italic]", title="Coverage Summary", border_style="dim"))

    for tc in result["test_cases"]:
        tc_color = TYPE_COLORS.get(tc["type"], "white")
        p_color = PRIORITY_COLORS.get(tc["priority"], "white")
        body = (
            f"  [{p_color}]●[/{p_color}] [{tc_color}]{tc['type'].replace('_',' ').title()}[/{tc_color}]"
            f"{'  [green]⚡ Auto[/green]' if tc['automation_candidate'] else ''}\n\n"
            f"  [dim]Given[/dim]  {tc['given']}\n"
            f"  [dim]When [/dim]  {tc['when']}\n"
            f"  [dim]Then [/dim]  {tc['then']}"
        )
        if tc.get("test_data"):
            body += f"\n  [dim]Data:[/dim]   {tc['test_data']}"
        console.print(Panel(body, title=f"[bold]{tc['id']}[/bold] — {tc['title']}", border_style=tc_color))

    if result.get("missing_scenarios"):
        console.print(Panel(
            "\n".join(f"  [yellow]•[/yellow] {s}" for s in result["missing_scenarios"]),
            title="[bold yellow]Scenarios to Consider Adding[/bold yellow]", border_style="yellow"
        ))
    console.print()

def main():
    if len(sys.argv) < 2:
        console.print("[dim]No file provided — using sample user story...[/dim]\n")
        story = SAMPLE_STORY
    else:
        with open(sys.argv[1]) as f:
            story = json.load(f)

    with console.status("[bold green]Generating test cases...[/bold green]"):
        result = generate_test_cases(story)
    display(story, result)

if __name__ == "__main__":
    main()
