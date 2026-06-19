---
description: Detect async/await bugs — missing awaits, blocking calls inside async functions, unhandled async exceptions, and fire-and-forget anti-patterns. Use before merging any async code.
---

# Async Check

Scan code for async/await correctness issues — the class of bugs that are silent at write time but cause hangs, race conditions, or swallowed errors at runtime.

## When to Use

- Before merging any code that uses `async`/`await` (Python, JS/TS, C#)
- When debugging unexpected hangs, timeouts, or missing error messages
- After adding concurrency to a previously synchronous module
- Code review of async-heavy services (API handlers, background workers, data pipelines)

## What to Check

### 1. Missing `await`
```python
# BAD — coroutine created but never awaited; silently does nothing
result = fetch_data(url)        # should be: await fetch_data(url)

# BAD (JS) — Promise returned but not awaited
const data = getUser(id)        # should be: await getUser(id)
```

### 2. Blocking calls inside `async` functions
```python
# BAD — blocks the entire event loop
async def handler():
    time.sleep(5)               # use: await asyncio.sleep(5)
    data = requests.get(url)    # use: await aiohttp or httpx async client
    result = open(path).read()  # use: aiofiles or run_in_executor
```

### 3. Unhandled exceptions in tasks / fire-and-forget
```python
# BAD — exception disappears silently
asyncio.create_task(risky_operation())

# GOOD
task = asyncio.create_task(risky_operation())
task.add_done_callback(lambda t: t.exception() and log.error(...))
```

### 4. Mixing sync and async incorrectly
```python
# BAD — calling async function from sync context without event loop
def sync_fn():
    result = async_fn()         # returns coroutine object, not result
```

### 5. async for / async with missing `async`
```python
# BAD
with aiofiles.open(path) as f:  # missing: async with
for item in async_generator():   # missing: async for
```

### 6. Not awaiting `__aenter__` / `__aexit__` context managers

### 7. Concurrent tasks without `gather` or `TaskGroup` (sequential when parallel was intended)
```python
# BAD — sequential despite being async
result1 = await fetch(url1)
result2 = await fetch(url2)

# GOOD — truly parallel
result1, result2 = await asyncio.gather(fetch(url1), fetch(url2))
```

## Steps

1. **Read the code** — identify all `async def`, `await`, `create_task`, `gather`, context managers
2. **Check each async function** for blocking stdlib calls (`time.sleep`, `requests`, `open`, `subprocess`)
3. **Find every coroutine call** — verify it is awaited
4. **Find every `create_task`** — verify exception handling is attached
5. **Find sequential awaits** that could be parallelized with `gather`
6. **Check `async with` / `async for`** — verify `async` keyword is present
7. **Report all findings** with severity and fix

## Output Format

```
## Async Check — <filename>

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 24   | `time.sleep(3)` inside async fn — blocks event loop | `await asyncio.sleep(3)` |
| blocking | 31   | `requests.get()` inside async fn | Replace with `await httpx.AsyncClient().get()` |
| major    | 45   | Coroutine `process()` called but not awaited | Add `await` |
| major    | 67   | `create_task(job())` — no exception handler | Add `.add_done_callback` |
| minor    | 82   | Sequential awaits on independent calls — could use `gather` | `await asyncio.gather(a(), b())` |

### Clean Examples
\`\`\`python
# Corrected line 24
await asyncio.sleep(3)

# Corrected line 31
async with httpx.AsyncClient() as client:
    response = await client.get(url)
\`\`\`

### Summary
3 blocking calls will freeze the event loop under load.
1 fire-and-forget task will silently swallow exceptions.
```

## Example Invocation

```
/async-check
/async-check src/workers/data_pipeline.py
```

## Notes

- Blocking calls in async are the #1 async bug — they work fine in tests but kill throughput in production
- `asyncio.get_event_loop().run_until_complete()` inside an already-running loop raises `RuntimeError` — flag it
- For JS/TS: also check for `async` functions that never use `await` (pointless async)
- Language support: Python (`asyncio`, `trio`), JavaScript/TypeScript (`Promise`, `async/await`), C# (`Task`, `async/await`)
