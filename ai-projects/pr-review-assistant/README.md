# PR Review Assistant

AI-powered pull request reviewer. Paste a git diff and get a thorough code review with verdict, line-level comments, severity ratings, and a checklist — just like a senior engineer's review.

## What It Does

- **Verdict** — approve / approve_with_comments / request_changes / needs_discussion
- **Line-level comments** — file + line reference, severity, suggested fix
- **Severity levels** — blocking · major · minor · nit · praise
- **Checklist** — security, tests, docs, performance, naming
- **Positives** — acknowledges what was done well

## Quick Start

```bash
cd pr-review-assistant
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python reviewer.py
```

## Sample Output

```
PR Review: feature/user-auth
Verdict: 🔴 REQUEST CHANGES

Comments:
  [BLOCKING] auth.py:14
    SQL injection vulnerability: f-string used directly in query.
    Fix: Use parameterized queries — cursor.execute(sql, (user_id,))

  [MAJOR] auth.py:31
    Hardcoded password "temp1234" — must use env variable or secrets vault.

  [MINOR] utils.py:8
    Debug print() statement left in — remove before merge.

  [PRAISE] tests/test_auth.py
    Good test coverage with edge cases and mock setup.

Checklist:
  ✅ Tests present  ❌ No SQL injection protection  ❌ Hardcoded secrets
```

## Run Tests (No API Key Required)

```bash
python test_reviewer.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Sample diff contains SQL injection, debug print, and weak password for demo
