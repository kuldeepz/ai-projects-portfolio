---
description: Analyze a team's current skills against project requirements and produce a gap report with coverage score, member fit, training plan, and hiring recommendations. Use during capacity planning or team assessments.
---

# Skill Gap Review

Map a team's current skills against what a project or role requires — produce a coverage score, per-member fit, training priorities, and hiring recommendations.

## When to Use

- Quarterly team capability assessment
- Planning a new project and evaluating team readiness
- Building a hiring plan for the next quarter
- Justifying training budget with data
- Onboarding a new team member who needs a development plan

## Steps

1. **Parse the input** — extract: team members with their skills and levels, project or role requirements with importance
2. **Score each required skill** — how well is it covered across the team? (0 = no one, 1 = one person partial, 2 = one person solid, 3 = multiple people)
3. **Calculate coverage score (0–100)** — weighted by importance (critical skills count more)
4. **Identify critical gaps** — required skills with coverage score 0 or 1 where importance is `critical` or `high`
5. **Score member fit** — for each team member, what % of required skills do they have at the needed level?
6. **Write training recommendations** — per gap: skill name, priority, suggested resource, who should train
7. **Write hiring recommendations** — roles to hire with must-have skills based on the gaps
8. **Produce a summary** with top 3 actions

## Output Format

```
## Skill Gap Analysis

**Project:** <name>  |  **Team Size:** 5  |  **Coverage Score:** 62/100

### Critical Gaps
| Skill                    | Coverage | Importance | Gap Severity |
|--------------------------|----------|------------|--------------|
| MLOps / model deployment | 0/5 members | Critical  | 🔴 Severe   |
| Azure DevOps pipelines   | 1/5 partial | High      | 🟠 High     |
| Vector databases         | 1/5 partial | High      | 🟠 High     |

### Member Fit
| Name           | Role       | Fit % | Strengths                    | Gaps                    |
|----------------|------------|-------|------------------------------|-------------------------|
| Kuldeep Rao    | AI Lead    | 88%   | Python, AI/ML, Azure, RAG    | MLOps deployment        |
| Sarah Chen     | Backend    | 71%   | FastAPI, PostgreSQL, Python  | ML serving, vectors     |
| Dev Kumar      | Frontend   | 34%   | React, TypeScript            | Most backend/ML skills  |

### Training Recommendations
| Priority | Skill                  | For               | Suggested Resource                   |
|----------|------------------------|-------------------|--------------------------------------|
| Critical | MLOps fundamentals     | Sarah, Dev        | Coursera MLOps Specialization (4 wk) |
| High     | Azure DevOps / AZ-400  | All               | Microsoft Learn — free, 20 hrs       |
| Medium   | Vector DB (pgvector)   | Sarah             | pgvector docs + 1 internal spike     |

### Hiring Recommendations
- **MLOps Engineer** — must-have: Kubernetes, MLflow, Azure ML, Python
  Reason: 0 team members cover model deployment end-to-end

### Top 3 Actions
1. Enroll Sarah in MLOps course before Q3 sprint (unblocks model deployment)
2. Book AZ-400 training for full team (fills ADO pipeline gap for everyone)
3. Open MLOps Engineer req — 6-week hiring cycle needed before project milestone
```

## Example Invocation

```
/skill-gap-review
/skill-gap-review <paste team roster + project requirements>
```

## Notes

- Coverage score weights critical skills at 3x, high at 2x, medium at 1x
- "Fit %" is the member's match to THIS project's requirements, not their overall ability
- Recommend training before hiring when the gap is 1–2 people and the skill is learnable in <4 weeks
- Recommend hiring when the gap is critical, no team member is close, and the timeline is short
