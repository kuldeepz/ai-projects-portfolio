# AI Resume Analyzer

An intelligent resume analyzer powered by GPT-4o-mini that extracts skills, scores your resume, identifies gaps, and gives you specific actionable improvements — plus an ATS (Applicant Tracking System) compatibility check.

## Features

- **Skill Extraction** — Automatically identifies technical and soft skills
- **Overall Score (1-100)** — Resume quality assessment
- **ATS Score (1-100)** — Checks how well the resume will parse in automated screening systems
- **Strengths Analysis** — What you're doing well
- **Gap Identification** — Skills and experience areas that are missing
- **Actionable Improvements** — Specific steps to improve your resume
- **Target Role Alignment** — Optionally specify a target role for tailored feedback
- **Supports PDF and TXT** — Works with common resume formats

## Setup

```bash
cd ai-resume-analyzer

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key to .env
```

## Usage

```bash
# Basic analysis
python analyzer.py resume.pdf

# With target role for focused feedback
python analyzer.py resume.pdf "Senior Data Engineer"

# Works with TXT files too
python analyzer.py resume.txt "Machine Learning Engineer"
```

**Sample output:**
```
╭─────── Resume Analysis Report ─────────╮
│  Jane Smith                             │
│  Backend Engineer · 4 yrs exp          │
╰─────────────────────────────────────────╯

╭─── Scores ─────────────────────────────╮
│  Overall Score    72/100               │
│  ATS Score        68/100               │
╰─────────────────────────────────────────╯

╭─── Strengths ──────────────────────────╮
│  ✔ Clear project impact with metrics   │
│  ✔ Strong Python and backend stack     │
╰─────────────────────────────────────────╯

╭─── Actionable Improvements ────────────╮
│  → Add quantified results to each role │
│  → Include cloud certifications        │
╰─────────────────────────────────────────╯
```

## Run Tests

```bash
python test_analyzer.py
```

No API key needed for tests.

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Structured Output | OpenAI Function Calling |
| PDF Parsing | PyPDF2 |
| Terminal UI | Rich |

## Project Structure

```
ai-resume-analyzer/
├── analyzer.py         # Main application
├── test_analyzer.py    # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```

## How It Works

Uses OpenAI **function calling** (structured outputs) to ensure the analysis always returns a consistent JSON schema — no parsing fragile free-text responses. The model is prompted as an expert recruiter and returns a typed analysis object every time.
