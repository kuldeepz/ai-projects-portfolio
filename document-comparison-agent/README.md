# Document Comparison Agent

Compare any two documents side-by-side using AI. Identifies common themes, what's unique to each, direct conflicts/contradictions, and gives a similarity score with a recommendation on which document to use.

## Features

- **Similarity Score (0-100)** — How similar the two documents are
- **Side-by-side summaries** — Quick overview of each document
- **Common Themes** — Topics covered in both
- **Unique Content** — What each document has that the other doesn't
- **Conflict Detection** — Direct contradictions between the two documents
- **Tone Comparison** — Writing style and formality differences
- **Actionable Recommendation** — Which document to prefer for a given purpose
- **Supports PDF and TXT** — Any combination of file types

## Setup

```bash
cd document-comparison-agent

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

```bash
# Compare two text files
python compare.py proposal_v1.txt proposal_v2.txt

# Compare PDFs with context for better analysis
python compare.py contract_2022.pdf contract_2024.pdf "software license agreement"

# Compare mixed file types
python compare.py requirements.txt requirements_updated.md "feature specification"
```

**Sample output:**
```
╭── Comparison Results ───────────────────────────────────────────╮
│  Document Comparison Report                                      │
│  contract_2022.pdf vs contract_2024.pdf                         │
│  Similarity: ████████████░░░░░░░░ 72%                           │
╰─────────────────────────────────────────────────────────────────╯

╭── Conflicts & Disagreements ────────────────────────────────────╮
│  Topic          contract_2022       contract_2024               │
│  Termination    60-day notice       30-day notice               │
│  Liability cap  $50,000             $100,000                    │
╰─────────────────────────────────────────────────────────────────╯

╭── Recommendation ───────────────────────────────────────────────╮
│  Use contract_2024 for new agreements — it includes updated     │
│  liability terms and remote work provisions.                    │
╰─────────────────────────────────────────────────────────────────╯
```

## Use Cases

- **Contract review** — Compare old vs new version to spot changes
- **Research papers** — Find how two papers agree or disagree
- **Policy documents** — Identify conflicts between policies
- **Requirements docs** — Track what changed between versions
- **Job descriptions** — Compare two roles before applying

## Run Tests

```bash
python test_compare.py
```

No API key needed.

## Tech Stack

| Component | Technology |
|---|---|
| LLM | OpenAI GPT-4o-mini |
| Structured Output | OpenAI Function Calling |
| PDF Parsing | PyPDF2 |
| Terminal UI | Rich |

## Project Structure

```
document-comparison-agent/
├── compare.py          # Main application
├── test_compare.py     # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- Each document is truncated to 5000 characters for the comparison prompt
- For very long documents, consider comparing specific sections
- The `context` argument significantly improves conflict detection — use it!
