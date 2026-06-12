"""
AI Unit Test Generator
Reads a Python source file and generates comprehensive pytest unit tests,
including happy paths, edge cases, and error conditions.
"""

import argparse
import os
import sys
import ast
import json
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

load_dotenv()

console = Console()
CHAT_MODEL = "gpt-4o-mini"
VERBOSE = False

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def parse_args():
    parser = argparse.ArgumentParser(description="Generate unit tests for a Python source file.")
    parser.add_argument("source_file", help="Path to the Python source file")
    parser.add_argument("--framework", choices=["pytest", "unittest"], default="pytest")
    parser.add_argument("-v", "--verbose", action="store_true")
    return parser.parse_args()


def validate_environment(source_path: str):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Missing OPENAI_API_KEY.[/red] Set it in your environment or .env file.")
        sys.exit(1)

    path = Path(source_path)
    if not path.exists():
        console.print(f"[red]File not found:[/red] {source_path}")
        sys.exit(1)
    if not path.is_file():
        console.print(f"[red]Path is not a file:[/red] {source_path}")
        sys.exit(1)
    if not os.access(path, os.R_OK):
        console.print(f"[red]File is not readable:[/red] {source_path}")
        sys.exit(1)

    console.print("[green]Setup OK ✓[/green]")


TEST_SCHEMA = {
    "name": "test_output",
    "description": "Generated pytest test suite",
    "parameters": {
        "type": "object",
        "properties": {
            "test_file_content": {
                "type": "string",
                "description": "Complete pytest test file content, ready to run"
            },
            "functions_covered": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of function/method names covered by tests"
            },
            "test_count": {"type": "integer", "description": "Total number of test functions generated"},
            "coverage_notes": {
                "type": "string",
                "description": "Notes on what's covered and what's not testable without external dependencies"
            },
            "setup_requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Any additional packages needed to run the tests (e.g., pytest-mock)"
            }
        },
        "required": ["test_file_content", "functions_covered", "test_count", "coverage_notes"]
    }
}


def extract_function_signatures(source_code: str) -> list[str]:
    """Parse the AST to extract all top-level function and class method signatures."""
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    signatures = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [arg.arg for arg in node.args.args if arg.arg != "self"]
            sig = f"{node.name}({', '.join(args)})"
            signatures.append(sig)
        elif isinstance(node, ast.ClassDef):
            signatures.append(f"class {node.name}")
    return signatures


def generate_tests(source_code: str, module_name: str, framework: str = "pytest") -> dict:
    system_content = (
        f"You are a senior Python engineer who writes thorough {framework} test suites. "
        "For each function/method: write happy path tests, edge cases (empty input, None, "
        "boundary values), and error condition tests. "
        "Use pytest.mark.parametrize for multiple similar cases. "
        "Mock external dependencies (I/O, network, database). "
        "Write self-contained tests — each test should be independent. "
        "Include docstrings explaining what each test validates."
    )
    user_content = (
        f"Generate a complete {framework} test file for this module "
        f"(module name: {module_name}):\n\n```python\n{source_code}\n```"
    )

    if VERBOSE:
        console.print(f"[dim]Model:[/dim] {CHAT_MODEL}")
        total_chars = len(system_content) + len(user_content)
        approx_tokens = total_chars // 4
        console.print(f"[dim]Input size:[/dim] {total_chars} chars (~{approx_tokens} tokens)")
        console.print("⏳ Calling OpenAI API...")

    start_time = time.time()
    response = get_client().chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {
                "role": "system",
                "content": system_content
            },
            {
                "role": "user",
                "content": user_content
            }
        ],
        tools=[{"type": "function", "function": TEST_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "test_output"}},
        temperature=0.2,
        max_tokens=4096,
    )
    elapsed = time.time() - start_time
    if VERBOSE:
        console.print(f"✅ Done in {elapsed:.1f}s")
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)


def display_summary(result: dict, output_file: str):
    console.print()

    # Stats table
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="dim")
    table.add_column(style="bold white")
    table.add_row("Tests generated", str(result["test_count"]))
    table.add_row("Functions covered", str(len(result["functions_covered"])))
    table.add_row("Output file", output_file)
    console.print(Panel(table, title="[bold cyan]Test Generation Summary[/bold cyan]", border_style="cyan"))

    # Functions covered
    co
