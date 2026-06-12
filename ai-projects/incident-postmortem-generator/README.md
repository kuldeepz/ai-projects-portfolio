# Incident Postmortem Generator

AI-powered blameless postmortem generator. Describe your incident timeline and get a structured RCA with root causes, action items, and a publish-ready markdown report.

## What It Does

- **Blameless RCA** — focuses on systemic causes, not individuals
- **Root cause types** — immediate · contributing · systemic
- **Action items** — priority tiers: immediate / short_term / long_term
- **Executive summary** — 2-3 sentence non-technical overview
- **Markdown export** — saved to `postmortem_YYYY-MM-DD_HHMM.md`

## Quick Start

```bash
cd incident-postmortem-generator
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python postmortem.py
```

## Sample Output

```markdown
# Incident Postmortem — P1: Payment Service Outage

**Severity:** P1  
**Duration:** 47 minutes  
**Impact:** 12,000 users unable to complete checkout

## Executive Summary
A misconfigured Kubernetes memory limit caused OOM kills in the payment
service during a traffic spike. No circuit breaker was in place to degrade
gracefully, resulting in full checkout unavailability for 47 minutes.

## Root Causes
- **Immediate:** Memory limit set to 256Mi (should be 512Mi)
- **Contributing:** Load test did not simulate Black Friday traffic patterns
- **Systemic:** No runbook for memory-related OOM alerts

## Action Items
| Priority | Action | Owner | Due |
|----------|--------|-------|-----|
| Immediate | Increase memory limit to 512Mi | Platform team | Today |
| Short-term | Add circuit breaker to payment service | Backend team | 1 week |
| Long-term | Update load test scenarios | QA team | 1 month |
```

## Run Tests (No API Key Required)

```bash
python test_postmortem.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Blameless postmortem format (Google SRE-inspired)
