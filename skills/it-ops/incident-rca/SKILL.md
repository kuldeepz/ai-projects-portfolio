---
description: Write a blameless incident postmortem from an incident description or timeline. Use after any P0/P1/P2 incident to produce a structured RCA with action items.
---

# Incident RCA

Produce a blameless postmortem document from an incident description, Slack thread, or timeline notes.

## When to Use

- After any P0 / P1 / P2 production incident
- When a team needs a structured RCA to share with stakeholders
- During an incident retrospective to structure the conversation

## Steps

1. **Parse the incident input** — extract: what happened, when, duration, impacted users/services, who was involved
2. **Identify the timeline** — reconstruct a chronological sequence of events (detection → escalation → mitigation → resolution)
3. **Determine root causes** — categorize as:
   - `immediate` — the direct trigger (e.g. bad deploy, config change)
   - `contributing` — factors that made it possible (e.g. no canary, missing alert)
   - `systemic` — deeper organizational or process gaps (e.g. no runbook, insufficient monitoring)
4. **Write action items** — for each root cause, one or more action items with:
   - Priority: `immediate` / `short_term` / `long_term`
   - Owner role (not individual name)
   - Clear, actionable description
5. **Write executive summary** — 2–3 sentences, non-technical, suitable for leadership
6. **Output the full postmortem** in markdown

## Output Format

```markdown
# Incident Postmortem — <title>

**Severity:** P1 | **Duration:** X min | **Date:** YYYY-MM-DD
**Impact:** <how many users/services affected>

## Executive Summary
<2–3 non-technical sentences>

## Timeline
| Time (UTC) | Event |
|------------|-------|
| 14:32 | Spike in 5xx errors detected by monitoring |
| 14:38 | On-call engineer paged |
| 14:51 | Root cause identified — bad config deploy |
| 15:19 | Rollback completed, service restored |

## Root Causes
- **Immediate:** <what directly caused it>
- **Contributing:** <what made it possible>
- **Systemic:** <deeper process or org gap>

## Action Items
| Priority | Action | Owner | Due |
|----------|--------|-------|-----|
| Immediate | Roll back config and add validation | Platform | Today |
| Short-term | Add smoke test to deployment pipeline | DevOps | 1 week |
| Long-term | Create incident runbook for this service | SRE | 1 month |

## What Went Well
- <positive observations>

## Lessons Learned
- <key takeaways>
```

## Example Invocation

```
/incident-rca
/incident-rca <paste incident notes, Slack thread, or timeline>
```

## Notes

- Blameless = focus on process and systems, never on individuals
- If duration is unknown, note it as "TBD — ongoing investigation"
- Every action item must be actionable and have an owner role
- Save output to `postmortem_YYYY-MM-DD_<slug>.md`
