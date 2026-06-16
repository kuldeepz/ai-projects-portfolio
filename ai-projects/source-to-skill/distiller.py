"""
Source-to-Skill Distiller
==========================

Ingest any source (web page / URL, PDF, ODF/DOCX) and distill it with Claude
into either:

  • a knowledge **note** (a structured .md summary), or
  • a reusable **skill** (a SKILL.md following the repo's skills/_template format).

Usage:
    python distiller.py <source> --mode note            # -> notes/<name>.md
    python distiller.py <source> --mode skill            # -> skills/<category>/<name>/SKILL.md
    python distiller.py <source> --mode both             # both of the above
    python distiller.py https://example.com/article --mode skill
    python distiller.py ./paper.pdf --mode note
    python distiller.py ./spec.docx --mode both --out-dir ./out

The LLM provider is Claude (Anthropic). Set ANTHROPIC_API_KEY in your .env.
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from openai import AzureOpenAI
from pydantic import BaseModel, Field
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()
console = Console()

# ─── Config ───────────────────────────────────────────────────────────────────

# On Azure OpenAI you call a *deployment*, not a model name directly. Set this to
# the deployment you created in the Azure portal (often named after the model,
# e.g. "gpt-4.1"). The deployment must be backed by a model that supports
# Structured Outputs (gpt-4.1 / gpt-4o families do).
DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4.1")
# API version that supports Structured Outputs / parse(). Override if needed.
API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
MAX_TOKENS = 16000
# Cap how much source text we feed the model (Claude handles far more, but this
# keeps cost/latency sane for a single distillation). ~120K chars ≈ 30K tokens.
MAX_SOURCE_CHARS = 120_000

REPO_ROOT = Path(__file__).resolve().parents[2]  # .../MyCodebase
SKILL_CATEGORIES = ["developer", "it-ops", "lead", "code-checks"]

REQUIRED_SKILL_SECTIONS = ["When to Use", "Steps", "Output Format"]

# ─── Budget tracking (app-side soft cap) ────────────────────────────────────────
#
# NOTE: this tracks ONLY spend made through this script, and the ₹ figure is an
# ESTIMATE from the prices below. The authoritative hard cap is an Azure Cost
# Management budget on the resource (see README). Set the prices to match your
# actual Azure contract — defaults are rough gpt-4.1 list pricing in INR/1M tokens.
BUDGET_INR = float(os.getenv("BUDGET_INR", "8000"))
# GPT-4.1 Global Standard list pricing, in USD per 1M tokens. Cached input tokens
# (repeated prompt prefixes Azure serves from cache) bill at the lower rate.
USD_PER_1M_INPUT = float(os.getenv("USD_PER_1M_INPUT", "2.0"))
USD_PER_1M_CACHED_INPUT = float(os.getenv("USD_PER_1M_CACHED_INPUT", "0.50"))
USD_PER_1M_OUTPUT = float(os.getenv("USD_PER_1M_OUTPUT", "8.0"))
USD_TO_INR = float(os.getenv("USD_TO_INR", "88.0"))  # adjust to current FX rate
# Matches the repo's *.cache.json gitignore rule, so it never gets committed.
LEDGER_PATH = Path(__file__).parent / "usage.cache.json"


def _load_ledger() -> dict:
    if LEDGER_PATH.exists():
        import json

        return json.loads(LEDGER_PATH.read_text())
    return {
        "input_tokens": 0,
        "cached_tokens": 0,
        "output_tokens": 0,
        "spent_inr": 0.0,
        "calls": 0,
    }


def _save_ledger(ledger: dict) -> None:
    import json

    LEDGER_PATH.write_text(json.dumps(ledger, indent=2))


def estimate_cost_inr(
    prompt_tokens: int, completion_tokens: int, cached_tokens: int = 0
) -> float:
    uncached_input = max(prompt_tokens - cached_tokens, 0)
    usd = (
        uncached_input / 1_000_000 * USD_PER_1M_INPUT
        + cached_tokens / 1_000_000 * USD_PER_1M_CACHED_INPUT
        + completion_tokens / 1_000_000 * USD_PER_1M_OUTPUT
    )
    return usd * USD_TO_INR


def check_budget() -> None:
    """Abort before a call if the running total has reached the budget."""
    ledger = _load_ledger()
    if ledger["spent_inr"] >= BUDGET_INR:
        raise SystemExit(
            f"Budget reached: estimated ₹{ledger['spent_inr']:.2f} spent "
            f"(cap ₹{BUDGET_INR:.0f}). Refusing to make more calls. "
            f"Raise BUDGET_INR or reset with --reset-usage to continue."
        )


def record_usage(usage) -> dict:
    """Add one call's usage to the ledger and persist it."""
    ledger = _load_ledger()
    prompt = getattr(usage, "prompt_tokens", 0) or 0
    completion = getattr(usage, "completion_tokens", 0) or 0
    details = getattr(usage, "prompt_tokens_details", None)
    cached = getattr(details, "cached_tokens", 0) or 0 if details else 0
    ledger["input_tokens"] += prompt
    ledger["cached_tokens"] = ledger.get("cached_tokens", 0) + cached
    ledger["output_tokens"] += completion
    ledger["spent_inr"] += estimate_cost_inr(prompt, completion, cached)
    ledger["calls"] += 1
    _save_ledger(ledger)
    return ledger


def _print_usage(ledger: dict | None = None) -> None:
    ledger = ledger or _load_ledger()
    spent = ledger["spent_inr"]
    pct = (spent / BUDGET_INR * 100) if BUDGET_INR else 0
    colour = "green" if pct < 80 else "yellow" if pct < 100 else "red"
    console.print(
        Panel.fit(
            f"[bold]Estimated spend (this tool only)[/]\n"
            f"  calls:   {ledger['calls']}\n"
            f"  tokens:  {ledger['input_tokens']:,} in "
            f"({ledger.get('cached_tokens', 0):,} cached) / "
            f"{ledger['output_tokens']:,} out\n"
            f"  spent:   [{colour}]₹{spent:.2f}[/] of ₹{BUDGET_INR:.0f}  ({pct:.0f}%)"
            f"   @ ₹{USD_TO_INR:.0f}/USD",
            border_style=colour,
        )
    )


# ─── Ingestion: one loader per source type ──────────────────────────────────────


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) > MAX_SOURCE_CHARS:
        return text[:MAX_SOURCE_CHARS], True
    return text, False


def load_url(url: str) -> tuple[str, str]:
    """Fetch a web page and extract the readable main content as markdown."""
    try:
        import trafilatura
    except ImportError:
        raise SystemExit("Missing dependency: pip install trafilatura")

    downloaded = trafilatura.fetch_url(url)
    if not downloaded:
        raise SystemExit(f"Could not fetch URL: {url}")
    text = trafilatura.extract(
        downloaded, output_format="markdown", include_links=False
    )
    if not text:
        raise SystemExit(f"Could not extract readable content from: {url}")
    title = trafilatura.extract_metadata(downloaded).title or url
    return title, text


def load_pdf(path: Path) -> tuple[str, str]:
    """Extract text from a PDF, page by page."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise SystemExit("Missing dependency: pip install pymupdf")

    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    title = (doc.metadata or {}).get("title") or path.stem
    doc.close()
    return title, "\n\n".join(pages)


def load_office(path: Path) -> tuple[str, str]:
    """Extract text from ODF / DOCX / PPTX / etc. via `unstructured`."""
    try:
        from unstructured.partition.auto import partition
    except ImportError:
        raise SystemExit(
            "Missing dependency: pip install 'unstructured[odt,docx,pptx]'"
        )

    elements = partition(filename=str(path))
    text = "\n\n".join(e.text for e in elements if getattr(e, "text", None))
    if not text:
        raise SystemExit(f"No extractable text found in: {path}")
    return path.stem, text


OFFICE_EXTS = {".odt", ".odp", ".ods", ".docx", ".doc", ".pptx", ".ppt", ".rtf"}


def ingest(source: str) -> tuple[str, str, str]:
    """Return (source_kind, title, normalized_text) for any supported source."""
    if source.lower().startswith(("http://", "https://")):
        title, text = load_url(source)
        kind = "web page"
    else:
        path = Path(source).expanduser()
        if not path.exists():
            raise SystemExit(f"File not found: {path}")
        ext = path.suffix.lower()
        if ext == ".pdf":
            title, text = load_pdf(path)
            kind = "PDF"
        elif ext in OFFICE_EXTS:
            title, text = load_office(path)
            kind = "office document"
        elif ext in {".md", ".markdown", ".txt"}:
            title, text = path.stem, path.read_text(encoding="utf-8", errors="ignore")
            kind = "text file"
        else:
            raise SystemExit(
                f"Unsupported source type: {ext}. "
                "Supported: URL, .pdf, .odt/.docx/.pptx, .md/.txt"
            )

    text, truncated = _truncate(text)
    if truncated:
        console.print(
            f"[yellow]Note:[/] source truncated to {MAX_SOURCE_CHARS:,} chars."
        )
    return kind, title, text


# ─── Distillation: turn source text into a note or skill via Claude ─────────────

DISTILLER_SYSTEM = """\
You are a knowledge distiller. You read source material and synthesize the \
durable, high-signal knowledge from it — concepts, how-tos, gotchas, and \
decisions — discarding fluff, marketing, navigation text, and boilerplate. \
You write in clear, dense Markdown. You never invent facts that are not \
supported by the source; if the source is thin, you say so rather than padding."""


def _client() -> AzureOpenAI:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
    api_key = os.getenv("AZURE_OPENAI_API_KEY")
    if not endpoint or not api_key:
        raise SystemExit(
            "AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set. "
            "Copy .env.example to .env and fill them in."
        )
    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=api_key,
        api_version=API_VERSION,
    )


def distill_note(client: AzureOpenAI, kind: str, title: str, text: str) -> str:
    """Produce a structured knowledge note (Markdown)."""
    prompt = f"""\
Distill the following {kind} titled "{title}" into a knowledge note.

Write Markdown with this structure:
# {title}
> One-sentence summary of what this is and why it matters.

## Key Concepts
- Bullet the core ideas, each with a tight explanation.

## How It Works / How To
- Concrete steps, commands, or mechanisms where the source provides them.

## Gotchas & Caveats
- Pitfalls, limitations, edge cases.

## Takeaways
- 2-4 sentences: what to remember.

Be faithful to the source. Do not pad. Source follows:

---
{text}
---"""
    check_budget()
    resp = client.chat.completions.create(
        model=DEPLOYMENT,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": DISTILLER_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    record_usage(resp.usage)
    return (resp.choices[0].message.content or "").strip()


class SkillDoc(BaseModel):
    """Structured result for skill generation."""

    name: str = Field(description="kebab-case skill name, e.g. 'summarize-incident'")
    category: str = Field(
        description="one of: developer, it-ops, lead, code-checks"
    )
    description: str = Field(
        description="one-line description for the SKILL.md frontmatter; "
        "starts with a verb and states when to use the skill"
    )
    body: str = Field(
        description="the full SKILL.md body in Markdown (everything AFTER the "
        "frontmatter). Must include '# <Title>', a one-line blockquote, and the "
        "sections: When to Use, Steps, Output Format, Example Invocation, Notes."
    )


def distill_skill(client: AzureOpenAI, kind: str, title: str, text: str) -> SkillDoc:
    """Produce a SKILL.md following the repo's skills/_template format."""
    prompt = f"""\
From the following {kind} titled "{title}", design a reusable agent **skill** \
that captures an actionable capability the material teaches.

Follow this exact SKILL.md body structure (the frontmatter is added separately):

# <Skill Name>
> One-line description of what this skill does and when to use it.

## When to Use
Specific situations that should trigger this skill.

## Steps
1. **Step one** — ...
2. **Step two** — ...

## Output Format
What the final output should look like.

## Example Invocation
```
/<skill-name> <optional-args>
```

## Notes
- Caveats, edge cases, tools relied on.

Choose a `category` from: developer, it-ops, lead, code-checks.
Choose a kebab-case `name`. Write a strong `description` (verb-first, states when to use it).
Be faithful to the source — only encode knowledge it actually supports. Source follows:

---
{text}
---"""
    check_budget()
    completion = client.beta.chat.completions.parse(
        model=DEPLOYMENT,
        max_tokens=MAX_TOKENS,
        messages=[
            {"role": "system", "content": DISTILLER_SYSTEM},
            {"role": "user", "content": prompt},
        ],
        response_format=SkillDoc,
    )
    record_usage(completion.usage)
    doc = completion.choices[0].message.parsed
    if doc is None:
        raise SystemExit("Model did not return a valid skill document.")
    return doc


# ─── Validation & writing ────────────────────────────────────────────────────


def slugify(value: str) -> str:
    value = re.sub(r"[^\w\s-]", "", value.lower()).strip()
    return re.sub(r"[\s_]+", "-", value) or "untitled"


def validate_skill(doc: SkillDoc) -> list[str]:
    """Return a list of validation problems (empty = OK)."""
    problems = []
    if doc.category not in SKILL_CATEGORIES:
        problems.append(
            f"category '{doc.category}' not in {SKILL_CATEGORIES}; "
            "defaulting to 'developer'"
        )
        doc.category = "developer"
    for section in REQUIRED_SKILL_SECTIONS:
        if f"## {section}" not in doc.body:
            problems.append(f"missing required section: ## {section}")
    if not doc.body.lstrip().startswith("#"):
        problems.append("body does not start with a '# Title' heading")
    return problems


def find_duplicate_skill(name: str) -> Path | None:
    skills_root = REPO_ROOT / "skills"
    if not skills_root.exists():
        return None
    for category in SKILL_CATEGORIES:
        candidate = skills_root / category / name / "SKILL.md"
        if candidate.exists():
            return candidate
    return None


def write_note(content: str, title: str, source: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{slugify(title)}.md"
    header = f"<!-- source: {source} | distilled: {date.today().isoformat()} -->\n\n"
    path.write_text(header + content + "\n", encoding="utf-8")
    return path


def write_skill(doc: SkillDoc, source: str, force: bool) -> Path:
    skill_dir = REPO_ROOT / "skills" / doc.category / doc.name
    path = skill_dir / "SKILL.md"
    if path.exists() and not force:
        raise SystemExit(
            f"Skill already exists: {path}\nRe-run with --force to overwrite."
        )
    skill_dir.mkdir(parents=True, exist_ok=True)
    frontmatter = f"---\ndescription: {doc.description}\n---\n\n"
    provenance = f"<!-- generated by source-to-skill from: {source} -->\n\n"
    path.write_text(frontmatter + provenance + doc.body.strip() + "\n", encoding="utf-8")
    return path


# ─── CLI ────────────────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Distill any source (URL, PDF, ODF/DOCX) into a note or skill."
    )
    parser.add_argument("source", help="URL or path to a PDF / ODF / DOCX / text file")
    parser.add_argument(
        "--mode",
        choices=["note", "skill", "both"],
        default="both",
        help="what to produce (default: both)",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=REPO_ROOT / "ai-engineering-notes" / "notes",
        help="where to write notes (skills always go to skills/<category>/<name>/)",
    )
    parser.add_argument(
        "--force", action="store_true", help="overwrite an existing skill"
    )
    parser.add_argument(
        "--show-usage", action="store_true", help="print estimated spend and exit"
    )
    parser.add_argument(
        "--reset-usage", action="store_true", help="reset the budget ledger and exit"
    )
    args = parser.parse_args()

    if args.reset_usage:
        if LEDGER_PATH.exists():
            LEDGER_PATH.unlink()
        console.print("[green]✓ usage ledger reset.[/]")
        return
    if args.show_usage:
        _print_usage()
        return

    console.print(Panel.fit(f"[bold]Ingesting[/] {args.source}", border_style="cyan"))
    kind, title, text = ingest(args.source)
    console.print(f"  kind: [cyan]{kind}[/]  •  title: [cyan]{title}[/]  •  {len(text):,} chars\n")

    client = _client()

    if args.mode in ("note", "both"):
        console.print("[bold]Distilling note…[/]")
        note = distill_note(client, kind, title, text)
        note_path = write_note(note, title, args.source, args.out_dir)
        console.print(f"[green]✓ note written:[/] {note_path}\n")
        console.print(Markdown(note[:1500] + ("\n\n…" if len(note) > 1500 else "")))
        console.print()

    if args.mode in ("skill", "both"):
        console.print("[bold]Distilling skill…[/]")
        doc = distill_skill(client, kind, title, text)
        for problem in validate_skill(doc):
            console.print(f"  [yellow]validation:[/] {problem}")
        dup = find_duplicate_skill(doc.name)
        if dup and not args.force:
            console.print(
                f"  [yellow]duplicate:[/] a skill named '{doc.name}' already exists "
                f"at {dup}. Re-run with --force to overwrite."
            )
        else:
            skill_path = write_skill(doc, args.source, args.force)
            console.print(
                f"[green]✓ skill written:[/] {skill_path}  "
                f"([cyan]{doc.category}/{doc.name}[/])"
            )

    console.print()
    _print_usage()


if __name__ == "__main__":
    main()
