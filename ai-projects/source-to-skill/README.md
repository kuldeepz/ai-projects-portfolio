# source-to-skill

Ingest **any source** — a web page/URL, a PDF, or an ODF/DOCX/PPTX document —
and distill it with an LLM into either:

- a **knowledge note** (`.md` summary), or
- a reusable **skill** (`SKILL.md` matching this repo's `skills/_template/` format).

Powered by **Azure OpenAI** (a `gpt-4.1` deployment by default).

## Pipeline

```
SOURCE          INGEST              DISTILL (LLM)        VALIDATE           WRITE
─────────────────────────────────────────────────────────────────────────────────────
web URL ─┐                          ┌ note  → markdown   frontmatter +    notes/<name>.md
PDF      ├─► loader → clean text ──►┤                    section checks
ODF/DOCX─┘   (per source type)      └ skill → SkillDoc    + dedupe vs      skills/<cat>/<name>/SKILL.md
                                       (structured out)    existing skills
```

| Source | Loader |
|---|---|
| URL / web page | `trafilatura` (readability extraction) |
| PDF | `PyMuPDF` |
| ODF / DOCX / PPTX / RTF | `unstructured` |
| `.md` / `.txt` | passthrough |

## Setup

```bash
cd ai-projects/source-to-skill
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then add your Azure endpoint, key, and deployment name
```

## Usage

```bash
# Produce both a note and a skill (default)
python distiller.py https://example.com/some-article

# Just a knowledge note
python distiller.py ./whitepaper.pdf --mode note

# Just a skill (writes to skills/<category>/<name>/SKILL.md)
python distiller.py ./runbook.docx --mode skill

# Overwrite an existing skill
python distiller.py ./runbook.docx --mode skill --force

# Custom notes output directory
python distiller.py ./paper.pdf --mode note --out-dir ./out
```

- **Notes** default to `ai-engineering-notes/notes/<slug>.md`.
- **Skills** go to `skills/<category>/<name>/SKILL.md`, where the model proposes
  a `category` (developer / it-ops / lead / code-checks) and a kebab-case `name`.
- Skill generation uses **Structured Outputs** (JSON schema) so the result is
  always a well-formed `SkillDoc`; the output is then validated for required
  sections and de-duplicated against existing skills.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `AZURE_OPENAI_ENDPOINT` | — | required — your `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | — | required |
| `AZURE_OPENAI_DEPLOYMENT` | `gpt-4.1` | the deployment name you created in Azure |
| `AZURE_OPENAI_API_VERSION` | `2024-10-21` | must support Structured Outputs |

## Budget tracking

The tool keeps a running estimate of spend in `usage.cache.json` and **refuses
to make another call once the estimate reaches `BUDGET_INR`** (default ₹8,000).

```bash
python distiller.py --show-usage     # print estimated spend so far
python distiller.py --reset-usage    # zero the ledger
```

After every run it prints `spent ₹X of ₹8000 (N%)`.

Cost is computed from **GPT-4.1 Global Standard** list pricing ($2 in / $0.50
cached in / $8 out per 1M tokens) converted at `USD_TO_INR` (default ₹88).
Cached prompt tokens are credited at the lower rate. Adjust `USD_TO_INR` to the
live FX rate and the `USD_PER_1M_*` values if your contract differs.

> ⚠️ **This is a soft, app-side cap.** It only counts calls made through this
> script, and the ₹ figure is an estimate. It does **not** know about usage from
> other apps or the portal playground.

**For the authoritative hard cap, set an Azure Cost Management budget** on the
resource — Azure enforces this regardless of what any client does:

```bash
az consumption budget create \
  --budget-name source-to-skill-cap \
  --amount 10000 --time-grain Monthly \
  --category Cost \
  --resource-group <your-rg> \
  --start-date 2026-06-01 --end-date 2027-06-01
# then add an alert/action at 80% (₹8k) in the portal, or via --notifications
```

## Testing

Offline tests (no network, no API key needed) cover ingestion routing,
validation, slugify, and writing:

```bash
python -m pytest test_distiller.py -v
```

## Roadmap

- **Phase 2:** git-repo ingestion; knowledge-graph export (rdflib/TTL) to link
  skills and notes — ties into `ai-engineering-notes/14-ontology/`.
- **Phase 3:** optional Streamlit UI.

## Notes

- `.env` is git-ignored at the repo root — never commit your key.
- Large sources are truncated to `MAX_SOURCE_CHARS` (~120K chars) per run to
  keep cost/latency bounded; raise it in `distiller.py` if you need more.
