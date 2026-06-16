# Test results

Real end-to-end runs of the distiller, kept as example outputs. Each subfolder
holds everything produced from one source.

## building-effective-agents

| | |
|---|---|
| **Source** | https://www.anthropic.com/engineering/building-effective-agents (web article) |
| **Command** | `python distiller.py <url> --mode both --graph` |
| **Model** | Azure OpenAI `gpt-4.1` |
| **Cost** | ~₹2.65 (3 calls: note + skill + graph) |

Files:
- `note.md` — distilled knowledge note (captures all six agent patterns).
- `SKILL.md` — generated skill (`developer/prompt-chaining`), in `skills/_template` format.
- `graph.ttl` — 32-triple concept knowledge graph (Turtle), loadable in rdflib.

> Note: the article describes six agent patterns but skill mode emits **one**
> skill per run. Multi-skill extraction from a broad source is a planned Phase 3
> improvement (`--max-skills N`). For focused single-topic sources, one skill is
> the right output.
