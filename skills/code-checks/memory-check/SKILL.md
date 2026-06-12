---
description: Find resource leaks and memory issues — unclosed file/DB/network handles, missing context managers, large object accumulation, and circular references. Use before merging I/O-heavy or long-running code.
---

# Memory Check

Audit code for resource leaks and memory issues — file handles left open, database connections not released, objects growing unbounded, and missing `with` blocks.

## When to Use

- Before merging code that handles files, DB connections, HTTP clients, or sockets
- When a service's memory grows over time without restarting (memory leak suspicion)
- When database connection pools are exhausted in production
- Code review of background workers, batch processors, or long-running services

## What to Check

### 1. File handles not closed
```python
# BAD — handle never closed if exception thrown
f = open(path, "r")
data = f.read()
process(data)
f.close()         # skipped if process() throws

# GOOD
with open(path, "r") as f:
    data = f.read()
```

### 2. Database connections not returned to pool
```python
# BAD — connection leaked if exception thrown before close()
conn = db.get_connection()
result = conn.execute(query)
conn.close()

# GOOD
with db.get_connection() as conn:
    result = conn.execute(query)
```

### 3. HTTP clients / sessions not closed
```python
# BAD — requests.Session not closed; aiohttp ClientSession leaks
session = requests.Session()
response = session.get(url)
# session never closed

# GOOD
with requests.Session() as session:
    response = session.get(url)
```

### 4. Unbounded list / dict accumulation in long-running loops
```python
# BAD — results grows forever in a daemon process
results = []
while True:
    results.append(fetch_next())   # OOM eventually
```

### 5. Circular references preventing garbage collection
```python
# BAD — parent and child hold references to each other
class Node:
    def __init__(self):
        self.children = []
        self.parent = None   # circular if parent.children includes self
```

### 6. Large objects held in module-level variables (never freed)
```python
# BAD — entire dataset stays in memory for the process lifetime
LOOKUP_TABLE = load_entire_dataset()   # 2GB never released
```

### 7. Generator vs list — loading everything into memory unnecessarily
```python
# BAD — loads all 1M rows into memory
rows = list(db.execute("SELECT * FROM events"))

# GOOD — iterate lazily
for row in db.execute("SELECT * FROM events"):
    process(row)
```

### 8. Thread-local or cache not bounded
```python
# BAD — cache grows without eviction
_cache = {}
def get_cached(key):
    if key not in _cache:
        _cache[key] = expensive_compute(key)
    return _cache[key]    # unbounded growth
```

## Steps

1. **Find all `open()` calls** — verify each is inside a `with` block
2. **Find all DB connection / cursor acquisition** — verify `with` or explicit `close()` in `finally`
3. **Find HTTP client / session creation** — verify `with` or `.close()` in `finally`
4. **Find module-level or class-level collections** (`list`, `dict`, `set`) appended inside loops — check for size bounds or eviction
5. **Find long-running `while True` loops** — check if any collection grows inside
6. **Find `list()` wrapping large queries** — suggest lazy iteration
7. **Find in-memory caches** — verify they have a max size (`maxsize`, `lru_cache`, `TTLCache`)
8. **Report** with severity, resource type, and fix

## Output Format

```
## Memory Check — <filename>

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 18   | `open(path)` without `with` — handle leaked on exception | Use `with open(path) as f:` |
| blocking | 34   | `conn = db.get_connection()` without `with` / `finally` | Use context manager or `try/finally` |
| major    | 57   | `results = []` grows unbounded in while-True loop | Cap size or process + clear after N items |
| major    | 71   | `list(db.execute(...))` loads full table into memory | Iterate directly over cursor |
| minor    | 88   | `_cache = {}` — no eviction policy | Use `functools.lru_cache` or `cachetools.TTLCache` |
| minor    | 103  | `requests.Session()` created per-request — not pooled | Create once at module level inside `with` |

### Summary
2 resource leaks that will exhaust DB connections or file descriptors under load.
1 unbounded accumulation that will cause OOM in the background worker.
```

## Example Invocation

```
/memory-check
/memory-check src/workers/event_processor.py
```

## Notes

- File descriptor leaks are invisible until the process hits the OS limit (`ulimit -n`) and crashes
- DB connection pool exhaustion shows up as timeout errors in an otherwise healthy service
- Use `tracemalloc` (Python) or `node --inspect` (Node.js) to confirm leaks in production if static analysis is unclear
- `weakref` can break circular reference cycles when strong ownership isn't needed
