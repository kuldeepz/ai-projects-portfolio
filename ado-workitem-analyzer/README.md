# ADO Work Item Analyzer

AI-powered Azure DevOps work item quality analyzer. Scores Definition-of-Ready, rewrites vague acceptance criteria in BDD format, and suggests Fibonacci story points.

## What It Does

- **DoR Score (0–100)** — checks title clarity, AC completeness, description, estimation
- **BDD Rewrite** — converts "Login works" → proper Given/When/Then scenarios  
- **Story Point Suggestion** — Fibonacci (1/2/3/5/8/13) with reasoning
- **Gap Detection** — missing fields, ambiguous language, dependency risks

## Quick Start

```bash
cd ado-workitem-analyzer
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python analyzer.py
```

## Sample Output

```
Work Item: User Authentication Feature
DoR Score: 45/100

Issues:
  - Acceptance criteria too vague ("Login works")
  - No definition of done
  - Missing security requirements

BDD Rewrite:
  Given a registered user visits /login
  When they enter valid credentials
  Then they are redirected to the dashboard
  And a JWT token is stored in httpOnly cookie

Suggested Story Points: 8 (Large — auth, token mgmt, error states)
```

## Run Tests (No API Key Required)

```bash
python test_analyzer.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Structured output for consistent JSON schema
- Mock ADO work item for demo/offline mode
