# AI Email Composer

Turn bullet points into polished, professional emails in seconds. Choose your tone, length, and purpose — the AI handles the rest. Includes follow-up suggestions and alternative subject lines.

## Features

- **5 Tone Options** — Formal, Friendly, Assertive, Empathetic, Persuasive
- **3 Length Controls** — Short (<100w), Medium (100-200w), Long (200-350w)
- **Alternative Subject Lines** — 2 options per email for A/B testing
- **Follow-up Suggestions** — Next steps after the email is sent
- **Interactive Mode** — Guided prompts for easy use
- **CLI Mode** — Scriptable for batch email generation
- **Save to File** — Export the final email as a `.txt` file

## Setup

```bash
cd email-composer-ai

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

### Interactive Mode (recommended for one-off emails)

```bash
python composer.py
```

You'll be guided through:
1. Tone selection (1-5)
2. Length preference
3. Email purpose
4. Recipient context
5. Your bullet points

### CLI Mode (for scripting / batch use)

Create a file with your bullet points:
```
# points.txt
Project X delivered ahead of schedule
Budget was 10% under estimate
Team is ready for Project Y kickoff
Request sign-off to proceed
```

```bash
python composer.py points.txt \
  --tone formal \
  --length medium \
  --purpose "project update and approval request" \
  --recipient "executive stakeholder" \
  --sender "Kuldeep Rao"
```

**Sample output:**
```
╭── Subject Line ─────────────────────────╮
│  Project X Delivered — Approval Needed  │
│  for Project Y Kickoff                  │
╰─────────────────────────────────────────╯

╭── Email Body ───────────────────────────╮
│  Dear [Name],                           │
│                                         │
│  I'm pleased to share that Project X    │
│  has been delivered ahead of schedule   │
│  and 10% under budget...               │
╰─────────────────────────────────────────╯

╭── Follow-up Suggestions ────────────────╮
│  → Schedule Project Y kickoff meeting   │
│  → Send detailed project Y scope doc    │
╰─────────────────────────────────────────╯
```

## Run Tests

```bash
python test_composer.py
```

No API key needed.

## Tone Guide

| Tone | Best For |
|---|---|
| **Formal** | Executives, clients, official requests |
| **Friendly** | Colleagues, team updates, collaboration |
| **Assertive** | Negotiations, follow-ups, deadlines |
| **Empathetic** | Apologies, difficult news, sensitive topics |
| **Persuasive** | Pitches, proposals, calls to action |

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Structured Output | OpenAI Function Calling |
| Terminal UI | Rich |

## Project Structure

```
email-composer-ai/
├── composer.py         # Main application (interactive + CLI)
├── test_composer.py    # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```
