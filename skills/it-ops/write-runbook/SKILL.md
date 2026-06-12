---
description: Generate an operations runbook for a service, process, or deployment procedure. Use when a new service is launched or an undocumented process needs to be standardized.
---

# Write Runbook

Create a structured operational runbook for a service, deployment, or on-call procedure — covering health checks, common failure modes, escalation paths, and recovery steps.

## When to Use

- A new service is going into production and has no runbook
- An existing process is undocumented and has caused incidents
- A team is onboarding new on-call engineers who need step-by-step guidance
- After an incident revealed a gap in operational documentation

## Steps

1. **Gather context** — understand: service name, what it does, tech stack, dependencies, team owner, SLA
2. **Write the overview** — purpose, criticality, and who owns it
3. **Document health checks** — how to verify the service is healthy (endpoints, metrics, logs)
4. **List common failure modes** — the top 3–5 things that go wrong and their symptoms
5. **Write recovery procedures** — numbered steps for each failure mode
6. **Define escalation path** — who to page, in what order, at what severity threshold
7. **Add useful commands** — copy-paste-ready CLI commands for diagnosis and recovery
8. **Add links** — dashboards, logs, deployment pipeline, on-call rotation

## Output Format

```markdown
# Runbook — <Service Name>

**Owner:** <team>  **Severity:** P1 / P2 / P3  **Updated:** YYYY-MM-DD

## Overview
<1–2 sentences: what the service does and why it matters>

## Health Checks
- **HTTP:** `curl -f https://service/health` → expect `{"status":"ok"}`
- **Metrics:** Grafana dashboard → [link]
- **Logs:** `kubectl logs -n prod -l app=service-name --tail=100`

## Common Failure Modes

### 1. High Error Rate (5xx Spike)
**Symptoms:** Error rate >1% in Datadog, user reports of failures
**Steps:**
1. Check recent deploys: `git log --oneline -10`
2. Roll back if deploy in last 30 min: `kubectl rollout undo deployment/service-name`
3. Check DB connections: `psql -c "SELECT count(*) FROM pg_stat_activity;"`

### 2. Service Unresponsive / Pod CrashLoopBackOff
**Symptoms:** Health check returns 503, pods in CrashLoop
**Steps:**
1. `kubectl describe pod -n prod -l app=service-name`
2. Check OOM: look for `OOMKilled` in events
3. Increase memory limit in `k8s/deployment.yaml` and redeploy

## Escalation Path
| Severity | First | If no response (15 min) | If no response (30 min) |
|----------|-------|-------------------------|-------------------------|
| P1       | On-call engineer | Engineering manager | CTO |
| P2       | On-call engineer | Team lead | — |

## Useful Commands
\`\`\`bash
# Restart service
kubectl rollout restart deployment/service-name -n prod

# View recent logs
kubectl logs -n prod -l app=service-name --since=1h

# Check resource usage
kubectl top pods -n prod -l app=service-name
\`\`\`

## Links
- [Grafana Dashboard](#) | [Deployment Pipeline](#) | [On-call Rotation](#)
```

## Example Invocation

```
/write-runbook
/write-runbook <describe the service or paste existing notes>
```

## Notes

- Every recovery step must be actionable — no "investigate the issue" steps without specifics
- Include the "what to check first" mental model, not just a list of commands
- Keep commands copy-paste ready: no `<placeholder>` without a note on where to find the real value
- Save output to `runbooks/<service-name>.md`
