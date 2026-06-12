# ADO Pipeline Failure Analyzer

AI-powered CI/CD pipeline failure analyzer for Azure DevOps. Paste a build log and get instant root cause analysis, fix steps with commands, and prevention recommendations.

## What It Does

- **Root cause detection** — identifies error type from 9 categories
- **Fix commands** — actionable shell commands to resolve the issue
- **Prevention tips** — long-term fixes to avoid recurrence
- **Confidence score** — how certain the analysis is (0–100)
- **Smart truncation** — keeps last 8000 chars of large logs (errors at the bottom)

## Error Categories

`test_failure` · `build_error` · `dependency_missing` · `permission_denied` · `timeout` · `environment_config` · `network_error` · `infrastructure` · `flaky_test`

## Quick Start

```bash
cd ado-pipeline-failure-analyzer
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python analyzer.py
```

## Sample Output

```
Pipeline Failure Analysis
=========================
Error Type: test_failure
Confidence: 92/100

Root Cause:
  UserAuthTest.test_login_with_expired_token fails because the mock
  JWT library was updated to v3.0 which changed the exception class name.

Fix Steps:
  1. pip install PyJWT==2.8.0
  2. Update test: catch jwt.ExpiredSignatureError (not jwt.ExpiredSignature)
  3. Run: pytest tests/auth/ -v

Prevention:
  - Pin test dependencies in requirements-dev.txt
  - Add dependabot alerts for test libraries
```

## Run Tests (No API Key Required)

```bash
python test_analyzer.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- Tail truncation for large logs (last 8000 chars)
