from datetime import datetime
from functools import wraps
import json
import os
import sys
import time
from typing import Any, Callable, NotRequired, TypedDict

from dotenv import load_dotenv
from openai import APIConnectionError, APIError, APITimeoutError, OpenAI, RateLimitError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

"""
ADO Sprint Planner
Analyzes a product backlog (JSON) + team capacity/velocity and recommends
the optimal sprint composition with story point distribution.
"""


class Team(TypedDict):
    name: str
    velocity: int
    capacity_this_sprint: int
    members: int


class BacklogItem(TypedDict):
    id: str
    title: str
    priority: str
    story_points: int
    dependencies: list[str]


class Backlog(TypedDict):
    team: Team
    sprint_number: int
    items: list[BacklogItem]


class RecommendedItem(TypedDict):
    id: str
    title: str
    story_points: int
    reason: str


class DeferredItem(TypedDict):
    id: str
    title: str
    reason: str


class SprintPlan(TypedDict):
    sprint_goal: str
    recommended_items: list[RecommendedItem]
    deferred_items: list[DeferredItem]
    total_points: int
    capacity_utilization_pct: int
    risks: list[str]
    recommendations: list[str]


class JsonSchemaRef(TypedDict):
    type: str


class JsonSchemaProperty(TypedDict, total=False):
    type: str
    items: JsonSchemaRef | "JsonSchemaObject"
    properties: dict[str, "JsonSchemaProperty"]
    required: list[str]


class JsonSchemaObject(TypedDict):
    type: str
    properties: dict[str, JsonSchemaProperty]
    required: list[str]


class ToolFunction(TypedDict):
    name: str
    description: str
    parameters: JsonSchemaObject


class ToolSpec(TypedDict):
    type: str
    function: ToolFunction


class ExportOutput(TypedDict):
    generated_at: str
    model: str
    backlog: Backlog
    sprint_plan: SprintPlan


load_dotenv()
console: Console = Console()
MODEL: str = "gpt-4o-mini"

RETRYABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    APIError,
)


def retry_with_backoff(
    max_attempts: int = 3,
    base_delay: int = 1,
    factor: int = 2,
    retryable_exceptions: tuple[type[Exception], ...] = RETRYABLE_EXCEPTIONS,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def deco(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exc: Exception | None = None
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


_client: OpenAI | None = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


SCHEMA: ToolSpec = {
    "type": "function",
    "function": {
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
    },
}

SAMPLE_BACKLOG: Backlog = {
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


def parse_export_arg(argv: list[str]) -> tuple[list[str], str | None]:
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
def plan_sprint(data: Backlog) -> SprintPlan:
    with console.status("[bold green]Processing..."):
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
            tools=[SCHEMA],
        )
        tool_calls = response.choices[0].message.tool_calls or []
        if not tool_calls:
            raise ValueError("No tool call returned by model")
        args = tool_calls[0].function.arguments
        return json.loads(args)
