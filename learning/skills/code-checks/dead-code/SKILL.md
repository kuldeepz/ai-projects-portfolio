---
description: Find dead code — unused variables, unreachable code paths, unused imports, unused function parameters, and commented-out code blocks. Use before a release or when cleaning up a module.
---

# Dead Code

Identify code that is never executed, never read, or no longer needed — unused imports, unreachable branches, commented-out blocks, and orphaned functions.

## When to Use

- Before a release to reduce noise in the codebase
- When onboarding to a legacy codebase to understand what is actually active
- After a refactor to clean up what was replaced
- Code review to flag unnecessary complexity

## What to Check

### 1. Unused imports
```python
# BAD — os, sys imported but never used in the file
import os
import sys
import json    # only json is used below
```

### 2. Unused variables
```python
# BAD — result computed but never used
def process():
    result = expensive_compute()   # assigned but never returned or used
    return "done"
```

### 3. Unreachable code after `return`/`raise`/`break`/`continue`
```python
# BAD — lines after return are never executed
def get_status():
    return "active"
    status = "inactive"   # unreachable
    return status         # unreachable
```

### 4. Condition that is always True or always False
```python
# BAD — always True; else branch is dead code
if True:
    do_something()
else:
    never_runs()          # dead

# BAD — x is always an int here; isinstance check always True
x = int(input())
if isinstance(x, int):   # always True
```

### 5. Commented-out code blocks
```python
# BAD — large block of commented-out code should be deleted
# def old_auth():
#     user = get_user()
#     if user.role == "admin":
#         return True
#     return False
```

### 6. Unused function parameters
```python
# BAD — `ctx` parameter accepted but never used
def handle_request(request, ctx, headers):
    return process(request)   # ctx and headers ignored
```

### 7. Functions/classes defined but never called
```python
# BAD — helper defined but no callers in the codebase
def _legacy_format(data):
    ...   # no calls found anywhere
```

### 8. `__all__` exports that don't exist
```python
# BAD — exports a name that was deleted
__all__ = ["process", "validate", "legacy_format"]   # legacy_format deleted
```

### 9. Duplicate imports or re-imports
```python
import json
# ... 200 lines later ...
import json   # already imported above
```

## Steps

1. **Scan all `import` statements** — check each name is used at least once below
2. **Find all variable assignments** — check each is read at least once after assignment
3. **Find code after `return`/`raise`/`break`/`continue`** — flag as unreachable
4. **Find conditions that are constant** (`if True`, `if False`, hardcoded type checks)
5. **Find consecutive commented lines** (5+ lines) — flag as dead code to delete
6. **Find function parameters** — check each is referenced inside the function body
7. **Find function/class definitions** — check each has at least one call site in the project
8. **Report** with severity and whether it is safe to delete

## Output Format

```
## Dead Code Check — <filename>

### Findings

| Severity | Line | Issue | Action |
|----------|------|-------|--------|
| major    | 1    | `import os` — unused | Delete |
| major    | 3    | `import sys` — unused | Delete |
| major    | 24   | `result = expensive_compute()` — assigned, never read | Delete assignment |
| major    | 38   | Lines 39–41 unreachable after `return` on line 38 | Delete lines 39–41 |
| minor    | 55   | 12-line commented-out function `old_auth` | Delete (use git history to recover if needed) |
| minor    | 78   | `ctx` parameter in `handle_request` — never used | Remove or prefix with `_` to signal intentional |
| minor    | 92   | `_legacy_format()` — no callers found in project | Delete or move to archive branch |

### Safe to Auto-Delete
Lines: 1, 3, 24, 38–41

### Review Before Deleting
Lines 55, 92 — may be referenced by external callers not in this file

### Summary
2 unused imports, 1 dead assignment, 3 unreachable lines.
1 orphaned function with no callers found.
```

## Example Invocation

```
/dead-code
/dead-code src/utils/helpers.py
```

## Notes

- Unused imports are safe to delete; unused code may still have callers in other modules — check before deleting
- Prefix intentionally-unused parameters with `_` (e.g. `_ctx`) to signal intent without triggering linter warnings
- Commented-out code belongs in git history, not in source files — delete it
- Run `vulture` (Python) or `ts-prune` (TypeScript) for a full project-wide dead code scan
