"""
ADO Sprint Planner
Analyzes a product backlog (JSON) + team capacity/velocity and recommends
the optimal sprint composition with story point distribution.
"""

import os, sys, json, time
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

def retry_with_backoff(func):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for i, delay in enumerate(delays):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if i == len(delays) - 1:
                    break
                time.sleep(delay)
        raise last_exc
    return wrapper

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

SCHEMA = {
    "name": "sprint_plan",
    "description": "AI-generated sprint plan",
    "parameters": {
        "type": "object",
        "properties": {
            "sprint_goal": {"type": "string"},
            "recommended_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "story_points": {"type": "integer"},
                        "reason": {"type": "string"}
                    },
                    "required": ["id", "title", "story_points", "reason"]
                }
            },
            "deferred_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {"id": {"type": "string"}, "title": {"type": "string"}, "reason": {"type": "string"}},
                    "required": ["id", "title", "reason"]
                }
            },
            "total_points": {"type": "integer"},
            "capacity_utilization_pct": {"type": "integer"},
            "risks": {"type": "array", "items": {"type": "string"}},
            "recommendations": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["sprint_goal", "recommended_items", "deferred_items",
                     "total_points", "capacity_utilization_pct", "risks", "recommendations"]
    }
}

SAMPLE_BACKLOG = {
    "team": {"name": "Phoenix", "velocity": 40, "capacity_this_sprint": 36, "members": 5},
    "sprint_number": 15,
    "items": [
        {"id": "US-101", "title": "User authentication with MFA", "priority": "Critical", "story_points": 8, "dependencies": []},
        {"id": "US-102", "title": "Dashboard redesign", "priority": "High", "story_points": 13, "dependencies": []},
        {"id": "US-103", "title": "Export reports to PDF", "priority": "High", "story_points": 5, "dependencies": ["US-102"]},
        {"id": "US-104", "title": "Email notification service", "priority": "Medium", "story_points": 8, "dependencies": []},
        {"id": "BUG-55", "title": "Fix login redirect on mobile", "priority": "Critical", "story_points": 3, "dependencies": []},
        {"id": "US-105", "title": "Admin user management panel", "priority": "Medium", "story_points": 13, "dependencies": ["US-101"]},
        {"id": "US-106", "title": "API rate limiting", "priority": "Low", "story_points": 5, "dependencies": []},
        {"id": "TECH-12", "title": "Upgrade React to v18", "priority": "Low", "story_points": 8, "dependencies": []},
    ]
}

@retry_with_backoff
def plan_sprint(data: dict) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are an experienced Scrum Master and AI sprint planner. "
                "Select backlog items that fit within team capacity, respect dependencies, "
                "prioritize critical bugs and high-value stories, and define a clear sprint goal."
            )},
            {"role": "user", "content": f"Plan the sprint for this backlog:\n\n{json.dumps(data, indent=2)}"}
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "sprint_plan"}},
        temperature=0.2,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def display(data: dict, plan: dict):
    team = data["team"]
    util = plan["capacity_utilization_pct"]
    color = "green" if util <= 95 else "yellow" if util <= 105 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]Sprint {data['sprint_number']} — Team {team['name']}[/bold]\n"
        f"[dim]Velocity: {team['velocity']}  |  Capacity: {team['capacity_this_sprint']} pts  |  Members: {team['members']}[/dim]\n"
        f"Utilization: [{color} bold]{util}%[/{color} bold]  ({plan['total_points']}/{team['capacity_this_sprint']} pts)",
        title="[bold cyan]Sprint Plan[/bold cyan]", border_style="cyan"
    ))
    console.print(Panel(f"[italic bold]{plan['sprint_goal']}[/italic bold]", title="[bold]Sprint Goal[/bold]", border_style="green"))

    t = Table(show_header=True, header_style="bold green")
    t.add_column("ID"); t.add_column("Title", ratio=2); t.add_column("Pts", width=5); t.add_column("Why", ratio=2, style="dim")
    for item in plan["recommended_items"]:
        t.add_row(item["id"], item["title"], str(item["story_points"]), item["reason"])
    console.print(Panel(t, title=f"[bold green]Recommended for Sprint ({plan['total_points']} pts)[/bold green]", border_style="green"))

    if plan["deferred_items"]:
        dt = Table(show_header=True, header_style="bold dim")
        dt.add_column("ID"); dt.add_column("Title", ratio=2); dt.add_column("Reason", ratio=2, style="dim")
        for item in plan["deferred_items"]:
            dt.add_row(item["id"], item["title"], item["reason"])
        console.print(Panel(dt, title="[bold]Deferred Items[/bold]", border_style="yellow"))


def main():
    export = "--export" in sys.argv

    data = SAMPLE_BACKLOG
    plan = plan_sprint(data)
    display(data, plan)

    if export:
        filename = f"sprint_plan_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)
        console.print(f"[green]Exported plan to {filename}[/green]")


if __name__ == "__main__":
    main()
