---
description: Explain a code block, function, or file in plain English. Use when onboarding to a codebase, reviewing unfamiliar code, or preparing to explain something to a non-technical stakeholder.
---

# Explain Code

Produce a clear, layered explanation of what a piece of code does — from the high-level intent down to the important details.

## When to Use

- Onboarding to a new codebase or file
- Preparing to explain a system to a stakeholder or junior developer
- Trying to understand code before modifying it
- Creating documentation for a function or module

## Steps

1. **Read the code** — understand the full context: imports, dependencies, calling code if visible
2. **Identify the purpose** — what problem does this code solve? (one sentence)
3. **Explain the structure** — walk through the major sections top-to-bottom
4. **Call out key decisions** — non-obvious logic, algorithms, design patterns used
5. **Identify side effects** — what does it change outside itself? (file, DB, network, state)
6. **Note what could go wrong** — edge cases, assumptions baked in, things callers must ensure
7. **Tailor the explanation** — match the depth to the audience (developer vs lead vs non-technical)

## Output Format

```
## Explanation — <function/file name>

**In one line:** <what it does>

**Purpose:**
<1–2 sentences on the problem it solves>

**How it works:**
1. First it does X because Y
2. Then it calls Z to handle the case where...
3. Finally it returns / writes / emits...

**Key details:**
- The `retry_limit` parameter defaults to 3 — callers can override for faster failure
- Uses exponential backoff — waits 2^n seconds between retries to avoid hammering the API

**Side effects:**
- Writes a log entry to `app.log` on every retry
- Does NOT commit the DB transaction — caller is responsible

**Watch out for:**
- If `timeout` is None the call blocks indefinitely
- Input is not validated — caller must ensure `url` is a valid string
```

## Example Invocation

```
/explain-code
/explain-code src/payments/processor.py
/explain-code <paste code block>
```

## Notes

- Always lead with the one-liner — readers need the "what" before the "how"
- Use analogies for complex algorithms (e.g. "this works like a checkout queue")
- If explaining to a non-technical audience, skip line-level details and focus on inputs, outputs, and effects
