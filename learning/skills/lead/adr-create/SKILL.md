---
description: Convert a discussion, meeting notes, or Slack thread into a structured Architecture Decision Record (ADR). Use when a significant technical decision has been made and needs to be documented.
---

# ADR Create

Turn discussion notes, Slack threads, or meeting summaries into a structured Architecture Decision Record in Michael Nygard format — auto-numbered and saved to the decisions directory.

## When to Use

- A significant technical decision was made (database choice, framework, API design pattern)
- A team is debating between options and needs the decision captured regardless of outcome
- An auditor or new team member needs to understand why a past decision was made
- Before implementing anything non-trivial that a future engineer might question

## Steps

1. **Parse the input** — extract: the problem being solved, options considered, the decision made, who was involved
2. **Write the context** — what situation forced this decision? What constraints apply?
3. **Write the decision** — one clear statement of what was chosen
4. **Write the rationale** — why this option over the alternatives? What criteria were used?
5. **List alternatives considered** — for each: what it was, and why it was rejected
6. **Write consequences** — positive outcomes, negative trade-offs, future implications
7. **Set status** — `proposed` (not yet agreed), `accepted` (agreed and active), `deprecated` (superseded)
8. **Auto-number** — check `decisions/` folder for existing ADRs and increment the number
9. **Save** to `decisions/ADR-NNN-<title-slug>.md`

## Output Format

```markdown
# ADR-007: Use pgvector for Vector Storage

**Status:** Accepted
**Date:** YYYY-MM-DD
**Deciders:** <team/role names>

## Context
<What is the situation? What forces are at play? What constraints exist?>

## Decision
We will use the pgvector extension on our existing PostgreSQL RDS instance
for vector similarity search in the RAG pipeline.

## Rationale
- No additional infrastructure to manage or pay for
- Same backup, monitoring, and IAM policies already in place
- Sufficient for <10M vectors at current scale projections
- Team has existing PostgreSQL expertise

## Alternatives Considered

### Pinecone
Rejected: additional monthly cost ($70+), vendor lock-in, requires new
team knowledge, and overkill for our current scale.

### Weaviate
Rejected: self-hosted adds ops burden; managed version exceeds budget;
team has no Kubernetes background to maintain it.

## Consequences
✅ Zero new infrastructure, cost-neutral
✅ One less vendor relationship to manage
⚠️  Will need to revisit if vectors exceed ~50M or query latency degrades
⚠️  pgvector has less tooling than dedicated vector DBs (no native UI)

## References
- [pgvector GitHub](https://github.com/pgvector/pgvector)
- Spike results: see Notion doc #spike-vector-db
```

## Example Invocation

```
/adr-create
/adr-create <paste discussion notes, Slack thread, or decision summary>
```

## Notes

- The context section is the most important — future readers need to know what problem existed, not just what was chosen
- Rejected alternatives are as valuable as the decision itself — document them thoroughly
- Status `proposed` = still open for discussion; `accepted` = committed; never delete old ADRs, only deprecate them
- If `decisions/` folder doesn't exist, create it
