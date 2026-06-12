"""
Standup Report Generator
Converts raw bullet notes into polished standup / status reports
for daily standups, weekly syncs, or executive status updates.
"""

import os, sys, json, argparse, time
from datetime import date, datetime
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"
VERBOSE = False

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

def retry_with_backoff(fn):
    def wrapper(*args, **kwargs):
        delays = [1, 2, 4]
        last_exc = None
        for i in range(len(delays) + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_exc = e
                if i < len(delays):
                    time.sleep(delays[i])
                else:
                    raise last_exc
    return wrapper

FORMATS = {
    "1": ("standup", "Daily standup (Yesterday / Today / Blockers)"),
    "2": ("weekly", "Weekly status report (Accomplishments / Plan / Risks)"),
    "3": ("executive", "Executive summary (Business impact, concise, non-technical)"),
    "4": ("slack", "Slack-style update (short, emoji-friendly, bullet points)"),
}

SCHEMA = {
    "name": "report_output",
    "description": "Generated status report",
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "formatted_report": {"type": "string", "description": "The complete formatted report in markdown"},
            "key_highlights": {"type": "array", "items": {"type": "string"}, "description": "Top 2-3 highlights for quick skim"},
            "blockers_summary": {"type": "string"},
            "tone_notes": {"type": "string"}
        },
        "required": ["title", "formatted_report", "key_highlights"]
    }
}

SAMPLE_NOTES = {
    "name": "Kuldeep Rao",
    "role": "AI Lead",
    "date": str(date.today()),
    "format": "standup",
    "raw_notes": [
        "finished the prompt library POC",
        "reviewed 3 PRs for the ML team",
        "fixed the embedding cache bug in prod",
        "today: working on ADO integration for sprint planner",
        "today: meeting with stakeholders at 2pm to demo the AI code reviewer",
        "blocker: waiting on infra team to provision GPU quota for fine-tuning job",
        "risk: sprint planner needs ADO API access — ticket with IT raised"
    ]
}

@retry_with_backoff
def _create_chat_completion(**kwargs):
    return get_client().chat.completions.create(**kwargs)

def generate_report(data: dict) -> dict:
    fmt = data.get("format", "standup")
    fmt_desc = next((v[1] for v in FORMATS.values() if v[0] == fmt), fmt)
    messages = [
        {"role": "system", "content": (
            f"You are a professional technical writer. Transform raw bullet notes into a polished "
            f"{fmt_desc}. Keep it concise, professional, and well-structured in markdown. "
            f"For standup: use Yesterday / Today / Blockers sections. "
            f"For executive: focus on business impact, skip technical jargon. "
            f"For Slack: use emojis sparingly, keep it scannable."
        )},
        {"role": "user", "content": (
            f"Name: {data.get('name','')}, Role: {data.get('role','')}, Date: {data.get('date','')}\n"
            f"Raw notes:\n" + "\n".join(f"- {n}" for n in data.get("raw_notes", []))
        )}
    ]
    if VERBOSE:
        total_chars = sum(len(m["content"]) for m in messages)
        est_tokens = int(total_chars / 4)
        console.print(f"[dim]Model:[/dim] {MODEL}")
        console.print(f"[dim]Input size:[/dim] {total_chars} chars (~{est_tokens} tokens)")
        console.print("⏳ Calling OpenAI API...")
        start = time.perf_counter()
    response = _create_chat_completion(
        model=MODEL,
        messages=messages,
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "report_output"}},
        temperature=0.4,
    )
    if VERBOSE:
        elapsed = time.perf_counter() - start
        console.print(f"✅ Done in {elapsed:.1f}s")
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", nargs="?")
    parser.add_argument("--export", "-e", choices=["json"])
    parser.add_argument("--export-out", default=None)
    parser.add_argument("--verbose", "-v", action="store_true")
    parsed = parser.parse_args()

    global VERBOSE
    VERBOSE = parsed.verbose

    if not parsed.input_file:
        console.print("[dim]No file provided — using sample notes...[/dim]\n")
        data = SAMPLE_NOTES
    else:
        with open(parsed.input_file) as f:
            data = json.load(f)

    with console.status("[bold green]Generating report...[/bold green]"):
        report = generate_report(data)

    console.print()
    console.print(Panel(Markdown(report["formatted_report"]),
                        title=f"[bold cyan]{report['title']}[/bold cyan]",
                        border_style="cyan", padding=(1, 2)))

    if report["key_highlights"]:
        console.print(Panel(
            "\n".join(f"  [cyan]★[/cyan] {h}" for h in report["key_highlights"]),
            title="[bold]Key Highlights[/bold]", border_style="dim"
        ))

    out = f"standup_{date.today().isoformat()}.md"
    with open(out, "w") as f:
        f.write(report["formatted_report"])
    console.print(f"\n[green]Saved:[/green] {out}\n")

    if parsed.export == "json":
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        export_out = parsed.export_out or f"output_{timestamp}.json"
        export_data = dict(report)
        export_data["generated_at"] = now.isoformat()
        with open(export_out, "w") as f:
            json.dump(export_data, f, indent=2)
        console.print(f"[green]Exported:[/green] {export_out}\n")

if __name__ == "__main__":
    main()


# -----------------------------
# CLI tests for export behavior
# -----------------------------
import unittest
import tempfile
from unittest.mock import patch


class TestCLIExportBehavior(unittest.TestCase):
    def _fake_report(self):
        return {
            "title": "Daily Standup",
            "formatted_report": "# Update\n- Did things",
            "key_highlights": ["Did things"],
            "blockers_summary": "None",
            "tone_notes": "Professional",
        }

    def test_verbose_flag_sets_verbose_mode(self):
        global VERBOSE
        VERBOSE = False
        with patch.object(sys, "argv", ["standup.py", "-v"]), \
             patch(__name__ + ".generate_report", return_value=self._fake_report()), \
             patch("builtins.open", unittest.mock.mock_open()):
            main()
        self.assertTrue(VERBOSE)

    def test_generate_report_verbose_prints_diagnostics(self):
        global VERBOSE
        VERBOSE = True

        fake_args = json.dumps(self._fake_report())

        class _Fn:
            arguments = fake_args

        class _ToolCall:
            function = _Fn()

        class _Msg:
            tool_calls = [_ToolCall()]

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        class _Completions:
            def create(self, **kwargs):
                return _Resp()

        class _Chat:
            completions = _Completions()

        class _Client:
            chat = _Chat()

        with patch(__name__ + ".get_client", return_value=_Client()), \
             patch.object(console, "print") as mock_print:
            generate_report(SAMPLE_NOTES)

        printed = "\n".join(" ".join(str(a) for a in call.args) for call in mock_print.call_args_list)
        self.assertIn("Model:", printed)
        self.assertIn("Input size:", printed)
        self.assertIn("Calling OpenAI API", printed)
        self.assertIn("Done in", printed)

    def test_generate_report_non_verbose_suppresses_diagnostics(self):
        global VERBOSE
        VERBOSE = False

        fake_args = json.dumps(self._fake_report())

        class _Fn:
            arguments = fake_args

        class _ToolCall:
            function = _Fn()

        class _Msg:
            tool_calls = [_ToolCall()]

        class _Choice:
            message = _Msg()

        class _Resp:
            choices = [_Choice()]

        class _Completions:
            def create(self, **kwargs):
                return _Resp()

        class _Chat:
            completions = _Completions()

        class _Client:
            chat = _Chat()

        with patch(__name__ + ".get_client", return_value=_Client()), \
             patch.object(console, "print") as mock_print:
            generate_report(SAMPLE_NOTES)

        printed = "\n".join(" ".join(str(a) for a in call.args) for call in mock_print.call_args_list)
        self.assertNotIn("Model:", printed)
        self.assertNotIn("Input size:", printed)
        self.assertNotIn("Calling OpenAI API", printed)
        self.assertNotIn("Done in", printed)
