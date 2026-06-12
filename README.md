# AI Projects Portfolio

A collection of 25 practical AI-powered tools and agents built with OpenAI's GPT-4o-mini. Each project solves a real-world problem and is fully runnable from the command line.

## Projects — Core AI Tools (1–10)

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

## Projects — Advanced AI Skills (11–25)

> DevOps, Engineering Leadership, Architecture & MLOps skills for AI Leads.

| # | Project | Description | Key Tech |
|---|---------|-------------|----------|
| 11 | [ado-workitem-analyzer](./ado-workitem-analyzer/) | Score ADO work items, rewrite AC in BDD, suggest story points | DoR Scoring, BDD, Fibonacci SP |
| 12 | [ado-sprint-planner](./ado-sprint-planner/) | Capacity-aware sprint planning from backlog | Velocity, Dependency Mgmt |
| 13 | [ado-release-notes-generator](./ado-release-notes-generator/) | Work items → multi-audience release notes | Semver, Markdown Export |
| 14 | [ado-pipeline-failure-analyzer](./ado-pipeline-failure-analyzer/) | CI/CD log → root cause + fix commands | Error Enum, Log Truncation |
| 15 | [ado-test-case-generator](./ado-test-case-generator/) | User stories → BDD test cases (5 types) | BDD, Automation Flags |
| 16 | [pr-review-assistant](./pr-review-assistant/) | Git diff → full PR review with verdict | Severity Levels, Checklist |
| 17 | [architecture-review-agent](./architecture-review-agent/) | Architecture → Well-Architected Framework review | WAF, SPoF Detection |
| 18 | [tech-debt-analyzer](./tech-debt-analyzer/) | File/dir scan → debt score + quick wins | 7 Categories, Effort Days |
| 19 | [dependency-risk-scanner](./dependency-risk-scanner/) | requirements.txt → CVE risk report | 5 Risk Levels, Upgrade Cmds |
| 20 | [incident-postmortem-generator](./incident-postmortem-generator/) | Incident notes → blameless RCA + action items | RCA Types, Priority Tiers |
| 21 | [standup-report-generator](./standup-report-generator/) | Raw notes → standup/weekly/exec/Slack reports | 4 Formats, Tone-aware |
| 22 | [prompt-library-manager](./prompt-library-manager/) | Versioned prompt registry with A/B testing | MD5 Versioning, CLI |
| 23 | [ai-model-evaluator](./ai-model-evaluator/) | Test suite → LLM-as-judge scoring + hallucination detection | Eval Framework, Judge Pattern |
| 24 | [ai-decision-log-creator](./ai-decision-log-creator/) | Discussion → ADR (Architecture Decision Record) | Nygard Format, Auto-numbering |
| 25 | [team-skill-gap-analyzer](./team-skill-gap-analyzer/) | Team skills vs project needs → gap analysis + hiring plan | Coverage Score, Training Plan |

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/kuldeepz/ai-projects-portfolio
cd ai-projects-portfolio

# Set up environment (once)
cp pdf-chatbot-rag/.env.example pdf-chatbot-rag/.env
# Add your OPENAI_API_KEY to each project's .env

# Run any project
cd pdf-chatbot-rag
pip install -r requirements.txt
python chatbot.py
```

## Running Sanity Tests (No API Key Required)

All projects include sanity tests that validate structure and logic without calling the OpenAI API.

```bash
# Run all core project tests
python incident-postmortem-generator/test_postmortem.py

# Run individual project tests
python ado-workitem-analyzer/test_analyzer.py
python pr-review-assistant/test_reviewer.py
python architecture-review-agent/test_reviewer.py
python tech-debt-analyzer/test_analyzer.py
python dependency-risk-scanner/test_scanner.py
python standup-report-generator/test_standup.py
python prompt-library-manager/test_manager.py
python ai-model-evaluator/test_evaluator.py
python ai-decision-log-creator/test_adr_creator.py
python team-skill-gap-analyzer/test_analyzer.py
```

## Tech Stack

- **LLM:** OpenAI GPT-4o-mini (function calling + structured outputs)
- **Language:** Python 3.10+
- **UI:** Rich terminal (panels, tables, syntax highlighting)
- **Patterns:** Lazy client init · Agent loops · LLM-as-judge · BDD generation · RAG

## Structure

```
ai-projects-portfolio/
├── pdf-chatbot-rag/          # Project 1-10: core AI tools
├── ...
├── ado-workitem-analyzer/    # Project 11-25: advanced AI skills
├── ...
└── README.md
```

> Each project folder contains: `main_script.py`, `test_*.py`, `README.md`, `requirements.txt`, `.env.example`
