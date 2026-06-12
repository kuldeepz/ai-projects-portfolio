# AI Meeting Notes Summarizer

Turn raw meeting transcripts into structured, actionable notes in seconds. Extracts action items, decisions, blockers, and key topics — formatted as a clean markdown report ready to share.

## Features

- **Executive Summary** — 3-4 sentence meeting overview
- **Action Items Table** — Task, owner, and due date extracted automatically
- **Decisions Made** — Concrete decisions explicitly recorded
- **Key Topics** — Each discussed topic with a 1-2 sentence summary
- **Blockers & Risks** — Issues raised during the meeting
- **Sentiment Detection** — Overall meeting tone (positive/neutral/tense/mixed)
- **Auto-save to Markdown** — Timestamped `.md` file saved after every run
- **Pipe support** — Works with `cat transcript.txt | python summarizer.py -`

## Setup

```bash
cd ai-meeting-summarizer

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

```bash
# Summarize a transcript file
python summarizer.py sprint_planning.txt

# Pipe from stdin
cat meeting_recording_transcript.txt | python summarizer.py -
```

**Input format:** Plain text transcript — speaker labels are helpful but not required:
```
Alice: Good morning everyone. Let's start with the sprint review.
Bob: We completed 11 out of 13 story points this sprint.
Alice: Great. Any blockers for next sprint?
Bob: We're waiting on the new API credentials from infra.
Alice: I'll follow up with them today. Bob, can you document the API spec by Friday?
...
```

**Sample output:**
```
╭── Meeting Notes ─────────────────────────────╮
│  Sprint Planning Q3 · Attendees: Alice, Bob  │
│  Duration: ~30 min  ● Positive               │
╰──────────────────────────────────────────────╯

╭── Decisions Made ────╮   ╭── Action Items ──────────────────────────────╮
│  ✔ Use feature flags │   │  Task              Owner   Due               │
╰──────────────────────╯   │  Document API spec  Bob     Friday           │
                           ╰──────────────────────────────────────────────╯
```

## Run Tests

```bash
python test_summarizer.py
```

No API key needed.

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Structured Output | OpenAI Function Calling |
| Terminal UI | Rich |

## Project Structure

```
ai-meeting-summarizer/
├── summarizer.py       # Main application
├── test_summarizer.py  # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```

## Tips

- Longer transcripts (>12,000 chars) are trimmed — split very long meetings into sections
- Speaker labels like `Alice:` or `[Alice]` improve attendee detection
- Works with AI-generated transcripts from Zoom, Teams, or Otter.ai
