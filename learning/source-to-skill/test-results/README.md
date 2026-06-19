# Test results — end-to-end walkthrough

Real runs of the distiller, kept as example outputs. Each subfolder holds
everything produced from one source. This README explains **exactly how the
`building-effective-agents` run worked, step by step.**

## The run

| | |
|---|---|
| **Source** | https://www.anthropic.com/engineering/building-effective-agents (web article) |
| **Command** | `python distiller.py <url> --mode both --graph` |
| **Model** | Azure OpenAI `gpt-4.1` deployment |
| **LLM calls** | 3 (one per output: note, skill, graph) |
| **Cost** | ~₹2.65 (tracked in `usage.cache.json`, capped at ₹8,000) |
| **Outputs** | `note.md`, `SKILL.md`, `graph.ttl` (in `building-effective-agents/`) |

## How it worked, end to end

```
  URL                                                        OUTPUTS
   │                                                            ▲
   ▼                                                            │
┌──────────┐   ┌──────────────┐   ┌───────────────────┐   ┌──────────┐
│ 1 INGEST │──▶│ 2 NORMALIZE  │──▶│ 3 DISTILL (3 LLM   │──▶│ 4 VALIDATE│
│ fetch +  │   │ clean text + │   │   calls on Azure)  │   │  + WRITE  │
│ extract  │   │ title        │   │ note / skill /graph│   │  + BUDGET │
└──────────┘   └──────────────┘   └───────────────────┘   └──────────┘
```

### 1. Ingest — fetch the page and extract readable content
`distiller.py` saw an `http(s)` source, so it routed to the **URL loader**
(`load_url`). It used **trafilatura** to download the page and strip away the
nav, header, footer, and boilerplate — keeping just the article body as clean
Markdown. The page `<title>` became the source title:
*"Building Effective AI Agents"*.

### 2. Normalize — bound the input
The extracted text was capped at `MAX_SOURCE_CHARS` (~120K chars) so a single
distillation stays cheap and fast. (This article fit well under the cap.)

### 3. Distill — three LLM calls on Azure OpenAI (`gpt-4.1`)
Because the command was `--mode both --graph`, the tool made **three** calls,
each with a purpose-built prompt and the article text:

1. **Note** (`distill_note`) → plain Markdown. A free-form summarization prompt
   asks for Key Concepts / How It Works / Gotchas / Takeaways. → `note.md`
2. **Skill** (`distill_skill`) → **Structured Outputs**. The model is forced to
   return a typed `SkillDoc` (`name`, `category`, `description`, `body`), so the
   result is always a well-formed skill, not free text. → `SKILL.md`
3. **Graph** (`extract_graph`) → **Structured Outputs**. The model returns a
   typed list of `(subject, predicate, object)` triples. → fed to step 4's
   writer.

Each call's token usage was read from the API response and added to the budget
ledger (see step 4).

### 4. Validate, write, and track budget
- **Validate (skill):** checked the `SkillDoc` has the required sections
  (`When to Use`, `Steps`, `Output Format`), a valid category, and a
  `# Title` heading; then checked it didn't duplicate an existing skill.
- **Write:**
  - the note → a `.md` file,
  - the skill → a `SKILL.md` in `skills/<category>/<name>/` (here
    `developer/prompt-chaining`),
  - the graph → `rdflib` serialized the 32 triples to Turtle (`.ttl`), each
    concept linked to a `Source` node via `ex:derivedFrom`.
- **Budget:** before each call the tool checked the running ₹ estimate against
  `BUDGET_INR` and refused if over; after each call it added the call's cost.
  The end-of-run panel printed the new total.

> The three files were generated into `skills/` and `ai-engineering-notes/notes/`
> during the run, then collected here so the example outputs don't pollute the
> real skills library.

## The output files

- **`building-effective-agents/note.md`** — distilled knowledge note. Captures
  all six agent patterns, workflows-vs-agents, and the "start simple" guidance.
- **`building-effective-agents/SKILL.md`** — generated skill
  (`developer/prompt-chaining`), in `skills/_template` format.
- **`building-effective-agents/graph.ttl`** — 32-triple concept knowledge graph
  (Turtle). Loadable in the same rdflib/owlrl tooling as
  `ai-engineering-notes/14-ontology/`.

## Known limitation (Phase 3 candidate)

The article describes **six** patterns, but skill mode emits **one** skill per
run (it picked `prompt-chaining`). The note and graph captured the full breadth.
Multi-skill extraction from a broad source (`--max-skills N`) is planned. For
focused, single-topic sources, one skill is exactly the right output.
