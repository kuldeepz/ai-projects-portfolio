# Skills

Reusable AI agent skill definitions — pure `.md` files, no code required.  
Each skill is invocable via `/skill-name` in Claude Code or any agent that supports SKILL.md workflows.

## Structure

```
skills/
├── _template/          ← blank template to copy when creating a new skill
├── developer/          ← hands-on coding skills for engineers
├── it-ops/             ← infrastructure, pipelines, and incident response
├── lead/               ← engineering leadership, planning, and communication
└── code-checks/        ← deep static analysis: async, exceptions, security, memory, concurrency
```

## Skills Index

### Developer (5 skills)

| Skill | Folder | What it does |
|-------|--------|--------------|
| `/code-review` | `developer/code-review/` | Review code for bugs, security, and style — severity-rated findings + fixes |
| `/write-tests` | `developer/write-tests/` | Generate a full pytest suite: happy path, edge cases, error conditions |
| `/debug-error` | `developer/debug-error/` | Root-cause any error or stack trace and provide an exact fix |
| `/explain-code` | `developer/explain-code/` | Plain-English explanation of any code block, function, or file |
| `/refactor-code` | `developer/refactor-code/` | Clean up working code without changing behaviour |

### IT-Ops (4 skills)

| Skill | Folder | What it does |
|-------|--------|--------------|
| `/incident-rca` | `it-ops/incident-rca/` | Blameless postmortem from incident notes — timeline, root causes, action items |
| `/pipeline-fix` | `it-ops/pipeline-fix/` | Diagnose CI/CD failure log → root cause + exact fix commands |
| `/dependency-audit` | `it-ops/dependency-audit/` | Scan requirements.txt or package.json for CVE risks + upgrade commands |
| `/write-runbook` | `it-ops/write-runbook/` | Generate an ops runbook with health checks, failure modes, and recovery steps |

### Lead (6 skills)

| Skill | Folder | What it does |
|-------|--------|--------------|
| `/sprint-plan` | `lead/sprint-plan/` | Backlog + capacity → sprint goal, recommended items, deferred list, risks |
| `/pr-review-checklist` | `lead/pr-review-checklist/` | Full PR review: verdict, severity comments, checklist, positives |
| `/adr-create` | `lead/adr-create/` | Discussion → Architecture Decision Record (Nygard format, auto-numbered) |
| `/standup-write` | `lead/standup-write/` | Raw notes → standup / weekly / executive / Slack update |
| `/skill-gap-review` | `lead/skill-gap-review/` | Team skills vs project requirements → gap analysis, training plan, hiring recs |
| `/release-notes` | `lead/release-notes/` | Work items → developer changelog + business summary + executive highlights |

### Code Checks (9 skills)

| Skill | Folder | What it checks |
|-------|--------|----------------|
| `/async-check` | `code-checks/async-check/` | Missing awaits, blocking calls in async, fire-and-forget exception loss |
| `/exception-check` | `code-checks/exception-check/` | Bare excepts, swallowed exceptions, missing try/except on risky calls |
| `/null-safety` | `code-checks/null-safety/` | Unguarded None access, Optional return not checked, chained attribute risk |
| `/type-check` | `code-checks/type-check/` | Missing annotations, Any leakage, wrong return types, mutable defaults |
| `/security-scan` | `code-checks/security-scan/` | SQL/cmd injection, hardcoded secrets, insecure crypto, OWASP Top 10 |
| `/memory-check` | `code-checks/memory-check/` | Unclosed handles, unbounded collections, missing `with` blocks, resource leaks |
| `/concurrency-check` | `code-checks/concurrency-check/` | Race conditions, missing locks, deadlock risk, thread-unsafe shared state |
| `/dead-code` | `code-checks/dead-code/` | Unused imports, unreachable code, orphaned functions, commented-out blocks |
| `/log-check` | `code-checks/log-check/` | Missing error logs, PII in logs, wrong levels, no stack traces, print() usage |

---

## How to Use a Skill

In **Claude Code**:
```
/code-review src/auth/login.py
/incident-rca <paste incident timeline>
/sprint-plan <paste backlog + capacity>
```

In **VS Code Copilot Chat**:
```
@workspace /debug-error <paste stack trace>
```

In **any agent** that supports markdown skill files:
- Point the agent at the relevant `SKILL.md` file
- The skill's `description` frontmatter tells the agent when to auto-activate it

---

## How to Create a New Skill

1. Copy `_template/` to a new folder under the appropriate category
2. Fill in the frontmatter `description`, steps, and output format
3. Add it to the index table above
4. That's it — no code, no dependencies

---

## Design Principles

- **Pure markdown** — no code, no dependencies, works with any agent
- **Opinionated output format** — every skill specifies exactly what to produce
- **Example invocation** — every skill shows how to call it
- **Audience-aware** — lead skills explicitly handle non-technical output
