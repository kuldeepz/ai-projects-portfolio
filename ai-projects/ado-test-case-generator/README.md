# ADO Test Case Generator

AI-powered test case generator for Azure DevOps user stories. Converts acceptance criteria into comprehensive BDD test cases covering happy paths, edge cases, negative tests, security, and performance.

## What It Does

- **BDD format** — Given/When/Then scenarios from user story AC
- **5 test types** — happy_path, edge_case, negative, security, performance
- **Automation flags** — marks cases suitable for automated testing
- **Priority assignment** — critical/high/medium/low per test
- **Coverage analysis** — identifies untested requirements

## Quick Start

```bash
cd ado-test-case-generator
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY
python test_case_generator.py
```

## Sample Output

```
User Story: US-142 — Password Reset Flow
Generated 8 test cases:

TC-001 [happy_path] [critical] [auto-candidate]
  Given a user with a valid registered email
  When they request a password reset
  Then a reset email is sent within 30 seconds
  And the link expires after 1 hour

TC-004 [negative] [high]
  Given a user enters an unregistered email
  When they submit the reset form
  Then the system shows "If this email exists, you'll receive a link"
  (security: no account enumeration)

TC-006 [security] [critical] [auto-candidate]
  Given a reset link has already been used
  When the same link is clicked again
  Then access is denied with 400 status
```

## Run Tests (No API Key Required)

```bash
python test_test_case_generator.py
```

## Tech Stack

- OpenAI GPT-4o-mini with function calling
- BDD-structured test output
