---
description: Scan code for security vulnerabilities — hardcoded secrets, injection risks (SQL/cmd/path), insecure crypto, broken auth patterns, and OWASP Top 10. Use before every release or security review.
---

# Security Scan

Perform a targeted security scan on code — find exploitable vulnerabilities, insecure patterns, and compliance risks before they reach production.

## When to Use

- Before any production release
- During a security review or penetration test prep
- When onboarding to a codebase to assess its security posture
- After adding new endpoints, auth flows, or external integrations
- Any code that handles user input, credentials, or payments

## What to Check

### 1. Hardcoded secrets
```python
# BAD
API_KEY = "sk-abc123xyz"
password = "admin1234"
conn = psycopg2.connect("host=db user=admin password=secret123")
```

### 2. SQL Injection
```python
# BAD
query = f"SELECT * FROM users WHERE email = '{email}'"
cursor.execute(f"DELETE FROM orders WHERE id = {order_id}")

# GOOD
cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
```

### 3. Command Injection
```python
# BAD
os.system(f"convert {filename} output.pdf")   # filename could be "x; rm -rf /"
subprocess.call(f"ls {user_path}", shell=True)

# GOOD
subprocess.run(["convert", filename, "output.pdf"])
```

### 4. Path Traversal
```python
# BAD — user controls filename → can read /etc/passwd
path = f"/uploads/{user_filename}"
open(path).read()

# GOOD
safe_path = Path("/uploads") / Path(user_filename).name
```

### 5. Insecure hashing / crypto
```python
# BAD — MD5/SHA1 for passwords or security tokens
hashlib.md5(password.encode()).hexdigest()
hashlib.sha1(token.encode()).hexdigest()

# GOOD
import bcrypt; bcrypt.hashpw(password.encode(), bcrypt.gensalt())
```

### 6. Insecure deserialization
```python
# BAD — pickle/eval from untrusted input can execute arbitrary code
data = pickle.loads(user_input)
result = eval(user_expression)
yaml.load(data)                 # use yaml.safe_load()
```

### 7. Missing authentication / authorization checks
```python
# BAD — any user can access any order
@app.route("/orders/<order_id>")
def get_order(order_id):
    return db.get_order(order_id)   # no ownership check!
```

### 8. Sensitive data in logs
```python
# BAD
log.info(f"Login attempt: user={email} password={password}")
log.debug(f"Payment processed: card={card_number}")
```

### 9. Insecure random (predictable tokens)
```python
# BAD — random is not cryptographically secure
token = str(random.randint(100000, 999999))

# GOOD
token = secrets.token_urlsafe(32)
```

### 10. Open redirect
```python
# BAD — attacker can redirect to phishing site
return redirect(request.args.get("next"))

# GOOD — validate against allowlist
if next_url in ALLOWED_REDIRECTS:
    return redirect(next_url)
```

## Steps

1. **Scan for hardcoded strings** matching secret patterns (keys, passwords, tokens, connection strings)
2. **Find all string interpolation into queries** — SQL, shell commands, file paths
3. **Find `eval`, `exec`, `pickle.loads`, `yaml.load`** (not `safe_load`)
4. **Find `os.system`, `subprocess` with `shell=True`** and user-controlled input
5. **Find `hashlib.md5`, `hashlib.sha1`** used for security purposes
6. **Find all `log.*` calls** — check if sensitive fields are being logged
7. **Find `random`** used for security tokens/OTPs (should be `secrets`)
8. **Find route handlers** — check each one for authentication and authorization
9. **Report** with severity, CWE/OWASP reference where applicable, and fix

## Output Format

```
## Security Scan — <filename>

### Findings

| Severity | Line | Vulnerability | OWASP | Fix |
|----------|------|--------------|-------|-----|
| critical | 14   | SQL built with f-string | A03:Injection | Use parameterized query |
| critical | 28   | API key hardcoded in source | A02:Crypto Failures | Move to env var / secrets vault |
| critical | 52   | `eval(user_input)` — RCE risk | A03:Injection | Reject or use ast.literal_eval for safe types only |
| high     | 71   | `hashlib.md5` for password hashing | A02:Crypto Failures | Use bcrypt or argon2 |
| high     | 88   | `subprocess.call(shell=True)` with user input | A03:Injection | Use list form, no shell=True |
| high     | 103  | No auth check on `/admin/users` route | A01:Broken Access Control | Add `@require_role("admin")` |
| medium   | 117  | Password logged at INFO level | A09:Logging Failures | Remove password from log call |
| medium   | 134  | `random.randint` for OTP — predictable | A02:Crypto Failures | Use `secrets.randbelow(900000) + 100000` |

### Summary
3 critical vulnerabilities requiring immediate fix before deployment.
2 high-severity issues likely exploitable by authenticated users.
```

## Example Invocation

```
/security-scan
/security-scan src/api/auth.py
/security-scan src/  (scans all files in directory)
```

## Notes

- Hardcoded secrets must be treated as compromised immediately — rotate them
- `eval` and `pickle.loads` on user input = arbitrary code execution, always `critical`
- For JS/TS: also check `innerHTML`, `dangerouslySetInnerHTML`, `document.write` (XSS vectors)
- This is a static analysis pass — it does NOT replace a full penetration test
