"""
AI Unit Test Generator
Reads a Python source file and generates comprehensive pytest unit tests,
including happy paths, edge cases, and error conditions.
"""

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


def validate_environment():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        console.print("[red]Missing OPENAI_API_KEY.[/red] Set it in your environment or .env file.")
        sys.exit(1)

    if len(sys.argv) < 2:
        console.print("[yellow]Usage:[/yellow] python generator.py <source_file.py> [--framework pytest|unittest]")
        console.print("[dim]Example: python generator.py my_module.py[/dim]")
        sys.exit(1)

    source_path = sys.argv[1]
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
    covered_text = "\n".join(f"  [green]✔[/green] {fn}" for fn in result["functions_covered"])
    console.print(Panel(covered_text, title="[bold green]Functions Covered[/bold green]", border_style="green"))

    # Coverage notes
    console.print(Panel(
        result["coverage_notes"],
        title="[bold]Coverage Notes[/bold]",
        border_style="dim"
    ))

    # Setup requirements
    if result.get("setup_requirements"):
        reqs = "\n".join(f"  [yellow]pip install[/yellow] {r}" for r in result["setup_requirements"])
        console.print(Panel(reqs, title="[bold yellow]Additional Requirements[/bold yellow]", border_style="yellow"))

    console.print()


def main():
    global VERBOSE
    VERBOSE = "--verbose" in sys.argv or "-v" in sys.argv

    validate_environment()

    source_path = sys.argv[1]
    framework = "pytest"
    if "--framework" in sys.argv:
        idx = sys.argv.index("--framework")
        framework = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "pytest"

    if not os.path.exists(source_path):
        console.print(f"[red]File not found:[/red] {source_path}")
        sys.exit(1)

    with open(source_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    if not source_code.strip():
        console.print("[red]Source file is empty.[/red]")
        sys.exit(1)

    if len(source_code) > 8000:
        console.print("[yellow]Source truncated to 8000 characters.[/yellow]")
        source_code = source_code[:8000]

    module_name = Path(source_path).stem
    signatures = extract_function_signatures(source_code)

    console.print(f"\n[cyan]Generating tests for:[/cyan] {source_path}")
    console.print(f"[cyan]Framework:[/cyan] {framework}")
    if signatures:
        console.print(f"[cyan]Detected:[/cyan] {', '.join(signatures[:5])}{'...' if len(signatures) > 5 else ''}")

    with console.status("[bold green]Generating test suite...[/bold green]"):
        result = generate_tests(source_code, module_name, framework)

    # Write test file
    output_file = f"test_{module_name}.py"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(result["test_file_content"])

    display_summary(result, output_file)

    # Show a preview
    console.print(Panel(
        Syntax(result["test_file_content"][:2000] + ("\n..." if len(result["test_file_content"]) > 2000 else ""),
               "python", theme="monokai", line_numbers=True),
        title=f"[bold]Preview: {output_file}[/bold]",
        border_style="cyan"
    ))


if __name__ == "__main__":
    main()
