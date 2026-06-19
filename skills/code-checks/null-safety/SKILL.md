---
description: Find null/None safety issues — unguarded attribute access, missing None checks, functions that can return None but callers don't check, and optional values used as if they were always present.
---

# Null Safety

Audit code for null/None dereference risks — the bugs that cause `AttributeError: 'NoneType' object has no attribute '...'` or `TypeError: argument of type 'NoneType' is not iterable` in production.

## When to Use

- Before merging code that calls external APIs, databases, or user input
- When `NoneType` errors appear in production logs
- Code review of any function that returns `Optional[T]` or `T | None`
- When adding a new caller to a function that might return `None`

## What to Check

### 1. Unguarded attribute access on potentially-None value
```python
# BAD — user could be None if not found in DB
user = get_user(user_id)
print(user.name)              # AttributeError if user is None

# GOOD
user = get_user(user_id)
if user is None:
    raise UserNotFoundError(user_id)
print(user.name)
```

### 2. Function return type can be None but callers don't check
```python
def find_config(key: str) -> Optional[str]:
    return CONFIG.get(key)    # returns None if key missing

# BAD caller
timeout = int(find_config("timeout"))   # TypeError if None
```

### 3. Chained attribute access without None guard
```python
# BAD — any step in the chain could be None
name = order.customer.address.city.upper()
```

### 4. Iterating over a potentially-None value
```python
# BAD — TypeError if results is None
for item in db.query(sql):
    process(item)
```

### 5. Dictionary `.get()` result used without None check
```python
# BAD
value = config.get("timeout")
time.sleep(value * 2)         # TypeError if key not in config
```

### 6. `or` default used incorrectly — masks real None
```python
# RISKY — if name="" (empty string), falls back to default unintentionally
name = user.name or "Unknown"
```

### 7. Missing None check after optional method calls
```python
# BAD — re.search() returns None if no match
match = re.search(pattern, text)
result = match.group(1)       # AttributeError if no match
```

### 8. Type annotation says non-None but implementation can return None
```python
def get_price(item_id: int) -> float:  # annotation says float
    item = db.get(item_id)
    return item.price                  # None.price if item not found
```

## Steps

1. **Find all function return types** annotated as `Optional[T]` or `T | None` — check every call site
2. **Find `.` access chains** longer than 2 levels — flag as needs guard
3. **Find `dict.get()` calls** — check if result is used directly without None check
4. **Find `re.search()`, `re.match()`** — check callers guard against `None` before `.group()`
5. **Find DB/ORM calls** that return single objects (`first()`, `get()`) — check None handling
6. **Check function signatures vs implementations** — flag where return can be None but type says otherwise
7. **Find iteration over values from external sources** without None/empty guard
8. **Report all findings** with severity, location, and fix

## Output Format

```
## Null Safety Check — <filename>

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 23   | `user.name` — `get_user()` returns Optional[User], no None check | Guard: `if user is None: raise ...` |
| blocking | 41   | `match.group(1)` — `re.search()` can return None | Guard: `if match: ...` |
| major    | 57   | `config.get("timeout") * 2` — dict.get() may return None | Use `config.get("timeout", 30)` |
| major    | 68   | `order.customer.address.city` — 3-level chain, any step can be None | Use `getattr` chain or Optional chaining |
| minor    | 84   | Return type annotated `str` but can return `None` | Fix annotation to `Optional[str]` |

### Corrected Examples
\`\`\`python
# Line 23 — guard before access
user = get_user(user_id)
if user is None:
    raise UserNotFoundError(f"User {user_id} not found")
print(user.name)

# Line 57 — use default in .get()
timeout = config.get("timeout", 30)
time.sleep(timeout * 2)
\`\`\`

### Summary
2 unguarded None dereferences that will crash in production when records are missing.
1 type annotation mismatch hiding a None return path from callers.
```

## Example Invocation

```
/null-safety
/null-safety src/api/handlers.py
```

## Notes

- Python: focus on `Optional[T]` return values, `dict.get()`, ORM `.first()`, regex `.search()`
- JavaScript/TypeScript: focus on optional chaining gaps (`?.`), non-null assertions (`!`), `find()` returning `undefined`
- The fix is almost never to add `if x is not None` everywhere — prefer fail-fast (raise early) or provide a meaningful default
- A function returning `None` to signal "not found" is a design smell — prefer raising a domain exception
