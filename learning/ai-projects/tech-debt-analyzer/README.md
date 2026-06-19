# Tech Debt Analyzer

AI-powered technical debt analyzer for Python codebases. Point it at a file or directory and get a scored debt report with effort estimates, quick wins, and a prioritized action plan.

## What It Does

- **Debt score (0–100)** — lower is worse
- **7 debt categories** — code_quality · architecture · security · testing · documentation · dependencies · performance
- **Effort estimates** — days per debt item
- **Quick wins** — low-effort, high-impact items to tackle first
- **Directory scan** — analyzes up to 20 .py files, 8000 chars each

## Quick Start

```bash
cd tech-debt-analyzer
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
# Analyze a file:
python analyzer.py path/to/file.py
# Analyze a directory:
python analyzer.py path/to/project/
```

## Sample Output

```
Tech Debt Report — myproject/
==============================
Overall Debt Score: 42/100
Total Estimated Effort: 18.5 days

Debt Items:
  [code_quality] 6 functions over 100 lines — 2 days
  [security]     Raw SQL queries in 3 files — 1.5 days  ⚡ QUICK WIN
  [testing]      0% test coverage on auth module — 4 days
  [documentation] 12 public functions with no docstrings — 0.5 days  ⚡ QUICK WIN
  [dependencies]  3 packages >2 major versions behind — 1 day

Quick Wins (do these first):
  1. Add docstrings to public functions (0.5 days)
  2. Parameterize SQL queries (1.5 days)
```

## Run Tests (No API Key Required)

```bash
python test_analyzer.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- AST-free — works with any Python code via text analysis
