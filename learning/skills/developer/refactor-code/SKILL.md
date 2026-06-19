---
description: Refactor code to improve readability, structure, and maintainability without changing behaviour. Use when code is working but hard to read, too long, or has duplication.
---

# Refactor Code

Clean up and restructure working code — improve names, reduce duplication, simplify logic — without breaking any existing behaviour.

## When to Use

- A function is too long (>40 lines) or does too many things
- There is copy-pasted code that should be extracted
- Variable/function names are unclear or misleading
- Nested conditionals are hard to follow
- You are about to add a feature and want the code in better shape first

## Steps

1. **Read and understand** the code fully before touching anything
2. **Identify the smells** — pick from:
   - Long method → extract smaller functions
   - Duplicate code → extract shared helper
   - Deep nesting → early return / guard clauses
   - Magic numbers/strings → named constants
   - Boolean parameters → split into two functions
   - Long parameter list → group into a dataclass or dict
   - Unclear names → rename variables, functions, classes
3. **Apply one refactor at a time** — small, safe steps
4. **Preserve all behaviour** — the output and side effects must be identical
5. **Check for test impact** — if tests exist, verify they still describe the right behaviour after renaming
6. **Output the refactored code** with a brief summary of changes made

## Output Format

```
## Refactored — <filename>

### Changes Made
- Extracted `_validate_input()` from `process_order()` (lines 12–28)
- Replaced magic number `86400` with `SECONDS_PER_DAY = 86_400`
- Replaced nested if/else with early return guards
- Renamed `x` → `retry_count`, `tmp` → `normalized_price`

### Refactored Code
\`\`\`python
<full refactored code here>
\`\`\`

### What Was NOT Changed
- Logic and output are identical to the original
- Public API (function signatures) unchanged
```

## Example Invocation

```
/refactor-code
/refactor-code src/orders/processor.py
```

## Notes

- Never add new features during a refactor — that belongs in a separate commit
- If there are no tests, warn the user before making structural changes
- Prefer readability over cleverness — a clear 5-line block beats a one-liner
- Magic number threshold: any literal used more than once or without obvious meaning
