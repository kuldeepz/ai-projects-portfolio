"""
AI Model Evaluator
Runs a test suite (question/expected-answer pairs) against a prompt+model,
scores outputs, and produces an evaluation report.
"""

import os, json, sys
from datetime import datetime
from typing import Any, Literal, TypedDict, cast
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import track

load_dotenv()
console: Console = Console()
MODEL: str = "gpt-4o-mini"

_client: OpenAI | None = None


class EvalSchema(TypedDict):
    name: str
    description: str
    parameters: dict[str, Any]


class TestCase(TypedDict):
    id: str
    input: str
    expected: str


class EvalResult(TypedDict, total=False):
    score: int
    correctness: Literal["correct", "partial", "incorrect"]
    reasoning: str
    key_missing: list[str]
    hallucination_detected: bool


class Suite(TypedDict):
    name: str
    system_prompt: str
    test_cases: list[TestCase]


class EvaluatedCase(TestCase):
    actual_output: str
    eval: EvalResult


class EvaluationReport(TypedDict):
    suite_name: str
    model: str
    run_at: str
    avg_score: float
    total: int
    correct: int
    partial: int
    incorrect: int
    hallucinations: int
    results: list[EvaluatedCase]


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client


def validate_environment() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key is None or api_key.strip() == "":
        console.print(
            "[red]Setup error:[/red] OPENAI_API_KEY is not set or is empty. "
            "Set it in your environment or .env file."
        )
        raise SystemExit(1)

    for arg in sys.argv[1:]:
        if arg.startswith("-"):
            continue
        if os.path.exists(arg):
            if not os.path.isfile(arg):
                console.print(
                    f"[red]Setup error:[/red] Path exists but is not a file: {arg}"
                )
                raise SystemExit(1)
            if not os.access(arg, os.R_OK):
                console.print(
                    f"[red]Setup error:[/red] File is not readable: {arg}"
                )
                raise SystemExit(1)

    console.print("[green]Setup OK ✓[/green]")


EVAL_SCHEMA: EvalSchema = {
    "name": "eval_score",
    "description": "Evaluation of a single model output against expected answer",
    "parameters": {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "description": "Score 0-100"},
            "correctness": {
                "type": "string",
                "enum": ["correct", "partial", "incorrect"],
            },
            "reasoning": {"type": "string"},
            "key_missing": {"type": "array", "items": {"type": "string"}},
            "hallucination_detected": {"type": "boolean"},
        },
        "required": ["score", "correctness", "reasoning", "hallucination_detected"],
    },
}

SAMPLE_SUITE: Suite = {
    "name": "Customer Support Bot Evaluation",
    "system_prompt": "You are a helpful customer support agent for an e-commerce company. Be concise, friendly, and accurate.",
    "test_cases": [
        {
            "id": "TC-01",
            "input": "How do I return a product?",
            "expected": "Mention 30-day return policy, initiate via account settings or email support",
        },
        {
            "id": "TC-02",
            "input": "Where is my order #12345?",
            "expected": "Ask for email to look up, explain tracking info is in confirmation email",
        },
        {
            "id": "TC-03",
            "input": "Do you ship internationally?",
            "expected": "Yes to 25 countries, 7-14 business days, additional customs fees may apply",
        },
        {
            "id": "TC-04",
            "input": "I want a refund for a damaged item",
            "expected": "Apologize, ask for photo evidence, offer replacement or full refund within 5 business days",
        },
        {
            "id": "TC-05",
            "input": "What's your phone number?",
            "expected": "No phone support, offer email and live chat alternatives",
        },
    ],
}


def run_model(system_prompt: str, user_input: str) -> str:
    r = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input},
        ],
        temperature=0.3,
    )
    content = r.choices[0].message.content
    if content is None:
        raise ValueError("Model returned null content")
    return content


def _validate_score_payload(payload: dict[str, Any]) -> EvalResult:
    required_types: dict[str, type] = {
        "score": int,
        "correctness": str,
        "reasoning": str,
        "hallucination_detected": bool,
    }

    for key, expected_type in required_types.items():
        if key not in payload:
            raise ValueError(f"Missing required eval key: {key}")
        if not isinstance(payload[key], expected_type):
            raise ValueError(
                f"Invalid type for '{key}': expected {expected_type.__name__}"
            )

    if payload["correctness"] not in {"correct", "partial", "incorrect"}:
        raise ValueError("Invalid correctness value")

    if "key_missing" in payload and not (
        isinstance(payload["key_missing"], list)
        and all(isinstance(x, str) for x in payload["key_missing"])
    ):
        raise ValueError("Invalid key_missing value")

    return cast(EvalResult, payload)


def score_output(actual: str, expected: str, question: str) -> EvalResult:
    r = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are an LLM evaluator. Score how well the actual output matches the expected answer. "
                    "Check for correctness, completeness, and hallucinations."
                ),
            },
            {
                "role": "user",
                "content": f"Question: {question}\nExpected: {expected}\nActual output: {actual}",
            },
        ],
        tools=[{"type": "function", "function": EVAL_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "eval_score"}},
        temperature=0.1,
    )
    tool_calls = r.choices[0].message.tool_calls
    if not tool_calls:
        raise ValueError("Evaluator did not return tool call arguments")
    parsed = json.loads(tool_calls[0].function.arguments)
    if not isinstance(parsed, dict):
        raise ValueError("Evaluator tool-call arguments must be a JSON object")
    return _validate_score_payload(parsed)


def run_evaluation(suite: Suite) -> EvaluationReport:
    results: list[EvaluatedCase] = []
    for tc in track(suite["test_cases"], description="Evaluating..."):
        actual = run_model(suite["system_prompt"], tc["input"])
        score_result = score_output(actual, tc["expected"], tc["input"])
        results.append({**tc, "actual_output": actual, "eval": score_result})

    avg_score = sum(r["eval"]["score"] for r in results) / len(results)
    hallucinations = sum(1 for r in results if r["eval"]["hallucination_detected"])
    correct = sum(1 for r in results if r["eval"]["correctness"] == "correct")
    partial = sum(1 for r in results if r["eval"]["correctness"] == "partial")
    incorrect = sum(1 for r in results if r["eval"]["correctness"] == "incorrect")
    return {
        "suite_name": suite["name"],
        "model": MODEL,
        "run_at": datetime.now().isoformat(),
        "avg_score": round(avg_score, 1),
        "total": len(results),
        "correct": correct,
        "partial": partial,
        "incorrect": incorrect,
        "hallucinations": hallucinations,
        "results": results,
    }


def display(report: EvaluationReport) -> None:
    summary = Table(title="Evaluation Summary")
    summary.add_column("Metric")
    summary.add_column("Value")
    summary.add_row("Suite", report["suite_name"])
    summary.add_row("Model", report["model"])
    summary.add_row("Run At", report["run_at"])
    summary.add_row("Average Score", str(report["avg_score"]))
    summary.add_row("Total", str(report["total"]))
    summary.add_row("Correct", str(report["correct"]))
    summary.add_row("Partial", str(report["partial"]))
    summary.add_row("Incorrect", str(report["incorrect"]))
    summary.add_row("Hallucinations", str(report["hallucinations"]))
    console.print(summary)

    for r in report["results"]:
        console.print(
            Panel(
                f"[bold]{r['id']}[/bold]\n"
                f"Q: {r['input']}\n"
                f"Expected: {r['expected']}\n"
                f"Actual: {r['actual_output']}\n"
                f"Score: {r['eval']['score']} ({r['eval']['correctness']})\n"
                f"Reasoning: {r['eval']['reasoning']}",
                title="Test Case",
            )
        )


def main() -> None:
    validate_environment()
    report = run_evaluation(SAMPLE_SUITE)
    display(report)


if __name__ == "__main__":
    main()
