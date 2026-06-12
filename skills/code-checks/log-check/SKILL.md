---
description: Audit logging quality — missing error logs, sensitive data in log messages, wrong log levels, missing correlation IDs, and logs that make production debugging impossible. Use before merging any service code.
---

# Log Check

Review logging for completeness, correctness, and safety — find missing error logs, sensitive data exposure, wrong severity levels, and structural issues that make production debugging painful.

## When to Use

- Before merging any service, API handler, or background worker
- When debugging in production is harder than it should be (no logs, unhelpful messages)
- After a production incident where logs were missing or useless
- Code review of error-handling paths and request/response flows

## What to Check

### 1. Missing log on exception
```python
# BAD — exception caught and handled, but nothing logged
try:
    process_payment(order)
except PaymentError as e:
    return {"error": "payment failed"}   # what error? which order? when?

# GOOD
except PaymentError as e:
    log.error("Payment failed for order %s: %s", order.id, e, exc_info=True)
    return {"error": "payment failed"}
```

### 2. Sensitive data in log messages
```python
# BAD — PII, credentials, card numbers in logs
log.info(f"User login: email={email} password={password}")
log.debug(f"Processing card: number={card.number} cvv={card.cvv}")
log.info(f"API call with token={api_key}")
```

### 3. Wrong log level
```python
# BAD — errors logged at DEBUG or INFO; routine events at ERROR
log.debug(f"Database connection failed: {e}")       # should be ERROR
log.error(f"User {user_id} logged in successfully") # should be INFO
log.warning(f"Application started")                 # should be INFO
```

### 4. Log message missing context (useless in production)
```python
# BAD — no context: which user? which request? what data?
log.error("Operation failed")
log.info("Done")
log.warning("Retrying")

# GOOD
log.error("Payment processing failed: user=%s order=%s attempt=%d/%d err=%s",
          user_id, order_id, attempt, max_retries, e)
```

### 5. Missing request correlation ID / trace ID
```python
# BAD — no way to trace a request through multiple log lines
@app.route("/checkout")
def checkout():
    log.info("Checkout started")
    result = process(cart)
    log.info("Checkout complete")
    # Which user? Which request? Logs can't be correlated
```

### 6. `print()` used instead of logger in production code
```python
# BAD — print() bypasses log levels, formatting, and log routing
print("Processing order:", order_id)
print("Error:", e)
```

### 7. Exception logged without `exc_info=True` — stack trace missing
```python
# BAD — log line appears but no stack trace in the log file
except Exception as e:
    log.error(f"Failed: {e}")          # no traceback

# GOOD
    log.error("Failed: %s", e, exc_info=True)   # includes full traceback
```

### 8. Logging in a tight loop — performance risk
```python
# BAD — one log line per item × 1M items = log flooding
for item in million_items:
    log.debug(f"Processing item {item.id}")
```

### 9. Log format uses f-string (lazy evaluation defeated)
```python
# BAD — f-string evaluated even when log level is disabled
log.debug(f"State: {expensive_serialize(obj)}")

# GOOD — % formatting is lazy: only evaluated if DEBUG is enabled
log.debug("State: %s", expensive_serialize(obj))
```

## Steps

1. **Find all `except` blocks** — check each has a `log.error()` or `log.warning()` call
2. **Find all `log.*` calls** — check for PII fields: email, password, token, card, SSN, phone
3. **Find `log.debug/info` on errors** and `log.error/warning` on routine events — flag mismatched levels
4. **Find log messages with no contextual fields** (user_id, request_id, order_id, etc.)
5. **Find `print()` in non-test code** — flag every instance
6. **Find `log.error(f"...")`** — verify `exc_info=True` is present when inside except block
7. **Find logging inside `for`/`while` loops** over large collections — flag as performance risk
8. **Find f-string log calls** — suggest switching to `%` formatting
9. **Report** with severity, line, issue, and fix

## Output Format

```
## Log Check — <filename>

### Findings

| Severity | Line | Issue | Fix |
|----------|------|-------|-----|
| blocking | 34   | `password` logged at INFO level — PII/secret exposure | Remove password from log; log `user_id` only |
| blocking | 52   | Exception caught with no log — silent failure | Add `log.error("...", exc_info=True)` |
| major    | 18   | `log.debug("DB connection failed")` — wrong level | Change to `log.error(...)` |
| major    | 67   | `log.error("Operation failed")` — no context | Add user_id, request_id, operation name |
| major    | 81   | `log.error(f"err: {e}")` inside except — no stack trace | Add `exc_info=True` |
| major    | 95   | `print("Processing:", id)` in service code | Replace with `log.info(...)` |
| minor    | 110  | `log.debug(f"Item: {expensive_fn()}")` — eager evaluation | Use `log.debug("Item: %s", expensive_fn())` |
| minor    | 128  | `log.debug(...)` inside loop over `all_events` — log flood risk | Log summary after loop instead |

### Summary
2 sensitive data exposures in log messages — must fix before release.
2 silent exception handlers — will make production incidents undebuggable.
```

## Example Invocation

```
/log-check
/log-check src/api/payment_handler.py
```

## Notes

- PII in logs is a compliance violation (GDPR, PCI-DSS) — always log IDs, never raw values
- Every `except` block that doesn't re-raise MUST log with `exc_info=True`
- Correlation IDs: inject a `request_id` at the entry point and pass it through (or use `contextvars`)
- Structured logging (`structlog`, `python-json-logger`) is preferred over plain text for searchability
- Log levels guide: `DEBUG` = dev tracing, `INFO` = normal events, `WARNING` = unexpected but handled, `ERROR` = failure that was caught, `CRITICAL` = system cannot continue
