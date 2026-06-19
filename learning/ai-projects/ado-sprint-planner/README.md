# ADO Sprint Planner

AI-powered sprint planning assistant for Azure DevOps. Analyzes your backlog, respects team capacity, and recommends an optimal sprint with goal statement and deferred items.

## What It Does

- **Capacity-aware planning** — team velocity + individual availability
- **Sprint goal generation** — concise 1-sentence theme
- **Item recommendation** — ranked by priority, dependencies, and value
- **Deferred list** — items that don't fit with reasoning
- **Risk flags** — capacity over-commitment, single-threaded risks

## Quick Start

```bash
cd ado-sprint-planner
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python sprint_planner.py
```

## Sample Output

```
Sprint Goal: "Deliver core authentication and user onboarding flows"

Recommended Items (28/36 pts):
  ✅ US-101: Login page           [5 pts]
  ✅ US-102: Registration flow    [8 pts]
  ✅ US-103: Email verification   [5 pts]
  ✅ US-107: Password reset       [5 pts]
  ✅ BUG-12: Fix session timeout  [3 pts]

Deferred (capacity exceeded):
  ⏸  US-110: SSO integration     [13 pts] — too large for remaining capacity

Capacity Utilization: 78%
```

## Run Tests (No API Key Required)

```bash
python test_sprint_planner.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Sample 8-item backlog exceeding 36pt capacity for demo
