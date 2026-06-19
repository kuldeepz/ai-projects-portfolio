---
description: Review code for bugs, security vulnerabilities, and style issues. Use when you want a thorough code review with severity-rated findings and concrete fix suggestions.
---

# Code Review

Perform a senior-engineer-level code review on the selected file or code block.

## When to Use

- Before merging a feature branch
- When you want a second opinion on logic, security, or structure
- To catch issues before a formal PR review

## Steps

1. **Read the code** — understand what it's trying to do; identify the language and framework
2. **Check for bugs** — logic errors, off-by-one, null/undefined handling, race conditions
3. **Check for security** — SQL injection, XSS, hardcoded secrets, insecure deserialization, OWASP Top 10
4. **Check for quality** — function length, naming, duplication, single responsibility, dead code
5. **Check for performance** — N+1 queries, unnecessary loops, missing indexes, large allocations
6. **Produce findings** — rate each finding: `blocking` / `major` / `minor` / `nit`
7. **Suggest fixes** — provide a corrected snippet for every `blocking` or `major` finding

## Output Format

```
## Code Review — <filename>

### Verdict: APPROVE | REQUEST CHANGES | NEEDS DISCUSSION

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 42   | SQL built with f-string — injection risk | Use parameterized query |
| major    | 17   | No input validation on user_id | Add assert isinstance(user_id, int) |
| nit      | 88   | Variable name `x` is unclear | Rename to `retry_count` |

### Positives
- Good test coverage on the happy path
- Error messages are informative

### Summary
<2–3 sentences overall assessment>
```

## Example Invocation

```
/code-review
/code-review src/auth/login.py
```

## Notes

- Focus on what matters — don't nitpick style if blocking issues exist
- Always include a positive observation; good code deserves acknowledgment
- If the file is >500 lines, ask the user which section to focus on
