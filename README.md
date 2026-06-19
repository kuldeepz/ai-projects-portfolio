# AI Projects Portfolio

Personal AI/ML portfolio — 25 practical tools and agents built with OpenAI GPT-4o-mini, plus custom Claude Code skills.

## Repository Structure

```
ai-projects-portfolio/
├── ai-projects/    ← 25 runnable AI/ML Python projects
└── skills/         ← 24 pure SKILL.md agent skills (no code, no dependencies)
    ├── developer/      5 skills  — code-review, write-tests, debug-error, explain-code, refactor-code
    ├── it-ops/         4 skills  — incident-rca, pipeline-fix, dependency-audit, write-runbook
    ├── lead/           6 skills  — sprint-plan, pr-review-checklist, adr-create, standup-write, skill-gap-review, release-notes
    └── code-checks/    9 skills  — async, exceptions, null-safety, types, security, memory, concurrency, dead-code, logging
```

---

## [ai-projects/](./ai-projects/) — Core AI Tools (1–10)

| # | Project | Description | Key Tech |
|---|---------|-------------|----------|
| 1 | [pdf-chatbot-rag](./ai-projects/pdf-chatbot-rag/) | Chat with any PDF using RAG | Embeddings, Cosine Similarity |
| 2 | [ai-resume-analyzer](./ai-projects/ai-resume-analyzer/) | Score & improve your resume with AI | Function Calling, ATS Check |
| 3 | [smart-research-agent](./ai-projects/smart-research-agent/) | Autonomous research agent with web search | Agent Loop, Tool Use |
| 4 | [ai-code-reviewer](./ai-projects/ai-code-reviewer/) | Security & quality code review | Function Calling, Severity Ratings |
| 5 | [email-composer-ai](./ai-projects/email-composer-ai/) | Generate emails from bullet points | Tone Control, Structured Output |
| 6 | [ai-meeting-summarizer](./ai-projects/ai-meeting-summarizer/) | Transcript → action items & notes | Function Calling, Markdown Export |
| 7 | [sql-query-generator](./ai-projects/sql-query-generator/) | Natural language → SQL (6 dialects) | Schema-aware, Multi-turn |
| 8 | [unit-test-generator](./ai-projects/unit-test-generator/) | Auto-generate pytest suites | AST Parsing, Function Calling |
| 9 | [document-comparison-agent](./ai-projects/document-comparison-agent/) | Compare two docs, find conflicts | Similarity Score, Side-by-side |
| 10 | [sentiment-dashboard](./ai-projects/sentiment-dashboard/) | Sentiment + emotion analysis, batch CSV | Aspect-level, Batch Mode |

## [ai-projects/](./ai-projects/) — Advanced AI Skills (11–25)

> ADO automation, engineering leadership, architecture review, and MLOps tooling.

| # | Project | Description | Key Tech |
|---|---------|-------------|----------|
| 11 | [ado-workitem-analyzer](./ai-projects/ado-workitem-analyzer/) | Score ADO work items, rewrite AC in BDD | DoR Scoring, BDD, Fibonacci SP |
| 12 | [ado-sprint-planner](./ai-projects/ado-sprint-planner/) | Capacity-aware sprint planning | Velocity, Dependency Mgmt |
| 13 | [ado-release-notes-generator](./ai-projects/ado-release-notes-generator/) | Work items → multi-audience release notes | Semver, Markdown Export |
| 14 | [ado-pipeline-failure-analyzer](./ai-projects/ado-pipeline-failure-analyzer/) | CI/CD log → root cause + fix commands | Error Enum, Log Truncation |
| 15 | [ado-test-case-generator](./ai-projects/ado-test-case-generator/) | User stories → BDD test cases (5 types) | BDD, Automation Flags |
| 16 | [pr-review-assistant](./ai-projects/pr-review-assistant/) | Git diff → full PR review with verdict | Severity Levels, Checklist |
| 17 | [architecture-review-agent](./ai-projects/architecture-review-agent/) | Architecture → Well-Architected review | WAF, SPoF Detection |
| 18 | [tech-debt-analyzer](./ai-projects/tech-debt-analyzer/) | File/dir scan → debt score + quick wins | 7 Categories, Effort Days |
| 19 | [dependency-risk-scanner](./ai-projects/dependency-risk-scanner/) | requirements.txt → CVE risk report | 5 Risk Levels, Upgrade Cmds |
| 20 | [incident-postmortem-generator](./ai-projects/incident-postmortem-generator/) | Incident notes → blameless RCA | RCA Types, Priority Tiers |
| 21 | [standup-report-generator](./ai-projects/standup-report-generator/) | Raw notes → standup/weekly/exec/Slack | 4 Formats, Tone-aware |
| 22 | [prompt-library-manager](./ai-projects/prompt-library-manager/) | Versioned prompt registry with A/B testing | MD5 Versioning, CLI |
| 23 | [ai-model-evaluator](./ai-projects/ai-model-evaluator/) | LLM-as-judge scoring + hallucination detection | Eval Framework, Judge Pattern |
| 24 | [ai-decision-log-creator](./ai-projects/ai-decision-log-creator/) | Discussion → Architecture Decision Record | Nygard Format, Auto-numbering |
| 25 | [team-skill-gap-analyzer](./ai-projects/team-skill-gap-analyzer/) | Team skills vs project needs → gap analysis | Coverage Score, Training Plan |

---

## [skills/](./skills/) — Agent Skills (24 skills)

Pure SKILL.md files — no code, no dependencies. Invoke as `/skill-name` in Claude Code or any SKILL.md-compatible agent.

| Category | Count | Skills |
|----------|-------|--------|
| [developer/](./skills/developer/) | 5 | `/code-review` · `/write-tests` · `/debug-error` · `/explain-code` · `/refactor-code` |
| [it-ops/](./skills/it-ops/) | 4 | `/incident-rca` · `/pipeline-fix` · `/dependency-audit` · `/write-runbook` |
| [lead/](./skills/lead/) | 6 | `/sprint-plan` · `/pr-review-checklist` · `/adr-create` · `/standup-write` · `/skill-gap-review` · `/release-notes` |
| [code-checks/](./skills/code-checks/) | 9 | `/async-check` · `/exception-check` · `/null-safety` · `/type-check` · `/security-scan` · `/memory-check` · `/concurrency-check` · `/dead-code` · `/log-check` |

> See [skills/README.md](./skills/README.md) for the full index with descriptions.

---

## Quick Start

```bash
git clone https://github.com/kuldeepz/ai-projects-portfolio
cd ai-projects-portfolio/ai-projects/pdf-chatbot-rag
pip install -r requirements.txt
cp .env.example .env   # add OPENAI_API_KEY
python chatbot.py
```

## Sanity Tests (No API Key Required)

```bash
cd ai-projects
python incident-postmortem-generator/test_postmortem.py
python pr-review-assistant/test_reviewer.py
python architecture-review-agent/test_reviewer.py
# ... etc
```

## Tech Stack

- **LLM:** OpenAI GPT-4o-mini (function calling + structured outputs)
- **Language:** Python 3.10+
- **UI:** Rich terminal (panels, tables, syntax highlighting)
- **Patterns:** Lazy client init · Agent loops · LLM-as-judge · BDD · RAG
