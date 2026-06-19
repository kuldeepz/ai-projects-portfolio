---
description: Audit exception handling — missing try/except, bare excepts, swallowed exceptions, wrong exception types, and missing cleanup in finally blocks. Use before merging any error-path code.
---

# Exception Check

Systematically audit exception handling across a file or module — find every place where errors can be silently swallowed, incorrectly caught, or left unhandled.

## When to Use

- Before merging code that touches external systems (DB, APIs, file I/O)
- When debugging why errors are disappearing silently in production
- When a service crashes with no useful log message
- Code review of any module with complex control flow

## What to Check

### 1. Missing exception handling on risky operations
```python
# BAD — FileNotFoundError, PermissionError unhandled
data = open(path).read()
result = json.loads(raw)         # json.JSONDecodeError unhandled
response = requests.get(url)     # ConnectionError, Timeout unhandled
```

### 2. Bare `except:` — catches everything including KeyboardInterrupt, SystemExit
```python
# BAD
try:
    do_something()
except:                          # catches EVERYTHING — never do this
    pass

# GOOD
except Exception as e:
    log.error("Failed: %s", e)
    raise
```

### 3. Swallowed exceptions — caught but silently ignored
```python
# BAD — error disappears, caller has no idea something went wrong
try:
    process(data)
except Exception:
    pass                         # silent failure is worse than a crash
```

### 4. Too-broad exception type — hides the real error
```python
# BAD — catches ValueError, TypeError, RuntimeError all the same way
except Exception as e:
    return None                  # caller can't distinguish error types
```

### 5. Exception caught but not re-raised or logged
```python
# BAD — log without raise means execution continues in broken state
except ValueError as e:
    log.warning("Bad value")     # no re-raise — caller gets wrong result
```

### 6. Missing `finally` for cleanup
```python
# BAD — resource leak if exception thrown before close()
conn = db.connect()
result = conn.execute(query)     # if this throws, conn never closed
conn.close()

# GOOD — use context manager or finally
with db.connect() as conn:
    result = conn.execute(query)
```

### 7. Wrong exception hierarchy — catching parent when child is needed
```python
# BAD — catches all OSError (includes PermissionError, FileNotFoundError)
except OSError:
    return default               # may hide permission errors
```

### 8. Exception in `__init__` with partial initialization
```python
# BAD — object partially constructed if __init__ throws midway
class Service:
    def __init__(self):
        self.conn = db.connect()
        self.cache = Redis()     # if this fails, self.conn leaks
```

## Steps

1. **Scan all `try` blocks** — check what's in the `except` clause
2. **Find bare `except:`** — flag every instance as blocking
3. **Find `except ... pass`** — flag as major (swallowed exception)
4. **Find risky calls without try/except** — `open`, `json.loads`, HTTP calls, DB calls, subprocess
5. **Check every `except` has either `raise`, `log + raise`, or a documented reason for suppressing**
6. **Find missing `finally` / `with` blocks** around resources
7. **Check exception specificity** — is the caught type as narrow as possible?
8. **Report all findings** with severity, line, issue, and fix

## Output Format

```
## Exception Check — <filename>

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 18   | Bare `except:` catches SystemExit and KeyboardInterrupt | Use `except Exception as e:` |
| blocking | 34   | `except Exception: pass` — exception swallowed silently | Log + re-raise or handle explicitly |
| major    | 52   | `open(path)` with no try/except — FileNotFoundError unhandled | Wrap in try/except or check `path.exists()` first |
| major    | 71   | `requests.get()` timeout not handled — hangs indefinitely | Add `timeout=30` and catch `requests.Timeout` |
| minor    | 88   | `except Exception` too broad — should be `except ValueError` | Narrow exception type |
| minor    | 103  | `conn = db.connect()` — no `with` block, leak if exception | Use `with db.connect() as conn:` |

### Corrected Examples
\`\`\`python
# Line 34 — log and re-raise
try:
    process(data)
except Exception as e:
    log.error("process() failed for data=%r: %s", data, e)
    raise

# Line 52 — handle FileNotFoundError
try:
    data = open(path).read()
except FileNotFoundError:
    log.warning("Config file not found: %s — using defaults", path)
    data = DEFAULT_CONFIG
\`\`\`

### Summary
2 blocking issues that will hide crashes in production.
3 unhandled risky operations that will cause unhandled exceptions under normal conditions.
```

## Example Invocation

```
/exception-check
/exception-check src/services/payment.py
```

## Notes

- "Never `pass` in an `except` block" is the iron rule — the only exception is explicitly documented intentional suppression
- Every exception should be either re-raised, logged with context, or converted to a domain exception
- `except Exception as e: raise` is valid — it lets you add logging without changing the exception flow
- For async code: also check that `asyncio.Task` exceptions are not silently dropped
