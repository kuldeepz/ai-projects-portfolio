# Team Skill Gap Analyzer

AI-powered engineering team skill gap analyzer. Map your team's current skills against project requirements and get coverage scores, member fit assessments, training priorities, and hiring recommendations.

## What It Does

- **Coverage score (0–100)** — how well the team covers all required skills
- **Critical gaps** — skills with zero or insufficient coverage
- **Member fit scores** — how well each person matches current project needs
- **Training recommendations** — prioritized upskilling plan with suggested courses
- **Hiring recommendations** — roles to hire with must-have skills

## Quick Start

```bash
cd team-skill-gap-analyzer
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python analyzer.py
```

## Sample Output

```
Team Skill Gap Analysis
========================
Coverage Score: 62/100
Team Size: 5  |  Project: AI Platform Migration

Critical Gaps:
  🔴 MLOps / model deployment  — 0 team members
  🔴 Azure DevOps pipelines    — 1 member (partial)
  🟡 Vector databases          — 1 member

Member Fit:
  Kuldeep Rao (AI Lead)     — 88% fit  [strong: Python, AI/ML, Azure]
  Sarah Chen (Backend)      — 71% fit  [gap: ML model serving]
  Dev Kumar (Frontend)      — 34% fit  [gap: most backend/ML skills]

Training Recommendations:
  1. [CRITICAL] MLOps fundamentals for Sarah + Dev — Coursera MLOps Specialization
  2. [HIGH]     Azure DevOps for all — Microsoft Learn AZ-400

Hiring:
  → MLOps Engineer (must-have: Kubernetes, MLflow, Azure ML)
```

## Run Tests (No API Key Required)

```bash
python test_analyzer.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Pre-loaded 5-member team for demo mode
