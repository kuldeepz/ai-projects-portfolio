---
description: Root-cause an error message or stack trace and suggest a concrete fix. Use when you hit an exception, a test failure, or an unexpected runtime error.
---

# Debug Error

Diagnose an error message or stack trace, identify the root cause, and provide step-by-step fix instructions.

## When to Use

- You have an error message, stack trace, or unexpected output you don't understand
- A test is failing and the assertion message doesn't make the cause obvious
- A service is crashing and you need to trace back to the origin

## Steps

1. **Parse the error** — identify the exception type, the message, and the deepest frame in user code (skip library internals)
2. **Read the relevant file and line** — look at the line that threw and the lines around it for context
3. **Identify the root cause category**:
   - `TypeError` / `AttributeError` — wrong type or missing attribute, trace back to where the value was set
   - `KeyError` / `IndexError` — missing key or out-of-bounds, check the data source
   - `ImportError` / `ModuleNotFoundError` — missing dependency or wrong path
   - `AssertionError` — check what the test expected vs what it got
   - `ConnectionError` / `TimeoutError` — check config, credentials, network
4. **State the root cause** in plain English — one sentence, no jargon
5. **Provide the fix** — exact code change, command to run, or config to update
6. **Add a prevention tip** — how to avoid this class of error in future

## Output Format

```
## Debug Report

**Error:** TypeError: unsupported operand type(s) for +: 'int' and 'str'
**File:** src/calculator.py, line 34, in add_values

**Root Cause:**
`user_input` comes from `request.form.get()` which returns a string.
It is passed directly to `add_values()` which expects an int.

**Fix:**
\`\`\`python
# Before
result = add_values(user_input, base)

# After
result = add_values(int(user_input), base)
\`\`\`

**Prevention:**
Validate and cast all form/query inputs at the boundary before they enter
business logic. Consider a Pydantic model or a dedicated parser layer.
```

## Example Invocation

```
/debug-error
/debug-error <paste error message or stack trace>
```

## Notes

- Always look at the deepest frame in *user* code, not the library frame
- If the error is intermittent, ask about concurrency, caching, or environment differences
- If there is no stack trace, ask the user to enable verbose logging first
