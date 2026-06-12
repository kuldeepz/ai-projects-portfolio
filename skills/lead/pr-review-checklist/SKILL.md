---
description: Review a pull request diff and produce a verdict, severity-rated comments, and a checklist. Use when you want a thorough AI-assisted PR review before approving or requesting changes.
---

# PR Review Checklist

Perform a structured pull request review on a git diff — verdict, line-level comments, positives, and a standard checklist.

## When to Use

- Reviewing a PR before merge
- Doing a pre-review pass before asking a senior engineer to look
- When you want consistent review coverage across a team

## Steps

1. **Read the diff** — understand the intent: what problem does this PR solve?
2. **Review for correctness** — does the code do what the description says?
3. **Review for security** — OWASP Top 10, injection, secrets, auth/authz gaps
4. **Review for tests** — are new behaviours covered? Are edge cases tested?
5. **Review for performance** — N+1 queries, unnecessary computation, large payloads
6. **Review for style** — naming, dead code, overly complex logic
7. **Write comments** — for each finding: file, line, severity, description, suggested fix
8. **Acknowledge positives** — what was done well?
9. **Complete the checklist** — standard items every PR should satisfy
10. **Deliver verdict**: `approve` / `approve_with_comments` / `request_changes` / `needs_discussion`

## Output Format

```
## PR Review

**Verdict:** 🔴 REQUEST CHANGES

### Comments
| Severity   | File           | Line | Issue                                      |
|------------|----------------|------|--------------------------------------------|
| blocking   | auth.py        | 14   | SQL built with f-string — injection risk   |
| major      | auth.py        | 31   | Hardcoded secret "temp1234"                |
| minor      | utils.py       | 8    | Debug print() left in                      |
| nit        | models.py      | 52   | Unused import `os`                         |
| praise     | tests/auth.py  | —    | Excellent parametrized test coverage       |

### Suggested Fix (blocking — auth.py:14)
\`\`\`python
# Instead of:
query = f"SELECT * FROM users WHERE id = {user_id}"

# Use:
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
\`\`\`

### Checklist
- ❌ No SQL injection protection
- ❌ Secret hardcoded (must use env var or vault)
- ✅ Tests present and cover happy path
- ✅ No breaking API changes
- ⚠️  No migration file despite model change

### Positives
- Clean commit history, well-scoped PR
- Test parametrize pattern is a good pattern to keep
```

## Example Invocation

```
/pr-review-checklist
/pr-review-checklist <paste git diff or PR description>
```

## Notes

- Blocking issues must be fixed before merge — no exceptions
- `praise` severity is important — teams that only get critical feedback disengage
- If the diff is >500 lines, focus on logic and security; note that style review was abbreviated
