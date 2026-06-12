# AI Projects Portfolio

A collection of 10 practical AI-powered tools and agents built with OpenAI's GPT-4o-mini. Each project solves a real-world problem and is fully runnable from the command line.

## Projects

| # | Project | Description | Key Tech |
|---|---------|-------------|----------|
| 1 | [pdf-chatbot-rag](./pdf-chatbot-rag/) | Chat with any PDF using RAG | Embeddings, Cosine Similarity |
| 2 | [ai-resume-analyzer](./ai-resume-analyzer/) | Score & improve your resume with AI | Function Calling, ATS Check |
| 3 | [smart-research-agent](./smart-research-agent/) | Autonomous research agent with web search | Agent Loop, Tool Use |
| 4 | [ai-code-reviewer](./ai-code-reviewer/) | Security & quality code review | Function Calling, Severity Ratings |
| 5 | [email-composer-ai](./email-composer-ai/) | Generate emails from bullet points | Tone Control, Structured Output |
| 6 | [ai-meeting-summarizer](./ai-meeting-summarizer/) | Transcript → action items & notes | Function Calling, Markdown Export |
| 7 | [sql-query-generator](./sql-query-generator/) | Natural language → SQL (6 dialects) | Schema-aware, Multi-turn |
| 8 | [unit-test-generator](./unit-test-generator/) | Auto-generate pytest suites | AST Parsing, Function Calling |
| 9 | [document-comparison-agent](./document-comparison-agent/) | Compare two docs, find conflicts | Similarity Score, Side-by-side |
| 10 | [sentiment-dashboard](./sentiment-dashboard/) | Sentiment + emotion analysis, batch CSV | Aspect-level, Batch Mode |

---

## Quick Start

All projects use Python and OpenAI. Each has its own `requirements.txt` and `.env.example`.

```bash
# 1. Go into any project folder
cd pdf-chatbot-rag

# 2. Set up virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set your API key
cp .env.example .env
# Edit .env — add your OpenAI API key

# 5. Run
python chatbot.py document.pdf
```

---

## Project Summaries

### 1. PDF Chatbot (RAG)
> `python chatbot.py document.pdf`

Implements Retrieval-Augmented Generation from scratch. Chunks your PDF, generates embeddings, and retrieves the top-4 most relevant chunks per query using cosine similarity. GPT-4o-mini answers using only that context. Embeddings are cached locally.

### 2. AI Resume Analyzer
> `python analyzer.py resume.pdf "Senior Engineer"`

Structured resume scoring using function calling — scores 1-100, checks ATS compatibility, lists skills, identifies gaps, and gives specific improvement suggestions. Rich terminal dashboard.

### 3. Smart Research Agent
> `python agent.py "topic" deep`

Autonomous multi-step agent: searches DuckDuckGo, fetches and reads web pages, summarizes content, and compiles a markdown report without human intervention. Saves timestamped reports.

### 4. AI Code Reviewer
> `python reviewer.py app.py "context"`

Reviews code for security vulnerabilities (SQL injection, XSS, hardcoded secrets), bugs, performance issues, and best practices. Severity-tagged findings (Critical/High/Medium/Low) with specific fixes and refactored snippets.

### 5. Email Composer AI
> `python composer.py`

Converts bullet points to polished emails with 5 tone options (formal, friendly, assertive, empathetic, persuasive) and 3 length controls. Returns the email, 2 subject line alternatives, and follow-up suggestions.

### 6. AI Meeting Notes Summarizer
> `python summarizer.py transcript.txt`

Turns raw meeting transcripts into structured notes: executive summary, action items table (task/owner/due), decisions, blockers, key topics, and sentiment. Auto-saves as a shareable markdown file.

### 7. SQL Query Generator
> `python generator.py "show top customers by revenue last 90 days"`

Natural language to SQL across 6 dialects (PostgreSQL, MySQL, SQLite, SQL Server, BigQuery, Snowflake). Schema-aware when you provide CREATE TABLE statements. Multi-turn session with history.

### 8. AI Unit Test Generator
> `python generator.py my_module.py`

Reads a Python file, parses function signatures via AST, then generates a complete pytest suite covering happy paths, edge cases, boundary values, and error conditions. Uses parametrize and mocking.

### 9. Document Comparison Agent
> `python compare.py doc1.pdf doc2.txt "contract"`

Compares two documents side-by-side: similarity score (0-100), common themes, unique content per doc, direct conflicts/contradictions, tone differences, and a recommendation on which to use.

### 10. Sentiment Analysis Dashboard
> `python dashboard.py "text"` or `python dashboard.py --batch reviews.csv`

Nuanced sentiment analysis: 4 classes, -1.0 to +1.0 score, specific emotions with intensity, aspect-level breakdown, and key phrases. Batch mode processes CSV files with a progress bar and exports results.

---

## Running All Tests

Each project includes a `test_*.py` file with sanity tests that run **without an API key**:

```bash
python pdf-chatbot-rag/test_chatbot.py
python ai-resume-analyzer/test_analyzer.py
python smart-research-agent/test_agent.py
python ai-code-reviewer/test_reviewer.py
python email-composer-ai/test_composer.py
python ai-meeting-summarizer/test_summarizer.py
python sql-query-generator/test_generator.py
python unit-test-generator/test_generator.py
python document-comparison-agent/test_compare.py
python sentiment-dashboard/test_dashboard.py
```

## Tech Stack

- **Language:** Python 3.10+
- **LLM:** OpenAI GPT-4o-mini
- **Embeddings:** OpenAI text-embedding-3-small (Project 1)
- **Structured Outputs:** OpenAI Function Calling (all projects)
- **Terminal UI:** Rich
- **PDF Parsing:** PyPDF2
- **Web Scraping:** BeautifulSoup4 (Project 3)
- **Code Analysis:** Python `ast` module (Project 8)

---

*Built with OpenAI GPT-4o-mini · Python 3.10+*
