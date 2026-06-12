"""
Standup Report Generator
Converts raw bullet notes into polished standup / status reports
for daily standups, weekly syncs, or executive status updates.
"""

import os, sys, json, argparse
from datetime import date, datetime
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

load_dotenv()
console = Console()
MODEL = "gpt-4o-mini"

_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    return _client

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

def generate_report(data: dict) -> dict:
    fmt = data.get("format", "standup")
    fmt_desc = next((v[1] for v in FORMATS.values() if v[0] == fmt), fmt)
    response = get_client().chat.completions.create(
        model=MODEL,
        messages=[
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
        ],
        tools=[{"type": "function", "function": SCHEMA}],
        tool_choice={"type": "function", "function": {"name": "report_output"}},
        temperature=0.4,
    )
    return json.loads(response.choices[0].message.tool_calls[0].function.arguments)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file", nargs="?")
    parser.add_argument("--export", "-e", choices=["json"])
    parser.add_argument("--export-out", default=None)
    parsed = parser.parse_args()

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
        }

    def _run_main_with_args(self, args, cwd, input_payload=None):
        input_file = None
        if input_payload is not None:
            input_file = os.path.join(cwd, "notes.json")
            with open(input_file, "w") as f:
                json.dump(input_payload, f)

        argv = ["standup.py", *args]
        with patch("sys.argv", argv), patch(__name__ + ".generate_report", return_value=self._fake_report()):
            main()

        return input_file

    def test_export_long_flag_with_input_file_creates_md_and_json(self):
        with tempfile.TemporaryDirectory() as td:
            notes = {
                "name": "Test User",
                "role": "Engineer",
                "date": str(date.today()),
                "format": "standup",
                "raw_notes": ["did x", "doing y"],
            }
            self._run_main_with_args(["notes.json", "--export", "json", "--export-out", "result.json"], td, input_payload=notes)

            md_path = os.path.join(td, f"standup_{date.today().isoformat()}.md")
            json_path = os.path.join(td, "result.json")
            self.assertTrue(os.path.exists(md_path))
            self.assertTrue(os.path.exists(json_path))

    def test_export_short_flag_e_with_input_file_works(self):
        with tempfile.TemporaryDirectory() as td:
            notes = {
                "name": "Test User",
                "role": "Engineer",
                "date": str(date.today()),
                "format": "standup",
                "raw_notes": ["did x", "doing y"],
            }
            old_cwd = os.getcwd()
            try:
                os.chdir(td)
                self._run_main_with_args(["-e", "json", "notes.json", "--export-out", "result.json"], td, input_payload=notes)
            finally:
                os.chdir(old_cwd)

            self.assertTrue(os.path.exists(os.path.join(td, f"standup_{date.today().isoformat()}.md")))
            self.assertTrue(os.path.exists(os.path.join(td, "result.json")))

    def test_export_with_no_input_uses_sample_notes_and_exports(self):
        with tempfile.TemporaryDirectory() as td:
            old_cwd = os.getcwd()
            try:
                os.chdir(td)
                self._run_main_with_args(["--export", "json", "--export-out", "sample.json"], td)
            finally:
                os.chdir(old_cwd)

            self.assertTrue(os.path.exists(os.path.join(td, f"standup_{date.today().isoformat()}.md")))
            self.assertTrue(os.path.exists(os.path.join(td, "sample.json")))

    def test_repeated_export_flags_parse_without_breaking(self):
        with tempfile.TemporaryDirectory() as td:
            old_cwd = os.getcwd()
            try:
                os.chdir(td)
                with patch("sys.argv", ["standup.py", "--export", "json", "-e", "json", "--export-out", "dup.json"]), \
                     patch(__name__ + ".generate_report", return_value=self._fake_report()):
                    main()
            finally:
                os.chdir(old_cwd)

            self.assertTrue(os.path.exists(os.path.join(td, "dup.json")))
            self.assertTrue(os.path.exists(os.path.join(td, f"standup_{date.today().isoformat()}.md")))


if __name__ == "__main_test__":
    unittest.main()
