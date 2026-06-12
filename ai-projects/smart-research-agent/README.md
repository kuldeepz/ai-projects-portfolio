# Smart Research Agent

An autonomous AI research agent that searches the web, reads pages, and compiles a structured markdown report — all in one command. Built with OpenAI function calling and a multi-step agent loop.

## How It Works

The agent operates in an autonomous loop:

```
User Topic
    ↓
GPT-4o-mini (decides next action)
    ↓  ↓  ↓
  search  fetch  summarize  ← tools
    ↓
(repeat until enough info gathered)
    ↓
Compile & write markdown report
    ↓
Save to file
```

The agent decides **on its own** when it has enough information and stops calling tools, then writes the final report.

## Setup

```bash
cd smart-research-agent

python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

pip install -r requirements.txt

cp .env.example .env
# Add your OpenAI API key
```

## Usage

```bash
# Standard depth (2-3 searches, ~500 word report)
python agent.py "Large Language Models in healthcare 2024"

# Quick mode (1 search, brief summary)
python agent.py "Rust programming language adoption" quick

# Deep research (3-4 searches, 800+ word report)
python agent.py "Climate change adaptation strategies" deep
```

**The agent shows its work as it runs:**
```
Agent starting research on: Large Language Models in healthcare 2024

  → Tool: web_search   LLMs in healthcare 2024
  → Tool: fetch_page   https://...
  → Tool: summarize_text   key findings
  → Tool: web_search   clinical AI safety regulations
  → Tool: fetch_page   https://...

╭── Research Report ─────────────────────╮
│  # LLMs in Healthcare 2024             │
│  ## Introduction                       │
│  ...                                   │
╰─────────────────────────────────────────╯

Report saved to: report_LLMs_in_healthcare_20240612_143022.md
```

## Run Tests

```bash
python test_agent.py
```

## Tech Stack

| Component | Technology |
|---|---|
| LLM & Agent | OpenAI GPT-4o-mini + Function Calling |
| Web Search | DuckDuckGo HTML (no API key needed) |
| Page Fetching | urllib + BeautifulSoup |
| Text Summarization | GPT-4o-mini |
| Report Format | Markdown |

## Available Tools

| Tool | Description |
|---|---|
| `web_search` | Search DuckDuckGo, returns titles + URLs + snippets |
| `fetch_page` | Fetches and cleans any web page text |
| `summarize_text` | Summarizes a page focused on the research topic |

## Project Structure

```
smart-research-agent/
├── agent.py            # Agent loop + tool implementations
├── test_agent.py       # Sanity tests
├── requirements.txt
├── .env.example
└── README.md
```

## Notes

- Uses DuckDuckGo for search — no additional API keys needed
- Reports are auto-saved as markdown files with timestamps
- Deep mode typically makes 6-8 tool calls before writing the report
