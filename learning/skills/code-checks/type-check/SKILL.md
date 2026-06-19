---
description: Audit type annotations — missing annotations, Any leakage, incorrect return types, inconsistent parameter types, and TypeVar misuse. Use before merging to enforce type-safe code.
---

# Type Check

Review type annotations for completeness and correctness — find missing annotations, `Any` overuse, wrong return types, and patterns that defeat static analysis.

## When to Use

- Before merging code to a typed codebase (mypy, pyright, TypeScript strict mode)
- When a `mypy --strict` run shows errors you want explained and fixed
- When refactoring a module to add types for the first time
- Code review when type annotations are inconsistent or misleading

## What to Check

### 1. Missing annotations on public functions
```python
# BAD — no parameter or return types
def process_order(order, discount):
    return order.total * (1 - discount)

# GOOD
def process_order(order: Order, discount: float) -> Decimal:
    return order.total * Decimal(str(1 - discount))
```

### 2. `Any` used as an escape hatch — defeats the type system
```python
# BAD — Any spreads silently to callers
def parse_config(data: Any) -> Any:
    ...
```

### 3. Wrong return type annotation
```python
# BAD — annotated str but can return None
def get_name(user_id: int) -> str:
    user = db.get(user_id)
    return user.name if user else None   # None != str
```

### 4. `Optional` not used where None is possible
```python
# BAD
def find_user(email: str) -> User:      # should be Optional[User]
    return db.query(User).filter_by(email=email).first()
```

### 5. Mutable default argument (Python-specific type trap)
```python
# BAD — same list shared across all calls
def append_item(item: str, items: list = []) -> list:
    items.append(item)
    return items

# GOOD
def append_item(item: str, items: list[str] | None = None) -> list[str]:
    items = items or []
    items.append(item)
    return items
```

### 6. TypeVar misuse — generic function not actually generic
```python
# BAD — T used in parameter but not constrained or returned consistently
T = TypeVar("T")
def first(items: list[T]) -> T:
    return items[0] if items else None   # None breaks the T guarantee
```

### 7. `cast()` overuse — hiding a real type error
```python
result = cast(str, some_func())   # if some_func can return int, this is a lie
```

### 8. Missing `ClassVar` for class-level attributes
```python
class Config:
    timeout = 30      # should be: timeout: ClassVar[int] = 30
```

### 9. Inconsistent dict/list generics
```python
# BAD — unparameterized generics
def process(items: list) -> dict:   # list[what]? dict[what, what]?
```

## Steps

1. **Scan all function signatures** — flag any missing parameter or return annotations
2. **Find every `Any`** — is it justified? Can it be replaced with a proper type?
3. **Check return type vs actual return statements** — can it return `None` when annotation says otherwise?
4. **Find `Optional` mismatches** — functions that return `None` without `Optional` in annotation
5. **Find mutable default arguments** — `def f(x=[])`, `def f(x={})`, `def f(x=set())`
6. **Find unparameterized generics** — `list`, `dict`, `tuple`, `set` without type params
7. **Find `cast()` calls** — verify they are accurate, not hiding errors
8. **Report** with severity, location, issue, and corrected annotation

## Output Format

```
## Type Check — <filename>

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 12   | Return type `str` but can return `None` | Change to `Optional[str]` |
| blocking | 28   | Mutable default argument `items: list = []` | Use `items: list[str] | None = None` |
| major    | 44   | `Any` return type on public function — defeats type checking | Define a TypedDict or dataclass |
| major    | 67   | Unparameterized `dict` — `dict[str, what]`? | Use `dict[str, float]` |
| minor    | 83   | Missing annotation on public method `calculate_tax` | Add `(amount: Decimal) -> Decimal` |
| minor    | 91   | `cast(str, value)` — value can be int, cast is inaccurate | Fix the upstream type or add runtime check |

### Corrected Examples
\`\`\`python
# Line 12 — correct return type
from typing import Optional
def get_name(user_id: int) -> Optional[str]:
    user = db.get(user_id)
    return user.name if user else None

# Line 28 — fix mutable default
def append_item(item: str, items: list[str] | None = None) -> list[str]:
    return (items or []) + [item]
\`\`\`

### Summary
2 annotation mismatches that will cause mypy errors and potential runtime crashes.
1 mutable default argument that causes a shared-state bug across calls.
```

## Example Invocation

```
/type-check
/type-check src/models/order.py
```

## Notes

- Run alongside `mypy --strict` or `pyright` — this skill explains WHY the errors exist, not just that they do
- `Any` is sometimes unavoidable (e.g. third-party lib with no stubs) — document why with a comment
- For TypeScript: also check `as any`, `as unknown`, non-null assertions (`!`), and missing `strict: true` in tsconfig
- Priority order: fix `blocking` (wrong annotations) before `major` (missing) before `minor` (style)
