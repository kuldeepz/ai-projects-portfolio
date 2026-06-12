# Standup Report Generator

AI-powered standup report writer. Paste your raw notes and get a polished report in 4 formats: daily standup, weekly summary, executive update, or Slack message.

## What It Does

- **4 formats** — standup · weekly · executive · slack
- **Auto-structure** — extracts: done, in-progress, blockers, next steps
- **Tone-aware** — casual for Slack, professional for executive
- **Blocker highlighting** — surfaces impediments clearly
- **Wins extraction** — pulls out notable achievements for weekly/executive

## Quick Start

```bash
cd standup-report-generator
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python standup.py
```

## Sample Output

**Standup format:**
```
Yesterday:
  ✅ Completed sprint planning session for Sprint 24
  ✅ Reviewed and merged 3 PRs from backend team
  ✅ Unblocked infrastructure issue with DevOps

Today:
  🔵 Starting architecture review for new microservice
  🔵 1:1s with 2 team members

Blockers:
  ⚠️  Waiting on security team approval for Azure AD integration
```

**Slack format:**
```
:wave: *AI Lead Update — June 12*
Done: sprint planning ✓, 3 PRs merged ✓, DevOps unblocked ✓
Today: arch review + team 1:1s
:warning: Blocker: security approval for Azure AD still pending
```

## Run Tests (No API Key Required)

```bash
python test_standup.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Sample notes pre-loaded for "Kuldeep Rao, AI Lead"
