---
description: Detect concurrency bugs — race conditions, shared mutable state without locks, thread-unsafe patterns, and missing synchronization. Use before merging multi-threaded, multi-process, or async concurrent code.
---

# Concurrency Check

Audit code for concurrency hazards — race conditions, unprotected shared state, lock misuse, and patterns that are safe in single-threaded code but break under concurrent execution.

## When to Use

- Before merging multi-threaded, async, or multiprocessing code
- When intermittent bugs appear only under load (symptoms: corrupted data, wrong counts, deadlocks, hangs)
- Code review of background workers, job queues, cache layers, or shared services
- When adding threading to previously single-threaded code

## What to Check

### 1. Shared mutable state without lock
```python
# BAD — counter incremented from multiple threads without lock
counter = 0

def increment():
    global counter
    counter += 1    # read-modify-write: NOT atomic in Python despite GIL
```

### 2. Check-then-act race condition
```python
# BAD — another thread can insert between the check and the insert
if not db.exists(key):
    db.insert(key, value)   # race: two threads can both pass the check

# GOOD — use INSERT ... ON CONFLICT or a DB-level unique constraint
```

### 3. Lock not released on exception (missing `with`)
```python
# BAD — lock never released if exception thrown
lock.acquire()
do_something()     # if this throws, lock is held forever → deadlock
lock.release()

# GOOD
with lock:
    do_something()
```

### 4. Deadlock risk — acquiring multiple locks in inconsistent order
```python
# BAD — Thread A takes lock_a then lock_b, Thread B takes lock_b then lock_a
# → classic deadlock
with lock_a:
    with lock_b:
        ...
```

### 5. Mutable default shared across threads
```python
# BAD — all threads share the same list
class Worker:
    results = []    # class-level mutable: shared across ALL instances

    def run(self):
        self.results.append(...)   # concurrent appends → corruption
```

### 6. Non-thread-safe collections used without lock
```python
# BAD — dict operations are NOT atomic; concurrent modification causes corruption
shared_dict = {}

def update(key, val):
    if key in shared_dict:         # race between check and assignment
        shared_dict[key] = val
```

### 7. `asyncio` coroutines modifying shared state without awaited lock
```python
# BAD — two coroutines can interleave between the check and the write
async def deduct(amount):
    if balance >= amount:          # another coroutine can run here
        balance -= amount          # balance may go negative
```

### 8. `threading.Thread` without `join()` or error handling
```python
# BAD — thread runs and exits silently; exception in thread not surfaced
t = threading.Thread(target=risky_job)
t.start()
# no t.join(), no exception check
```

### 9. Singleton initialized in a racy way
```python
# BAD — two threads can both see `instance is None` simultaneously
if _instance is None:
    _instance = ExpensiveObject()
```

## Steps

1. **Find all global/class-level mutable variables** — check if they are accessed from multiple threads/tasks
2. **Find all `lock.acquire()` calls** — verify they are inside `with lock:` or have `try/finally: lock.release()`
3. **Find check-then-act patterns** — `if not exists: insert`, `if key not in dict: dict[key] = ...`
4. **Find nested lock acquisitions** — flag if order is inconsistent across call sites
5. **Find `threading.Thread` starts** — check for `.join()` and exception handling
6. **Find class-level mutable attributes** — flag if instances are used concurrently
7. **Find async functions** that modify shared state across `await` boundaries
8. **Report** with severity, pattern type, and fix

## Output Format

```
## Concurrency Check — <filename>

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 22   | `counter += 1` from multiple threads — not atomic | Use `threading.Lock()` around read-modify-write |
| blocking | 41   | `lock.acquire()` without `with` — deadlock on exception | Replace with `with self.lock:` |
| major    | 58   | Check-then-insert race: `if not db.exists(): db.insert()` | Use `INSERT ... ON CONFLICT IGNORE` |
| major    | 74   | Class-level `results = []` shared across instances | Move to `__init__`: `self.results = []` |
| major    | 89   | Async `balance -= amount` across `await` boundary | Use `asyncio.Lock()` around the critical section |
| minor    | 103  | `Thread.start()` with no `.join()` — exceptions silently lost | Add `.join()` or use `ThreadPoolExecutor` |

### Corrected Examples
\`\`\`python
# Line 22 — protect counter with lock
import threading
_lock = threading.Lock()
counter = 0

def increment():
    global counter
    with _lock:
        counter += 1

# Line 89 — asyncio lock
_balance_lock = asyncio.Lock()

async def deduct(amount):
    async with _balance_lock:
        if balance >= amount:
            balance -= amount
\`\`\`

### Summary
2 race conditions that will cause data corruption under concurrent load.
1 potential deadlock if any exception is raised inside the critical section.
```

## Example Invocation

```
/concurrency-check
/concurrency-check src/services/cache_service.py
```

## Notes

- Python's GIL does NOT protect against race conditions — `counter += 1` is still three bytecode operations
- The classic sign of a race condition: bug disappears when you add a print statement (timing change)
- Prefer `concurrent.futures.ThreadPoolExecutor` over raw `threading.Thread` — handles exceptions properly
- For async code: any `await` is a potential concurrency boundary — treat shared state modifications before/after `await` as needing protection
