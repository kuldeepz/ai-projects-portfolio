from datetime import datetime
from functools import wraps
import json
import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

"""
ADO Sprint Planner
Analyzes a product backlog (JSON) + team capacity/velocity and recommends
the optimal sprint composition with story point distribution.
"""

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"


def retry_with_backoff(max_attempts=3, base_delay=1, factor=2, retryable_exceptions=(Exception,)):
    def deco(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    last_exc = e
                    if attempt == max_attempts - 1:
                        break
                    delay = base_delay * (factor ** attempt)
                    time.sleep(delay)
            raise last_exc

        return wrapper

    return deco


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
                        "reason": {"type": "string"},
                    },
                    "required": ["id", "title", "story_points", "reason"],
                },
            },
            "deferred_items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "title": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["id", "title", "reason"],
                },
            },
            "total_points": {"type": "integer"},
            "capacity_utilization_pct": {"type": "integer"},
            "risks": {"type": "array", "items": {"type": "string"}},
            "recommendations": {"type": "array", "items": {"type": "string"}},
        },
        "required": [
            "sprint_goal",
            "recommended_items",
            "deferred_items",
            "total_points",
            "capacity_utilization_pct",
            "risks",
            "recommendations",
        ],
    },
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
    ],
}


def parse_export_arg(argv):
    args = argv[:]
    export_path = None

    for flag in ("--export", "-e"):
        while flag in args:
            i = args.index(flag)
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                export_path = args[i + 1]
                del args[i : i + 2]
            else:
                export_path = f"output_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
                del args[i]

    return args, export_path


@retry_with_backoff()
def plan_sprint(data: dict) -> dict:
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an experienced Scrum Master and AI sprint planner. "
                    "Select backlog items that fit within team capacity, respect dependencies, "
                    "prioritize critical bugs and high-value stories, and define a clear sprint goal."
                ),
            },
            {"role": "user", "content": f"Plan the sprint for this backlog:\n\n{json.dumps(data, indent=2)}"},
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
    console.print(
        Panel.fit(
            f"[bold]Sprint {data['sprint_number']} — Team {team['name']}[/bold]\n"
            f"[dim]Velocity: {team['velocity']}  |  Capacity: {team['capacity_this_sprint']} pts  |  Members: {team['members']}[/dim]\n"
            f"Utilization: [{color} bold]{util}%[/{color} bold]  ({plan['total_points']}/{team['capacity_this_sprint']} pts)",
            title="[bold cyan]Sprint Plan[/bold cyan]",
            border_style="cyan",
        )
    )
    console.print(Panel(f"[italic bold]{plan['sprint_goal']}[/italic bold]", title="[bold]Sprint Goal[/bold]"))


def export_output(filename: str, output: dict):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2)
    except OSError as e:
        console.print(f"[red]Failed to export JSON: {e}[/red]")


if __name__ == "__main__":
    args, export_path = parse_export_arg(sys.argv[1:])
    data = SAMPLE_BACKLOG
    plan = plan_sprint(data)
    display(data, plan)

    if export_path:
        output = {"input": data, "plan": plan}
        export_output(export_path, output)
