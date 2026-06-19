---
description: Convert raw daily notes into a formatted standup, weekly summary, executive update, or Slack message. Use at the start or end of the day to produce polished status updates.
---

# Standup Write

Transform bullet-point notes or a brain dump into a polished status report in one of four formats: daily standup, weekly summary, executive update, or Slack message.

## When to Use

- End of day or before a standup call — turn raw notes into a clean update
- Weekly reporting — synthesize the week's work into a summary for leadership
- Executive updates — distill technical progress into business-impact language
- Async Slack updates — quick, scannable message for the team channel

## Steps

1. **Parse the notes** — extract: completed work, in-progress items, blockers, upcoming work
2. **Identify the format** from the request:
   - `standup` — yesterday / today / blockers (concise, <5 bullets each)
   - `weekly` — achievements, in-progress, blockers, next week (with impact statements)
   - `executive` — wins, risks, decisions needed (business language, no jargon)
   - `slack` — single compact message with emoji structure, scannable in 10 seconds
3. **Elevate blockers** — make them visible and specific; include who/what is needed to unblock
4. **Write wins clearly** — be specific about what was delivered, not just what was worked on
5. **Apply appropriate tone** — casual for Slack, professional for executive
6. **Output** the formatted report

## Output Format

### standup
```
Yesterday:
  ✅ Completed auth service refactor — all tests green
  ✅ Reviewed and merged 3 PRs from backend team
  ✅ Unblocked infrastructure ticket with DevOps

Today:
  🔵 Starting architecture review for payment microservice
  🔵 1:1s with 2 team members (10am, 2pm)

Blockers:
  ⚠️  Waiting on security team approval for Azure AD integration (escalated to manager)
```

### weekly
```
## Week of <date> — <Name>, <Role>

**Wins:**
- Shipped Sprint 24 on time: auth refactor + 2 new API endpoints
- Reduced build time 40% by parallelizing test pipeline

**In Progress:**
- Payment microservice architecture review (50% done)
- Hiring: 2 candidates in final round

**Blockers / Risks:**
- Azure AD approval delayed 2 weeks — may affect Q3 milestone

**Next Week:**
- Complete architecture review and share RFC
- Begin onboarding new backend engineer
```

### executive
```
## AI Platform Update — Week of <date>

**Progress:** Sprint 24 delivered on schedule. Authentication system
hardened and deployed to production with zero downtime.

**Risk:** Third-party security approval for Azure AD integration is
delayed 2 weeks. Mitigation plan in place; team is building parallel
to avoid blocking the Q3 launch.

**Decision Needed:** Approve additional $2k/month for managed vector
DB service to meet performance targets.
```

### slack
```
:wave: *AI Lead Update — <date>*
:white_check_mark: Done: sprint 24 shipped ✓, auth refactor merged ✓, 3 PRs reviewed ✓
:blue_circle: Today: payment service arch review + team 1:1s
:warning: Blocker: Azure AD approval still pending — needs security team escalation
```

## Example Invocation

```
/standup-write
/standup-write weekly
/standup-write executive <paste notes>
/standup-write slack
```

## Notes

- Default format is `standup` if not specified
- Never pad with vague statements like "continued work on..." — be specific
- Blockers must name what is needed and who can unblock it
- For executive format: no technical jargon, lead with business outcomes
