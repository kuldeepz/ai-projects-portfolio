"""
AI Model Evaluator
Runs a test suite (question/expected-answer pairs) against a prompt+model,
scores outputs, and produces an evaluation report.
"""

import os, sys, json
from datetime import datetime
from typing import Any
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
def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

EVAL_SCHEMA: dict[str, Any] = {
    "name": "eval_score",
    "description": "Evaluation of a single model output against expected answer",
    "parameters": {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "description": "Score 0-100"},
            "correctness": {"type": "string", "enum": ["correct", "partial", "incorrect"]},
            "reasoning": {"type": "string"},
            "key_missing": {"type": "array", "items": {"type": "string"}},
            "hallucination_detected": {"type": "boolean"}
        },
        "required": ["score", "correctness", "reasoning", "hallucination_detected"]
    }
}

SAMPLE_SUITE: dict[str, Any] = {
    "name": "Customer Support Bot Evaluation",
    "system_prompt": "You are a helpful customer support agent for an e-commerce company. Be concise, friendly, and accurate.",
    "test_cases": [
        {"id": "TC-01", "input": "How do I return a product?",
         "expected": "Mention 30-day return policy, initiate via account settings or email support"},
        {"id": "TC-02", "input": "Where is my order #12345?",
         "expected": "Ask for email to look up, explain tracking info is in confirmation email"},
        {"id": "TC-03", "input": "Do you ship internationally?",
         "expected": "Yes to 25 countries, 7-14 business days, additional customs fees may apply"},
        {"id": "TC-04", "input": "I want a refund for a damaged item",
         "expected": "Apologize, ask for photo evidence, offer replacement or full refund within 5 business days"},
        {"id": "TC-05", "input": "What's your phone number?",
         "expected": "No phone support, offer email and live chat alternatives"},
    ]
}


def validate_eval_result(data: dict[str, Any]) -> dict[str, Any]:
    required_keys = ["score", "correctness", "reasoning", "hallucination_detected"]
    missing = [k for k in required_keys if k not in data]
    if missing:
        raise ValueError(f"Evaluator output missing required keys: {missing}")

    score = data["score"]
    if not isinstance(score, int):
        raise TypeError("Evaluator output 'score' must be int")
    if score < 0 or score > 100:
        raise ValueError("Evaluator output 'score' must be between 0 and 100")

    correctness = data["correctness"]
    if correctness not in {"correct", "partial", "incorrect"}:
        raise ValueError("Evaluator output 'correctness' must be one of: correct, partial, incorrect")

    reasoning = data["reasoning"]
    if not isinstance(reasoning, str) or not reasoning.strip():
        raise TypeError("Evaluator output 'reasoning' must be a non-empty string")

    hallucination_detected = data["hallucination_detected"]
    if not isinstance(hallucination_detected, bool):
        raise TypeError("Evaluator output 'hallucination_detected' must be bool")

    if "key_missing" in data and not isinstance(data["key_missing"], list):
        raise TypeError("Evaluator output 'key_missing' must be a list when provided")

    return data


def validate_suite_schema(suite: dict[str, Any]) -> None:
    if not isinstance(suite.get("name"), str) or not suite["name"].strip():
        raise ValueError("suite.name must be a non-empty string")
    if not isinstance(suite.get("system_prompt"), str) or not suite["system_prompt"].strip():
        raise ValueError("suite.system_prompt must be a non-empty string")
    test_cases = suite.get("test_cases")
    if not isinstance(test_cases, list) or not test_cases:
        raise ValueError("suite.test_cases must be a non-empty list")
    for i, tc in enumerate(test_cases):
        if not isinstance(tc, dict):
            raise TypeError(f"test_cases[{i}] must be an object")
        for key in ("id", "input", "expected"):
            if not isinstance(tc.get(key), str) or not tc[key].strip():
                raise ValueError(f"test_cases[{i}].{key} must be a non-empty string")


def run_model(system_prompt: str, user_input: str) -> str:
    r = get_client().chat.completions.create(
        model=MODEL,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_input}],
        temperature=0.3,
    )
    content = r.choices[0].message.content
    if content is None:
        raise ValueError("Model returned null content")
    return content

def score_output(actual: str, expected: str, question: str) -> dict[str, Any]:
    r = get_client().chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": (
                "You are an LLM evaluator. Score how well the actual output matches the expected answer. "
                "Check for correctness, completeness, and hallucinations."
            )},
            {"role": "user", "content": (
                f"Question: {question}\nExpected: {expected}\nActual output: {actual}"
            )}
        ],
        tools=[{"type": "function", "function": EVAL_SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "eval_score"}},
        temperature=0.1,
    )
    parsed = json.loads(r.choices[0].message.tool_calls[0].function.arguments)
    return validate_eval_result(parsed)

def run_evaluation(suite: dict[str, Any]) -> dict[str, Any]:
    validate_suite_schema(suite)
    results: list[dict[str, Any]] = []
    for tc in track(suite["test_cases"], description="Evaluating..."):
        actual = run_model(suite["system_prompt"], tc["input"])
        score_result = score_output(actual, tc["expected"], tc["input"])
        results.append({**tc, "actual_output": actual, "eval": score_result})

    avg_score = sum(r["eval"]["score"] for r in results) / len(results)
    hallucinations = sum(1 for r in results if r["eval"]["hallucination_detected"])
    correct = sum(1 for r in results if r["eval"]["correctness"] == "correct")
    return {"suite_name": suite["name"], "model": MODEL, "run_at": datetime.now().isoformat(),
            "avg_score": round(avg_score, 1), "total": len(results),
            "correct": correct, "hallucinations": hallucinations, "results": results}

def display(report: dict[str, Any]) -> None:
    avg = report["avg_score"]
    color = "green" if avg >= 80 else "yellow" if avg >= 60 else "red"
    console.print()
    console.print(Panel.fit(
        f"[bold]{report['suite_name']}[/bold]  [dim]({report['model']})[/dim]\n"
        f"Avg Score: [{color} bold]{avg}/100[/{color} bold]  "
        f"Correct: [green]{report['correct']}/{report['total']}[/green]  "
        f"Hallucinations: [{'red' if report['hallucinations'] else 'green'}]{report['hallucinations']}[/{'red' if report['hallucinations'] else 'green'}]",
        title="[bold cyan]Evaluation Report[/bold cyan]", border_style="cyan"
    ))
    t = Table(show_header=True, header_style="bold", show_lines=True)
    t.add_column("ID", width=7); t.add_column("Question", ratio=2)
    t.add_column("Score", width=7); t.add_column("Verdict", width=12)
    t.add_column("Hallucination", width=13); t.add_column("Notes", ratio=2, style="dim")
    for r in report["results"]:
        e = r["eval"]
        sc = e["score"]
        sc_c = "green" if sc >= 80 else "yellow" if sc >= 60 else "red"
        corr_c = {"correct": "green", "partial": "yellow", "incorrect": "red"}[e["correctness"]]
        t.add_row(r["id"], r["input"][:50],
                  f"[{sc_c}]{sc}[/{sc_c}]",
                  f"[{corr_c}]{e['correctness']}[/{corr_c}]",
                  "[red]YES[/red]" if e["hallucination_detected"] else "[green]no[/green]",
                  e["reasoning"][:80])
    console.print(Panel(t, title="[bold]Test Case Results[/bold]", border_style="dim"))

    out = f"eval_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    console.print(f"\nSaved report: [bold]{out}[/bold]")


if __name__ == "__main__":
    suite = SAMPLE_SUITE
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            suite = json.load(f)
    report = run_evaluation(suite)
    display(report)
