# AI Code Reviewer

An AI-powered code reviewer that analyzes any code file for security vulnerabilities, bugs, performance issues, and best practice violations. Gives structured, prioritized findings with specific fixes — not just vague suggestions.

## Features

- **Security Analysis** — SQL injection, XSS, hardcoded secrets, insecure patterns
- **Bug Detection** — Logic errors, null pointer risks, off-by-one errors
- **Performance Review** — N+1 queries, inefficient loops, memory issues
- **Best Practices** — Code style, naming, error handling, documentation
- **Severity Levels** — Critical / High / Medium / Low for prioritization
- **Auto Fix Suggestions** — Refactored code snippet for critical issues
- **Language Detection** — Auto-detects Python, JS, Go, Java, Rust, and more
- **Stdin Support** — Pipe code directly from terminal

## Setup

```bash
cd ai-code-reviewer

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

```bash
# Review a file
python reviewer.py app.py

# Review with context for better analysis
python reviewer.py views.py "Django REST API — handles user authentication"

# Pipe code from stdin
cat suspicious_code.js | python reviewer.py -

# Review with context via stdin
echo "$(cat main.go)" | python reviewer.py - "Go HTTP server handler"
```

**Sample output:**
```
Reviewing: app.py

╭── Code Review Report ───────────────────╮
│  Language: python                       │
│  Score: 45/100                          │
╰─────────────────────────────────────────╯

╭── Security Issues ──────────────────────╮
│  🔴 CRITICAL  SQL injection via f-string  →  Use parameterized queries
│  🟠 HIGH      Password stored in plaintext →  Use bcrypt/argon2
╰─────────────────────────────────────────╯

╭── Suggested Fix ────────────────────────╮
│  cursor.execute(                        │
│      "SELECT * FROM users WHERE id=%s", │
│      (user_id,)                         │
│  )                                      │
╰─────────────────────────────────────────╯
```

## Run Tests

```bash
python test_reviewer.py
```

No API key needed.

## Supported Languages

Python, JavaScript, TypeScript, Go, Java, Rust, C/C++, Ruby, PHP, C#, Bash, SQL — auto-detected from file extension.

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Structured Output | OpenAI Function Calling |
| Terminal UI | Rich (syntax highlighting, tables, panels) |

## Project Structure

```
ai-code-reviewer/
├── reviewer.py         # Main application
├── test_reviewer.py    # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- Code is truncated to 8000 characters for very large files. For large codebases, review individual modules.
- The `context` argument significantly improves review quality — tell the reviewer what the code is supposed to do.
