"""
SQL Query Generator
Converts natural language questions into SQL queries.
Supports schema-aware generation and multiple SQL dialects.
"""

import os
import sys
import json
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.prompt import Prompt, Confirm
from rich.table import Table

load_dotenv()

console = Console()
CHAT_MODEL = "gpt-4o-mini"

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Missing OPENAI_API_KEY.[/red] Set it in your environment or .env file.")
        sys.exit(1)

    file_paths = []
    for arg in sys.argv[1:]:
        if arg.startswith("--schema="):
            file_paths.append(arg.split("=", 1)[1])

    for i, arg in enumerate(sys.argv[1:]):
        if arg == "--schema" and i + 2 <= len(sys.argv[1:]):
            file_paths.append(sys.argv[1:][i + 1])

    for path_str in file_paths:
        path = Path(path_str)
        if not path.exists():
            console.print(f"[red]File not found:[/red] {path_str}")
            sys.exit(1)
        if not path.is_file():
            console.print(f"[red]Not a file:[/red] {path_str}")
            sys.exit(1)
        if not os.access(path, os.R_OK):
            console.print(f"[red]File is not readable:[/red] {path_str}")
            sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")


DIALECTS = {
    "1": "PostgreSQL",
    "2": "MySQL",
    "3": "SQLite",
    "4": "SQL Server (T-SQL)",
    "5": "BigQuery (Standard SQL)",
    "6": "Snowflake",
}

SQL_SCHEMA = {
    "name": "sql_result",
    "description": "Generated SQL query with explanation",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "The generated SQL query, properly formatted"},
            "explanation": {"type": "string", "description": "Plain English explanation of what the query does"},
            "assumptions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Assumptions made about the schema or data"
            },
            "alternatives": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string"},
                        "query": {"type": "string"}
                    },
                    "required": ["description", "query"]
                },
                "description": "1-2 alternative approaches if applicable"
            },
            "performance_notes": {"type": "string", "description": "Index recommendations or performance considerations"},
            "dialect_specific_notes": {"type": "string", "description": "Any dialect-specific syntax notes"}
        },
        "required": ["query", "explanation", "assumptions"]
    }
}


def generate_sql(question: str, schema: str, dialect: str, history: list[dict]) -> dict:
    schema_section = f"\n\nDatabase Schema:\n```sql\n{schema}\n```" if schema else ""

    system_prompt = (
        f"You are an expert SQL developer. Generate correct, efficient {dialect} SQL queries "
        f"from natural language questions. Format SQL with proper indentation. "
        f"Use CTEs for complex queries. Add comments for non-obvious logic."
    )

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history[-6:])
    messages.append({
        "role": "user",
        "content": f"Question: {question}{schema_section}"
    })

    with console.status("[bold green]Processing..."):
        response = get_client().chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            tools=[{"type": "function", "function": SQL_SCHEMA}],
            tool_choice={"type": "function", "function": {"name": "sql_result"}},
            temperature=0.1,
        )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)


def display_result(result: dict, dialect: str):
    console.print()
    console.print(Panel(
        Syntax(result["query"], "sql", theme="monokai", line_numbers=True),
        title=f"[bold cyan]Generated {dialect} Query[/bold cyan]",
        border_style="cyan"
    ))

    console.print(Panel(
        result["explanation"],
        title="[bold]What This Query Does[/bold]",
        border_style="dim"
    ))

    if result.get("assumptions"):
        text = "\n".join(f"  [yellow]•[/yellow] {a}" for a in result["assumptions"])
        console.print(Panel(text, title="[bold yellow]Assumptions[/bold yellow]", border_style="yellow"))

    if result.get("performance_notes"):
        console.print(Panel(
            result["performance_notes"],
            title="[bold]Performance Notes[/bold]",
            border_style="blue"
        ))

    if result.get("alternatives"):
        for alt in result["alternatives"]:
            console.print(Panel(
                f"[dim]{alt['description']}[/dim]\n\n" +
                Syntax(alt["query"], "sql", theme="monokai").highlight(alt["query"]),
                title="[bold dim]Alternative Approach[/bold dim]",
                border_style="dim"
            ))

    if result.get("dialect_specific_notes"):
        console.print(Panel(
            result["dialect_specific_notes"],
            title=f"[bold]{dialect} Notes[/bold]",
            border_style="dim"
        ))

    console.print()


def load_schema(schema_path: str) -> str:
    if not os.path.exists(schema_path):
        console.print(f"[red]Schema file not found:[/red] {schema_path}")
        sys.exit(1)
    with console.status("[bold green]Processing..."):
        with open(schema_path) as f:
            return f.read()


def interactive_mode():
    console.print(Panel.fit(
        "[bold cyan]SQL Query Generator[/bold cyan]\n"
        "Convert natural language to production-ready SQL",
        border_style="cyan"
    ))


def main():
    with console.status("[bold green]Processing..."):
        validate_environment()
    interactive_mode()


if __name__ == "__main__":
    main()
