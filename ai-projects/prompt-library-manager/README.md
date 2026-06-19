# Prompt Library Manager

A versioned prompt registry with CLI management. Store, version, test, and A/B compare prompts — keeping your best-performing system prompts organized and auditable.

## What It Does

- **Version control** — MD5-hashed versions, full history per prompt
- **Tag-based organization** — find prompts by use case
- **Live testing** — run a prompt against GPT and capture results
- **A/B comparison** — test two versions side-by-side on the same input
- **JSON storage** — `prompt_library.json` — simple, portable, git-trackable

## Quick Start

```bash
cd prompt-library-manager
pip install -r requirements.txt
cp .env.example .env   # add your OPENAI_API_KEY

# Add a prompt:
python manager.py add

# List all prompts:
python manager.py list

# Show a prompt + history:
python manager.py show <name>

# Test a prompt:
python manager.py test <name>

# Compare two versions:
python manager.py compare <name>
```

## Sample Output

```
Prompt Library — 4 prompts

  summarizer_v1    [summarization, docs]     2 versions    last: 2024-06-01
  code_reviewer    [code, review, security]  3 versions    last: 2024-06-10  ← current
  email_composer   [email, tone]             1 version     last: 2024-05-20
  adr_writer       [architecture, decisions] 2 versions    last: 2024-06-05

A/B Test — code_reviewer (v1 vs v3):
  Input: "Review this Python function..."
  v1 score: 72  v3 score: 91  → v3 wins ✅
```

## Run Tests (No API Key Required)

```bash
python test_manager.py
```

## Tech Stack

- OpenAI GPT-4o-mini for prompt testing
- MD5 8-char version hashes
- JSON file storage — no database required
