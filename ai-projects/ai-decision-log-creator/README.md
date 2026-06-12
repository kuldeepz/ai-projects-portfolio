# AI Decision Log Creator

AI-powered Architecture Decision Record (ADR) generator. Paste discussion notes and get a structured ADR in Michael Nygard format — saved and numbered automatically.

## What It Does

- **ADR format** — title, status, context, decision, rationale, alternatives, consequences
- **Auto-numbering** — `ADR-001`, `ADR-002`, ... saved to `decisions/`
- **Status tracking** — proposed · accepted · deprecated · superseded
- **Alternatives section** — why other options were rejected
- **Markdown output** — ready for docs site or wiki

## Quick Start

```bash
cd ai-decision-log-creator
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python adr_creator.py
```

## Sample Output

```markdown
# ADR-007: Use pgvector for Vector Storage

**Status:** Accepted  
**Date:** 2024-06-12

## Context
We are building a RAG pipeline and need a vector store. The team evaluated
several options including Pinecone, Weaviate, and pgvector. The existing
infrastructure already runs PostgreSQL on RDS.

## Decision
Use pgvector extension on existing PostgreSQL RDS instance.

## Rationale
- No additional service to manage or pay for
- Same backup/monitoring/IAM policies apply
- Sufficient for <10M vectors at current scale
- Team already has PostgreSQL expertise

## Alternatives Considered
- **Pinecone** — rejected: additional cost, vendor lock-in
- **Weaviate** — rejected: overkill, requires new infra team knowledge

## Consequences
- Positive: Zero new infrastructure, cost-neutral
- Negative: Will need migration if scale exceeds PostgreSQL limits
```

## Run Tests (No API Key Required)

```bash
python test_adr_creator.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Michael Nygard ADR format
- Auto-saves to `decisions/ADR-NNN-title-slug.md`
