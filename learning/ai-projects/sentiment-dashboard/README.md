# Sentiment Analysis Dashboard

Analyze the emotional tone of any text with nuanced, aspect-level insights — not just positive/negative, but specific emotions, key phrases, and topic-by-topic sentiment. Supports both single-text and batch CSV analysis.

## Features

- **4 Sentiment Classes** — Positive, Negative, Neutral, Mixed
- **Emotion Detection** — Joy, frustration, trust, fear, surprise, etc. with intensity levels
- **Aspect-level Sentiment** — Breaks down sentiment per topic mentioned (product quality, customer service, pricing, etc.)
- **Sentiment Score** — Precise -1.0 to +1.0 floating point score
- **Confidence % ** — How certain the model is about its classification
- **Key Phrases** — The exact phrases that drove the sentiment
- **Batch Mode** — Analyze entire CSV files with a progress bar and dashboard
- **CSV Export** — Batch results saved as structured CSV

## Setup

```bash
cd sentiment-dashboard

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

### Single Text Analysis

```bash
python dashboard.py "The new feature is great but the onboarding process was really confusing."
```

### Batch Analysis (CSV)

Create a CSV with a `text` column (optionally a `label` column):
```csv
text,label
"Absolutely love this product! Best purchase I've made.",review_1
"Shipping was fast but the item was damaged on arrival.",review_2
"Works as described. Nothing special.",review_3
```

```bash
python dashboard.py --batch reviews.csv
```

**Single analysis output:**
```
╭── Sentiment Analysis ───────────────────────────────────╮
│  🤔 MIXED                                               │
│  Score: ░░░░░░░░░░░░─────────── +0.15                  │
│  Confidence: 82%                                        │
╰─────────────────────────────────────────────────────────╯

╭── Emotions Detected ────╮   ╭── Key Phrases ───────────────────────╮
│  Emotion    Intensity   │   │  "great"  |  "really confusing"      │
│  Approval   HIGH        │   ╰──────────────────────────────────────╯
│  Confusion  MEDIUM      │
╰─────────────────────────╯

╭── Aspect-Level Sentiment ──────────────────────────────╮
│  Aspect        Sentiment   Reason                       │
│  New feature   positive    "great" directly applied     │
│  Onboarding    negative    described as "confusing"     │
╰────────────────────────────────────────────────────────╯
```

**Batch dashboard output:**
```
╭── Batch Analysis Dashboard ─────────────────────────────╮
│  Total analyzed    25                                   │
│  Average score     ████████████░░░░░░░░ +0.31           │
│  Positive          14 (56%)                             │
│  Negative          6 (24%)                              │
│  Mixed             5 (20%)                              │
╰─────────────────────────────────────────────────────────╯
```

## Run Tests

```bash
python test_dashboard.py
```

No API key needed.

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Structured Output | OpenAI Function Calling |
| Terminal UI | Rich (tables, panels, progress bars) |
| Batch I/O | Python csv module |

## Project Structure

```
sentiment-dashboard/
├── dashboard.py        # Main application
├── test_dashboard.py   # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```

## CSV Format for Batch Mode

| Column | Required | Notes |
|---|---|---|
| `text` | Yes | The text to analyze (also accepts `review` or `content`) |
| `label` | No | Display label in results (falls back to first 40 chars of text) |

Results are exported as CSV with: index, label, sentiment, score, confidence, top_emotion, summary.
