---
description: Diagnose a CI/CD pipeline failure from a build log. Use when a pipeline fails and you need the root cause, fix steps, and prevention recommendations quickly.
---

# Pipeline Fix

Analyze a CI/CD pipeline failure log, identify the root cause, and provide exact fix commands and prevention tips.

## When to Use

- A build, test, or deploy pipeline has failed
- You have a log or error output from Azure DevOps, GitHub Actions, Jenkins, or similar
- You need to quickly unblock a team blocked by a failing pipeline

## Steps

1. **Parse the log** — scan from the bottom up (errors appear at the end); identify the first fatal line
2. **Classify the failure type**:
   - `test_failure` — unit/integration test assertion failed
   - `build_error` — compile error, syntax error, missing file
   - `dependency_missing` — package not found, pip/npm install failed
   - `permission_denied` — secrets not injected, service principal issue, file permission
   - `timeout` — step exceeded time limit
   - `environment_config` — wrong env var, missing secret, wrong branch/environment
   - `network_error` — registry unreachable, DNS failure, firewall
   - `flaky_test` — test passes locally, fails intermittently in CI
   - `infrastructure` — agent/runner out of disk/memory, Kubernetes pod crash
3. **State the root cause** — one paragraph, plain English
4. **List fix steps** — numbered, with exact commands where possible
5. **Add prevention tips** — changes to the pipeline config, tests, or infra to avoid recurrence
6. **Rate confidence** — 0–100 based on how clear the log evidence is

## Output Format

```
## Pipeline Failure Analysis

**Failure Type:** test_failure
**Confidence:** 91/100

**Root Cause:**
UserAuthTest.test_login_with_expired_token fails because PyJWT was updated
to v3.0 which renamed `jwt.ExpiredSignature` to `jwt.ExpiredSignatureError`.
The test catches the old exception class and never matches.

**Fix Steps:**
1. `pip install PyJWT==2.8.0` (pin to last known-good version)
   OR update the test: `except jwt.ExpiredSignatureError:`
2. Run locally: `pytest tests/auth/test_login.py -v`
3. Re-trigger pipeline once green locally

**Prevention:**
- Pin all test dependencies in `requirements-dev.txt`
- Add `dependabot.yml` to alert on minor/major library bumps
- Run `pip-audit` as a pipeline step before test execution

**Confidence Notes:**
Log clearly shows the exception class name mismatch on line 47.
```

## Example Invocation

```
/pipeline-fix
/pipeline-fix <paste log output>
```

## Notes

- Always read from the bottom of the log — the first FATAL or ERROR line is usually the real cause
- For large logs (>500 lines), focus on the last 100 lines and the first failure marker
- If confidence is <50, ask the user for more context (env vars, recent changes, branch)
