---
description: Turn a backlog and team capacity into a recommended sprint plan with goal, selected items, deferred items, and risk flags. Use at the start of sprint planning.
---

# Sprint Plan

Convert a backlog and team capacity into a capacity-aware sprint plan with a clear sprint goal, recommended items, and deferred list.

## When to Use

- At the start of sprint planning
- When a scrum master or lead wants an AI-assisted first draft to workshop with the team
- When the backlog has more items than capacity and prioritization decisions are needed

## Steps

1. **Parse the input** — extract: team velocity or capacity (story points or days), backlog items with estimates and priorities, any known dependencies or blockers
2. **Calculate capacity** — total available points/days; apply a 20% buffer for unplanned work
3. **Prioritize items** using this order:
   - Committed items from previous sprint carried over
   - P1 bugs and blockers
   - High-priority user stories
   - Tech debt and improvements
   - Nice-to-haves
4. **Check dependencies** — don't include an item if its dependency isn't also included or already done
5. **Write the sprint goal** — one sentence that describes the theme or outcome, not a list of tasks
6. **Build the recommended list** — items that fit within capacity with cumulative point tally
7. **Build the deferred list** — items that didn't fit, with a brief reason for each
8. **Flag risks** — capacity too tight, single-threaded items, unclear requirements

## Output Format

```
## Sprint Plan — Sprint <N>

**Sprint Goal:** "Deliver core checkout flow with payment integration"
**Capacity:** 36 pts  |  **Buffer (20%):** 29 pts available

### Recommended Items (27 pts)
| # | Item                         | Type    | Pts | Cumulative |
|---|------------------------------|---------|-----|------------|
| 1 | US-101: Payment API connect   | Story   | 8   | 8          |
| 2 | US-102: Cart checkout UI      | Story   | 5   | 13         |
| 3 | BUG-44: Fix order total rounding | Bug  | 2   | 15         |
| 4 | US-98: Order confirmation email | Story | 5   | 20         |
| 5 | US-105: Guest checkout        | Story   | 5   | 25         |
| 6 | TECH-12: Upgrade Stripe SDK   | Tech    | 2   | 27         |

### Deferred (capacity exceeded)
| Item                          | Pts | Reason |
|-------------------------------|-----|--------|
| US-110: Promo code support    | 8   | Exceeds remaining capacity |
| US-115: Saved payment methods | 5   | Depends on US-110 |

### Risks
⚠️  US-101 is blocked on Stripe API key from platform team — confirm before sprint starts
⚠️  US-102 and US-105 are assigned to same developer — flag capacity risk
```

## Example Invocation

```
/sprint-plan
/sprint-plan <paste backlog items + team capacity>
```

## Notes

- Sprint goal must be outcome-oriented, not a task list ("enable checkout" not "complete US-101, US-102")
- Always apply a 20% buffer for unplanned work, interruptions, and meetings
- If estimates are missing, ask before proceeding — don't assume 1 point per item
